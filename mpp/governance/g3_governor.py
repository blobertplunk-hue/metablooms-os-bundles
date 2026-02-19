# ECL:
#   id: GVN.G3.GOVERNOR
#   role: orchestrator
#   owns: [pipeline health tracking — detects gaming, drift, and systemic failures across runs]
#   does_not: [override MPP gates, approve blocked changes, run the pipeline itself]
#   inputs: [turn_dir: str, governor_log_path: str (defaults to gov/GOVERNOR_LOG.md)]
#   outputs: [GovStageResult, appends entry to GOVERNOR_LOG.md]
#   side_effects: [filesystem — appends to gov/GOVERNOR_LOG.md, may update mpp_config.json thresholds]
#   failure_modes: [LOG_UNWRITABLE, GAMING_SIGNAL_DETECTED, THRESHOLD_DRIFT,
#                   CONSECUTIVE_ESCALATIONS_WITHOUT_PROGRESS]
#   invariants: [governor log is append-only — entries are never deleted or modified,
#                governor may raise thresholds but never lower them without explicit justification]
#   evidence: [gov/GOVERNOR_LOG.md]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
G3 — Governor Loop: Pipeline Health Tracking

Intent:
    A pipeline that isn't monitored will be gamed. Not necessarily
    deliberately — teams under pressure take shortcuts. The Governor
    tracks whether the pipeline is being used as designed or
    as a rubber stamp, and adjusts thresholds accordingly.

Scope:
    Reads the MPP certificate history and governance receipts across
    runs to detect: gaming signals (repetitive boilerplate), quality
    drift (shorter research artifacts over time), and threshold
    miscalibration (coverage that's too low or too high for the
    actual failure rate).

    Appends a structured entry to the Governor Log after each run.

Non-Goals:
    Does not override MPP gates. Does not approve blocked changes.
    Does not assess the correctness of individual artifacts — only
    patterns across multiple runs.

Gaming Signals (Governor flags these):
    - Same edge cases appearing in every MMD report
    - CDR proposals getting shorter over successive runs
    - Research dossiers shrinking in word count over time
    - Coverage threshold always hit exactly (suspiciously precise)
    - Adversarial reviewer always finding zero new gaps
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mpp.governance.gov_types import GovIssue, GovSeverity, GovStageID, GovStageResult
from mpp.governance.pattern_context import load_pattern_context


def run(turn_dir: str,
        governor_log_path: Optional[str] = None) -> GovStageResult:
    root     = Path(turn_dir)
    log_path = Path(governor_log_path) if governor_log_path else root / "gov" / "GOVERNOR_LOG.md"
    issues   = []

    cert_history   = _load_certificate_history(root)
    gov_receipts   = _load_all_gov_receipts(root)

    if len(cert_history) >= 3:
        issues += _detect_gaming_signals(root, cert_history)
        issues += _detect_threshold_drift(root, cert_history)
        issues += _detect_consecutive_escalations(cert_history)

    gov_entry = _build_governor_entry(root, cert_history, gov_receipts, issues)
    _append_to_governor_log(log_path, gov_entry)

    # Governor runs last and warns but does not block (it's a health signal, not a gate)
    # CRITICAL issues from governor DO block — they indicate systemic misuse
    blocking = [i for i in issues if i.severity == GovSeverity.CRITICAL]
    passed   = len(blocking) == 0

    warning_count = sum(1 for i in issues if i.severity in (GovSeverity.HIGH, GovSeverity.MEDIUM))
    notes = (
        f"PASSED — {warning_count} governance warning(s). See GOVERNOR_LOG.md."
        if passed else
        f"BLOCKED — {len(blocking)} systemic issue(s) detected. Pipeline health at risk."
    )

    return GovStageResult(
        stage     = GovStageID.G3,
        passed    = passed,
        artifacts = [str(log_path.relative_to(root))],
        issues    = issues,
        notes     = notes,
    )


# ---- Gaming signal detectors ------------------------------------------------

