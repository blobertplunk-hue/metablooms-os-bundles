# ECL:
#   id: MPP.S3.MMD
#   role: gate
#   owns: [missing middle detection across all 6 sub-checks including pattern compliance]
#   does_not: [fix gaps, conduct research, modify source code, add pattern cards]
#   inputs: [turn_dir: str]
#   outputs: [StageResult with per-sub-check issue breakdown]
#   side_effects: [filesystem — writes s3_mmd_receipt.json]
#   failure_modes: [MISSING_MMD_REPORT, HIGH_SEVERITY_GAP, INSUFFICIENT_EDGE_CASES,
#                   UNDECLARED_DEPENDENCY, UNMAPPED_INTEGRATION_POINT,
#                   UNADDRESSED_PATTERN, MISSING_PATTERN_WAIVER]
#   invariants: [any HIGH gap blocks regardless of other sub-check results,
#                any ACTIVE pattern matched by code_shapes must be addressed or waived]
#   evidence: [receipts/s3_mmd_receipt.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
Stage 3 — MMD: Missing Middle Detector

Intent:
    The missing middle is the space between "what we said we'd do" and
    "what we actually need to do." It is where bugs are born before a
    single line is written. MMD makes the invisible visible.

Scope:
    Validates all 6 sub-checks in MMD_REPORT.json:
    (1) gaps, (2) dependencies, (3) edge cases, (4) failure modes,
    (5) integrations, (6) pattern compliance.
    Any HIGH-severity unresolved issue blocks the pipeline.

Non-Goals:
    Does not fill gaps. Does not conduct research to resolve unknowns.
    Does not evaluate whether gap resolutions are correct — only that
    each HIGH gap has a stated resolution.
    Does not add pattern cards — that goes through the Study Protocol.

The Six Sub-Checks:
    1. Gap Detection        — unstated assumptions made explicit
    2. Dependency Audit     — all required inputs declared
    3. Edge Case Enum       — min 3 edge cases per non-trivial function
    4. Failure Mode Cat.    — each failure mode has a named response
    5. Integration Audit    — every touch point with existing code mapped
    6. Pattern Compliance   — every ACTIVE pattern matched by code_shapes
                              is addressed in failure_modes or explicitly waived
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mpp.stages import Issue, Severity, StageID, StageResult

EDGE_CASE_MINIMUM = 3


def run(turn_dir: str) -> StageResult:
    root   = Path(turn_dir)
    issues = []

    report_path = root / "mmd" / "MMD_REPORT.json"
    if not report_path.exists():
        issues.append(Issue(
            severity    = Severity.CRITICAL,
            location    = "mmd/MMD_REPORT.json",
            description = "MMD_REPORT.json is missing. All 5 sub-checks are required.",
            remediation = (
                "Create mmd/MMD_REPORT.json with keys: "
                "gaps, dependencies, edge_cases, failure_modes, integration_points. "
                "See mpp/contracts/mmd_report.template.json."
            ),
        ))
        _write_receipt(root, passed=False, summary="Missing MMD_REPORT.json.")
        return StageResult(stage=StageID.MMD, passed=False, issues=issues,
                           notes="BLOCKED: MMD_REPORT.json missing.")

    report = _load_json(report_path)
    if not isinstance(report, dict):
        issues.append(Issue(
            severity    = Severity.CRITICAL,
            location    = "mmd/MMD_REPORT.json",
            description = "MMD_REPORT.json is not valid JSON or is not an object.",
            remediation = "Fix the JSON syntax and ensure the root is a JSON object.",
        ))
        _write_receipt(root, passed=False, summary="Invalid MMD_REPORT.json.")
        return StageResult(stage=StageID.MMD, passed=False, issues=issues)

    issues += _check_gaps(report.get("gaps", []))
    issues += _check_dependencies(report.get("dependencies", []))
    issues += _check_edge_cases(report.get("edge_cases", []))
    issues += _check_failure_modes(report.get("failure_modes", []))
    issues += _check_integration_points(report.get("integration_points", []))
    issues += _check_pattern_compliance(report, root)

    passed = not any(i.severity in (Severity.CRITICAL, Severity.HIGH) for i in issues)
    high_count = sum(1 for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH))
    notes  = "PASSED" if passed else f"BLOCKED: {high_count} HIGH/CRITICAL issue(s) in MMD sub-checks."
    _write_receipt(root, passed=passed, summary=notes)

    return StageResult(
        stage     = StageID.MMD,
        passed    = passed,
        artifacts = ["mmd/MMD_REPORT.json"],
        issues    = issues,
        notes     = notes,
    )


# ---- Sub-check validators ---------------------------------------------------

