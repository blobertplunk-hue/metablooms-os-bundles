# ECL:
#   id: MPP.S4.CDR
#   role: gate
#   owns: [code delta review — beauty and scope are locked here before a line is written]
#   does_not: [write code, evaluate correctness, run tests]
#   inputs: [turn_dir: str]
#   outputs: [StageResult, aesthetic_contract loaded into StageResult.notes as JSON]
#   side_effects: [filesystem — writes s4_cdr_receipt.json, exports aesthetic contract path]
#   failure_modes: [MISSING_ARTIFACTS, REVIEW_BLOCKED, AESTHETIC_CONTRACT_INCOMPLETE,
#                   SCOPE_MISMATCH_WITH_DOSSIER]
#   invariants: [passes only when REVIEW_DECISION verdict is APPROVED]
#   evidence: [receipts/s4_cdr_receipt.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json (this stage locks that contract)
#   last_reviewed: 2026-02-18
"""
Stage 4 — CDR: Code Delta Review

Intent:
    Beauty and correctness are not afterthoughts — they are designed in.
    CDR is the stage where the exact change is proposed, its blast radius
    is mapped, and its aesthetic rules are locked before implementation begins.
    By the time code is written, its shape is already decided.

Scope:
    Validates DELTA_PROPOSAL, IMPACT_ANALYSIS, AESTHETIC_CONTRACT,
    and REVIEW_DECISION. Exports the aesthetic contract for downstream
    stages to enforce.

Non-Goals:
    Does not write the code. Does not assess whether the proposal is a
    good idea — only that it is fully specified and explicitly approved.

Aesthetic Contract:
    The AESTHETIC_CONTRACT.json binds all downstream stages. ECL will
    enforce its naming and structure rules. The TEST stage will verify
    output quality against its output_format spec.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from mpp.stages import Issue, Severity, StageID, StageResult

REQUIRED_CDR_ARTIFACTS = [
    "cdr/DELTA_PROPOSAL.md",
    "cdr/IMPACT_ANALYSIS.md",
    "cdr/AESTHETIC_CONTRACT.json",
    "cdr/REVIEW_DECISION.json",
]

AESTHETIC_REQUIRED_KEYS = [
    "naming_style",
    "max_function_lines",
    "max_nesting_depth",
    "line_length_limit",
    "output_format",
    "expressiveness_rule",
    "banned_patterns",
]


def run(turn_dir: str) -> StageResult:
    root   = Path(turn_dir)
    issues = []
    found  = []

    for artifact in REQUIRED_CDR_ARTIFACTS:
        path = root / artifact
        if not path.exists():
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = artifact,
                description = f"Required CDR artifact '{artifact}' is missing.",
                remediation = f"Create {artifact}. See mpp/contracts/ for templates.",
            ))
        else:
            found.append(artifact)

    if len(found) < len(REQUIRED_CDR_ARTIFACTS):
        _write_receipt(root, passed=False, verdict="BLOCKED_MISSING")
        return StageResult(stage=StageID.CDR, passed=False, artifacts=found, issues=issues,
                           notes="BLOCKED: CDR artifacts missing.")

    issues += _validate_review_decision(root)
    issues += _validate_aesthetic_contract(root)
    issues += _validate_scope_consistency(root)

    passed = not any(i.severity in (Severity.CRITICAL, Severity.HIGH) for i in issues)
    verdict = "APPROVED" if passed else "BLOCKED"
    _write_receipt(root, passed=passed, verdict=verdict)

    aesthetic_path = str(root / "cdr" / "AESTHETIC_CONTRACT.json")
    notes = f"PASSED — aesthetic contract locked at {aesthetic_path}" if passed else \
            f"BLOCKED: {sum(1 for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH))} issue(s)."

    return StageResult(
        stage     = StageID.CDR,
        passed    = passed,
        artifacts = found,
        issues    = issues,
        notes     = notes,
    )


# ---- Sub-validators ---------------------------------------------------------

def _validate_review_decision(root: Path) -> List[Issue]:
    """REVIEW_DECISION must have verdict=APPROVED with a reason."""
    decision = _load_json(root / "cdr" / "REVIEW_DECISION.json")
    if not isinstance(decision, dict):
        return [Issue(Severity.HIGH, "cdr/REVIEW_DECISION.json",
                      "REVIEW_DECISION.json is not valid JSON or is not an object.",
                      "Fix the JSON. Root must be an object.")]
    issues = []
    verdict = str(decision.get("verdict", "")).upper()
    if verdict != "APPROVED":
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "cdr/REVIEW_DECISION.json",
            description = f"Review verdict is '{verdict}', not APPROVED. Pipeline cannot continue.",
            remediation = (
                "Either set \"verdict\": \"APPROVED\" with a written reason, "
                "or revise the DELTA_PROPOSAL and re-review."
            ),
        ))
    if not str(decision.get("reason", "")).strip():
        issues.append(Issue(
            severity    = Severity.MEDIUM,
            location    = "cdr/REVIEW_DECISION.json",
            description = "Review decision has no written reason.",
            remediation = "Add a 'reason' string explaining why the change was approved.",
        ))
    return issues


def _validate_aesthetic_contract(root: Path) -> List[Issue]:
    """AESTHETIC_CONTRACT must have all required keys with non-empty values."""
    contract = _load_json(root / "cdr" / "AESTHETIC_CONTRACT.json")
    if not isinstance(contract, dict):
        return [Issue(Severity.HIGH, "cdr/AESTHETIC_CONTRACT.json",
                      "AESTHETIC_CONTRACT.json is not valid JSON or is not an object.",
                      "Fix the JSON.")]
    issues = []
    for key in AESTHETIC_REQUIRED_KEYS:
        value = contract.get(key)
        if value is None:
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = "cdr/AESTHETIC_CONTRACT.json",
                description = f"Required aesthetic key '{key}' is missing.",
                remediation = f"Add \"{key}\" to AESTHETIC_CONTRACT.json. See MPP_SPEC.md for the schema.",
            ))
        elif isinstance(value, str) and not value.strip():
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = "cdr/AESTHETIC_CONTRACT.json",
                description = f"Aesthetic key '{key}' is an empty string.",
                remediation = f"Provide a non-empty value for '{key}'.",
            ))
    return issues


def _validate_scope_consistency(root: Path) -> List[Issue]:
    """Files touched in DELTA_PROPOSAL must be consistent with research_dossier."""
    dossier       = _load_json(root / "research_dossier.json") or {}
    dossier_files = set(dossier.get("files_touched", []))

    proposal_path = root / "cdr" / "DELTA_PROPOSAL.md"
    proposal_text = proposal_path.read_text(encoding="utf-8", errors="replace")

    issues = []
    if not proposal_text.strip():
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "cdr/DELTA_PROPOSAL.md",
            description = "DELTA_PROPOSAL.md is empty. It must describe the exact change.",
            remediation = "Write a detailed description of what files change and why.",
        ))

    # Only check consistency if dossier declared files — avoids false positives
    if dossier_files:
        for fname in dossier_files:
            if fname not in proposal_text:
                issues.append(Issue(
                    severity    = Severity.MEDIUM,
                    location    = "cdr/DELTA_PROPOSAL.md",
                    description = f"File '{fname}' is in research_dossier.json::files_touched "
                                  "but not mentioned in DELTA_PROPOSAL.md.",
                    remediation = f"Either reference '{fname}' in the proposal or remove it from files_touched.",
                ))
    return issues


# ---- Helpers ----------------------------------------------------------------

def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_receipt(root: Path, *, passed: bool, verdict: str) -> None:
    import datetime
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "stage":    "S4_CDR",
        "passed":   passed,
        "verdict":  verdict,
        "time_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }
    (receipts / "s4_cdr_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