def _detect_gaming_signals(root: Path,
                            cert_history: List[Dict[str, Any]]) -> List[GovIssue]:
    """Look for patterns that indicate the pipeline is being used as a rubber stamp."""
    issues = []

    # Check adversarial reviews — a reviewer who always finds zero gaps is not trying
    adversarial_receipts = _load_adversarial_receipts_across_runs(root)
    zero_gap_streak = sum(
        1 for r in adversarial_receipts
        if isinstance(r.get("new_gaps_found"), list) and len(r["new_gaps_found"]) == 0
    )
    if zero_gap_streak >= 3:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/ (adversarial history)",
            description = (
                f"Adversarial reviewer has found zero new gaps in {zero_gap_streak} consecutive runs. "
                "This is statistically unlikely in active development and suggests the review is perfunctory."
            ),
            remediation = (
                "Assign a different adversarial reviewer or require the reviewer to spend "
                "more structured time with the plan. Consider mandatory external review rotation."
            ),
        ))

    # Check for shrinking research dossiers
    dossier_lengths = _measure_artifact_lengths_over_runs(root, "research_dossier.json")
    if _is_consistently_shrinking(dossier_lengths):
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "research_dossier.json (trend)",
            description = "Research dossiers have been getting shorter over the last 3 runs. Quality may be drifting.",
            remediation = (
                "Review recent dossiers for substance. Shorter is only acceptable if "
                "the problem genuinely became simpler. If not, restore depth."
            ),
        ))

    return issues


def _detect_threshold_drift(root: Path,
                             cert_history: List[Dict[str, Any]]) -> List[GovIssue]:
    """Detect if coverage thresholds are miscalibrated for the actual failure rate."""
    issues = []

    # If every recent run hits coverage exactly at threshold ± 1%, the threshold may be gamed
    coverages = [
        float(entry.get("coverage_pct", 0))
        for entry in cert_history
        if "coverage_pct" in entry
    ]
    if len(coverages) >= 3:
        config    = _load_json(root / "mpp_config.json") or {}
        threshold = float(config.get("coverage_threshold", 90))
        near_threshold = sum(1 for c in coverages[-3:] if abs(c - threshold) <= 2)
        if near_threshold == 3:
            issues.append(GovIssue(
                severity    = GovSeverity.MEDIUM,
                location    = "mpp_config.json::coverage_threshold",
                description = (
                    f"Coverage has been within 2% of the {threshold}% threshold for 3 consecutive runs. "
                    "This pattern suggests tests are being written to hit the threshold, not to verify behavior."
                ),
                remediation = (
                    "Raise the coverage threshold by 5% in mpp_config.json, "
                    "or have the Governor audit whether recent tests are substantive."
                ),
            ))

    return issues


def _detect_consecutive_escalations(cert_history: List[Dict[str, Any]]) -> List[GovIssue]:
    """Detect a run of escalations — the pipeline is stuck and needs structural intervention."""
    issues = []

    recent_escalations = sum(
        1 for entry in cert_history[-4:]
        if entry.get("verdict") == "ESCALATED"
    )
    if recent_escalations >= 3:
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "MPP_CERTIFICATE.json (escalation trend)",
            description = (
                f"{recent_escalations} of the last 4 pipeline runs escalated without certification. "
                "The pipeline is structurally blocked. This requires human intervention, "
                "not another iteration."
            ),
            remediation = (
                "Stop running the pipeline. Convene a review of: "
                "(1) whether the problem is correctly stated in the Context Brief, "
                "(2) whether the research operator has sufficient domain knowledge, "
                "(3) whether the pipeline thresholds are appropriate for this type of change."
            ),
        ))

    return issues


# ---- Helpers ----------------------------------------------------------------

def _load_certificate_history(root: Path) -> List[Dict[str, Any]]:
    cert = _load_json(root / "MPP_CERTIFICATE.json") or {}
    return cert.get("entries", [])


def _load_all_gov_receipts(root: Path) -> Dict[str, Any]:
    receipts_dir = root / "gov" / "receipts"
    result       = {}
    if receipts_dir.exists():
        for receipt_path in receipts_dir.glob("*.json"):
            data = _load_json(receipt_path)
            if data:
                result[receipt_path.name] = data
    return result


def _load_adversarial_receipts_across_runs(root: Path) -> List[Dict[str, Any]]:
    """Load all G1 adversarial receipts from loop iteration history."""
    receipts = []
    loop_dir = root / "loop"
    if not loop_dir.exists():
        return receipts
    for iteration_file in sorted(loop_dir.glob("ITERATION_*_RECEIPT.json")):
        data = _load_json(iteration_file)
        if isinstance(data, dict):
            gov_data = data.get("governance", {})
            g1 = gov_data.get("G1_ADVERSARIAL_MMD")
            if g1:
                receipts.append(g1)
    return receipts