def _check_gaps(gaps: List[Any]) -> List[Issue]:
    """Sub-check 1: Every HIGH gap must have a resolution."""
    issues = []
    if not isinstance(gaps, list):
        return [Issue(Severity.HIGH, "mmd/MMD_REPORT.json::gaps",
                      "'gaps' must be a list.", "Fix the schema.")]
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        severity = str(gap.get("severity", "")).upper()
        if severity == "HIGH" and not str(gap.get("resolution", "")).strip():
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = f"mmd/MMD_REPORT.json::gaps[{gap.get('id', '?')}]",
                description = f"HIGH gap '{gap.get('id', 'unnamed')}' has no resolution: {gap.get('description', '')}",
                remediation = "Add a 'resolution' string explaining how this gap is closed.",
            ))
    return issues


def _check_dependencies(deps: List[Any]) -> List[Issue]:
    """Sub-check 2: Every dependency must have a name and type."""
    issues = []
    if not isinstance(deps, list):
        return [Issue(Severity.MEDIUM, "mmd/MMD_REPORT.json::dependencies",
                      "'dependencies' must be a list.", "Fix the schema.")]
    for dep in deps:
        if not isinstance(dep, dict):
            continue
        if not dep.get("name") or not dep.get("type"):
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = "mmd/MMD_REPORT.json::dependencies",
                description = f"Dependency entry is missing 'name' or 'type': {dep}",
                remediation = "Each dependency needs {\"name\": \"...\", \"type\": \"stdlib|third-party|internal|runtime\", \"declared\": true}",
            ))
    return issues


def _check_edge_cases(edge_cases: List[Any]) -> List[Issue]:
    """Sub-check 3: Non-trivial changes must enumerate at least 3 edge cases."""
    issues = []
    if not isinstance(edge_cases, list):
        return [Issue(Severity.HIGH, "mmd/MMD_REPORT.json::edge_cases",
                      "'edge_cases' must be a list.", "Fix the schema.")]
    if len(edge_cases) < EDGE_CASE_MINIMUM:
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "mmd/MMD_REPORT.json::edge_cases",
            description = f"Only {len(edge_cases)} edge case(s) documented. Minimum is {EDGE_CASE_MINIMUM}.",
            remediation = (
                f"Add at least {EDGE_CASE_MINIMUM - len(edge_cases)} more edge case(s). "
                "Each must include: {\"input\": \"...\", \"expected_behavior\": \"...\", \"test_exists\": false}."
            ),
        ))
    for ec in edge_cases:
        if not isinstance(ec, dict):
            continue
        if not ec.get("input") or not ec.get("expected_behavior"):
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = "mmd/MMD_REPORT.json::edge_cases",
                description = f"Edge case missing 'input' or 'expected_behavior': {ec}",
                remediation = "Every edge case must state what the input is and what the system should do with it.",
            ))
    return issues


def _check_failure_modes(failure_modes: List[Any]) -> List[Issue]:
    """Sub-check 4: Each failure mode must have a named response."""
    issues = []
    if not isinstance(failure_modes, list):
        return [Issue(Severity.HIGH, "mmd/MMD_REPORT.json::failure_modes",
                      "'failure_modes' must be a list.", "Fix the schema.")]
    if not failure_modes:
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "mmd/MMD_REPORT.json::failure_modes",
            description = "No failure modes documented. Every non-trivial function can fail.",
            remediation = (
                "Add at least one failure mode: "
                "{\"name\": \"...\", \"trigger\": \"...\", \"response\": \"BLOCK|WARN|ESCALATE|SKIP\"}."
            ),
        ))
    for fm in failure_modes:
        if not isinstance(fm, dict):
            continue
        if not fm.get("name") or not fm.get("response"):
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = "mmd/MMD_REPORT.json::failure_modes",
                description = f"Failure mode missing 'name' or 'response': {fm}",
                remediation = "Each failure mode needs a name and a response (BLOCK|WARN|ESCALATE|SKIP).",
            ))
    return issues


def _check_integration_points(points: List[Any]) -> List[Issue]:
    """Sub-check 5: Every touch point with existing code must be mapped."""
    issues = []
    if not isinstance(points, list):
        return [Issue(Severity.MEDIUM, "mmd/MMD_REPORT.json::integration_points",
                      "'integration_points' must be a list.", "Fix the schema.")]
    for pt in points:
        if not isinstance(pt, dict):
            continue
        if not pt.get("target") or not pt.get("contract"):
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = "mmd/MMD_REPORT.json::integration_points",
                description = f"Integration point missing 'target' or 'contract': {pt}",
                remediation = (
                    "Each integration point needs: "
                    "{\"target\": \"module.function\", \"contract\": \"what we expect from it\"}."
                ),
            ))
    return issues


# ---- Sub-check 6 — Pattern Compliance ---------------------------------------