def _measure_artifact_lengths_over_runs(root: Path, artifact_name: str) -> List[int]:
    """Return word counts of a named artifact from recent loop iterations."""
    lengths  = []
    loop_dir = root / "loop"
    if not loop_dir.exists():
        return lengths
    for iteration_file in sorted(loop_dir.glob("ITERATION_*_RECEIPT.json")):
        data = _load_json(iteration_file)
        if isinstance(data, dict):
            length = data.get("artifact_lengths", {}).get(artifact_name)
            if isinstance(length, int):
                lengths.append(length)
    return lengths


def _is_consistently_shrinking(lengths: List[int]) -> bool:
    """True if each value is strictly less than the previous."""
    if len(lengths) < 3:
        return False
    return all(lengths[i] < lengths[i - 1] for i in range(1, len(lengths)))


def _build_governor_entry(root: Path, cert_history: List[Dict],
                           gov_receipts: Dict, issues: List[GovIssue]) -> Dict[str, Any]:
    latest_cert = cert_history[-1] if cert_history else {}
    return {
        "time_utc":         datetime.datetime.utcnow().isoformat() + "Z",
        "total_runs":       len(cert_history),
        "latest_verdict":   latest_cert.get("verdict", "NONE"),
        "latest_iteration": latest_cert.get("iteration", 0),
        "gov_stages_run":   list(gov_receipts.keys()),
        "governor_issues":  [
            {"severity": i.severity.value, "description": i.description}
            for i in issues
        ],
        "lint_accuracy":    _compute_lint_accuracy(root, gov_receipts),
        "health":           "HEALTHY" if not issues else
                            "DEGRADED" if not any(i.severity == GovSeverity.CRITICAL for i in issues)
                            else "CRITICAL",
    }


def _compute_lint_accuracy(root: Path, gov_receipts: Dict) -> Dict[str, Any]:
    """
    Compare G0's predicted patterns against what G1 adversarial review found.

    This is the feedback loop that validates the cascade graph over time.
    If lint repeatedly predicts patterns that G1 never confirms, the trigger
    shapes on those cards may need revision. If G1 repeatedly finds patterns
    that lint missed, new trigger shapes or cards are needed.

    Returns an accuracy summary for the current run's governor entry.
    This is observational — it does not block the pipeline on its own.
    G3 uses repetition across runs to decide whether to flag drift.
    """
    ctx = load_pattern_context(str(root))
    if ctx is None:
        return {"status": "no_lint_context"}
    if not ctx.detected:
        return {"status": "no_patterns_detected", "predicted": []}

    predicted_ids = [p.pattern_id for p in ctx.detected]

    # Look for pattern IDs mentioned in G1 adversarial gaps.
    g1_receipt_name = "g1_adversarial_receipt.json"
    g1 = gov_receipts.get(g1_receipt_name, {})
    g1_gaps_text = " ".join(str(g) for g in g1.get("new_gaps_found", [])).lower()
    g1_reviewed  = [str(x) for x in g1.get("misdiagnosis_cards_reviewed", [])]

    confirmed   = [pid for pid in predicted_ids if pid.lower() in g1_gaps_text or pid in g1_reviewed]
    unconfirmed = [pid for pid in predicted_ids if pid not in confirmed]

    return {
        "status":       "evaluated",
        "predicted":    predicted_ids,
        "confirmed_in_g1": confirmed,
        "unconfirmed":  unconfirmed,
        "note": (
            "unconfirmed patterns are not evidence of a wrong prediction — "
            "G1 may have addressed them without using the pattern ID. "
            "Flag for manual review if unconfirmed count exceeds 3 across consecutive runs."
        ),
    }


def _append_to_governor_log(log_path: Path, entry: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")

    new_entry = (
        f"\n---\n"
        f"**{entry['time_utc']}** | Health: **{entry['health']}** | "
        f"Runs: {entry['total_runs']} | Latest verdict: {entry['latest_verdict']}\n"
    )
    if entry["governor_issues"]:
        new_entry += "\nIssues flagged:\n"
        for issue in entry["governor_issues"]:
            new_entry += f"- [{issue['severity']}] {issue['description']}\n"

    if not existing.strip():
        header = "# Governor Log\nAppend-only health record. Never edit or delete entries.\n"
        log_path.write_text(header + new_entry, encoding="utf-8")
    else:
        log_path.write_text(existing + new_entry, encoding="utf-8")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