def _check_pattern_compliance(report: Dict[str, Any], root: Path) -> List[Issue]:
    """
    Sub-check 6: Every ACTIVE failure pattern matched by the research dossier's
    code_shapes must appear in MMD_REPORT.json::pattern_checks and must be either
    addressed (addressed=true, addressed_in points to the failure mode or gap that
    covers it) or explicitly waived (addressed=false, waiver is a specific reason).

    If code_shapes is absent or empty, this sub-check produces no issues —
    pure refactors and documentation changes have nothing to match.

    DRAFT patterns produce a MEDIUM advisory (not blocking).
    ACTIVE patterns with no entry produce a HIGH issue (blocking).
    ACTIVE patterns with addressed=false and no waiver produce a HIGH issue (blocking).
    """
    dossier = _load_json(root / "research_dossier.json") or {}
    code_shapes: List[str] = dossier.get("code_shapes", [])

    if not isinstance(code_shapes, list) or not code_shapes:
        return []

    try:
        from mpp.patterns.pattern_registry import PatternRegistry, RegistryValidationError
        registry = PatternRegistry()
    except Exception as exc:
        return [Issue(
            severity    = Severity.MEDIUM,
            location    = "mpp/patterns/",
            description = f"Pattern registry failed to load: {exc}",
            remediation = "Fix the pattern library before MMD can run sub-check 6.",
        )]

    # Find all ACTIVE and DRAFT patterns that match any declared code shape.
    matched: Dict[str, Any] = {}   # pattern_id → PatternCard
    for shape in code_shapes:
        for card in registry.find_by_trigger(shape):
            if card.id not in matched:
                matched[card.id] = card

    if not matched:
        return []

    # Index the operator's pattern_checks by pattern_id.
    declared_checks: Dict[str, Dict[str, Any]] = {}
    for entry in report.get("pattern_checks", []):
        if isinstance(entry, dict) and "pattern_id" in entry:
            pid = str(entry["pattern_id"])
            if not pid.startswith("_"):          # skip template comment entries
                declared_checks[pid] = entry

    issues = []
    for pattern_id, card in sorted(matched.items()):
        if card.is_draft:
            # DRAFT patterns are advisory — flag but don't block.
            if pattern_id not in declared_checks:
                issues.append(Issue(
                    severity    = Severity.MEDIUM,
                    location    = "mmd/MMD_REPORT.json::pattern_checks",
                    description = (
                        f"DRAFT pattern '{pattern_id}' ({card.name}) matched your code shapes "
                        "but has no entry in pattern_checks."
                    ),
                    remediation = (
                        f"Add a pattern_checks entry for '{pattern_id}'. "
                        "DRAFT patterns are advisory — an explicit waiver is enough."
                    ),
                ))
            continue

        # ACTIVE patterns must be explicitly handled.
        if pattern_id not in declared_checks:
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = "mmd/MMD_REPORT.json::pattern_checks",
                description = (
                    f"ACTIVE pattern '{pattern_id}' ({card.name}) matched your code shapes "
                    "but has no entry in pattern_checks."
                ),
                remediation = (
                    f"Add an entry for '{pattern_id}' to pattern_checks. "
                    "Either address it in failure_modes and set addressed=true, "
                    "or set addressed=false with a specific waiver explaining why it doesn't apply. "
                    f"Diagnostic: {card.diagnostic}"
                ),
            ))
            continue

        check     = declared_checks[pattern_id]
        addressed = check.get("addressed", False)
        waiver    = str(check.get("waiver") or "").strip()

        if addressed:
            addressed_in = str(check.get("addressed_in") or "").strip()
            if not addressed_in:
                issues.append(Issue(
                    severity    = Severity.MEDIUM,
                    location    = f"mmd/MMD_REPORT.json::pattern_checks[{pattern_id}]",
                    description = (
                        f"Pattern '{pattern_id}' is marked addressed=true but "
                        "'addressed_in' is empty. Where in this report is it handled?"
                    ),
                    remediation = (
                        "Set addressed_in to the failure_modes entry name or gaps ID "
                        "that covers this pattern, e.g. \"failure_modes[RETRY_STORM]\"."
                    ),
                ))
        else:
            if not waiver:
                issues.append(Issue(
                    severity    = Severity.HIGH,
                    location    = f"mmd/MMD_REPORT.json::pattern_checks[{pattern_id}]",
                    description = (
                        f"Pattern '{pattern_id}' is marked addressed=false with no waiver. "
                        "Either address it or explain explicitly why it doesn't apply."
                    ),
                    remediation = (
                        "Set waiver to a specific reason this pattern is not applicable "
                        "(e.g. 'all writes use idempotency keys — see SEE_CITATION_MAP::C3'). "
                        "'N/A' without a reason is not accepted."
                    ),
                ))

    return issues


# ---- Helpers ----------------------------------------------------------------

def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_receipt(root: Path, *, passed: bool, summary: str) -> None:
    import datetime
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "stage":    "S3_MMD",
        "passed":   passed,
        "summary":  summary,
        "time_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }
    (receipts / "s3_mmd_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
