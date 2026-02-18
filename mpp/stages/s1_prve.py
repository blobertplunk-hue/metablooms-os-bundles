# ECL:
#   id: MPP.S1.PRVE
#   role: gate
#   owns: [pre-build research validation — nothing executes until this passes]
#   does_not: [conduct the research itself, write any build artifacts]
#   inputs: [turn_dir: str — path to the current turn's working directory]
#   outputs: [StageResult with pass/fail + issue list]
#   side_effects: [filesystem — writes s1_prve_receipt.json to turn_dir/receipts/]
#   failure_modes: [MISSING_ARTIFACT, SCHEMA_INVALID, NOT_AUTHORIZED, TRIVIAL_UNJUSTIFIED]
#   invariants: [never returns passed=True if readiness_decision.json is absent or unauthorized]
#   evidence: [s1_prve_receipt.json in turn_dir/receipts/]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
Stage 1 — PRVE: Pre-Build Research & Validation Engine

Intent:
    Force understanding before action. Research-first is non-negotiable.
    No build step runs until the operator has documented what they know,
    what constrains them, and why they are ready to proceed.

Scope:
    Validates the existence and internal consistency of three research
    artifacts: research_dossier, constraint_register, readiness_decision.

Non-Goals:
    Does not conduct research. Does not write build artifacts.
    Does not evaluate the quality of the research — only its presence
    and structural completeness.

Fast Path:
    If readiness_decision.json claims complexity=TRIVIAL, the gate
    passes with a warning but requires a written justification.
    TRIVIAL claims are rejected if more than one file is touched.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from mpp.stages import Issue, Severity, StageID, StageResult

REQUIRED_ARTIFACTS = [
    "research_dossier.json",
    "constraint_register.json",
    "readiness_decision.json",
]


def run(turn_dir: str) -> StageResult:
    root   = Path(turn_dir)
    issues = []
    found  = []

    for artifact in REQUIRED_ARTIFACTS:
        path = root / artifact
        if not path.exists():
            issues.append(Issue(
                severity    = Severity.CRITICAL,
                location    = artifact,
                description = f"Required research artifact '{artifact}' is missing.",
                remediation = (
                    f"Create {artifact} in {turn_dir}. "
                    "See mpp/contracts/ for starter templates."
                ),
            ))
        else:
            found.append(artifact)

    if issues:
        _write_receipt(root, passed=False, notes="Missing required artifacts.")
        return StageResult(stage=StageID.PRVE, passed=False, artifacts=found, issues=issues,
                           notes="BLOCKED: required artifacts missing.")

    decision = _load_json(root / "readiness_decision.json")
    dossier  = _load_json(root / "research_dossier.json")

    if not decision.get("authorized", False):
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "readiness_decision.json",
            description = "'authorized' is false or missing. Explicit go/no-go is required.",
            remediation = "Set \"authorized\": true and provide a \"justification\" string.",
        ))

    complexity = str(decision.get("complexity", "STANDARD")).upper()
    if complexity == "TRIVIAL":
        justification = str(decision.get("trivial_justification", "")).strip()
        if not justification:
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = "readiness_decision.json",
                description = "TRIVIAL fast-path claimed without a written justification.",
                remediation = "Add \"trivial_justification\": \"one sentence explaining why this is trivial\".",
            ))

        files_touched = dossier.get("files_touched", [])
        if isinstance(files_touched, list) and len(files_touched) > 1:
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = "research_dossier.json",
                description = f"TRIVIAL claimed but {len(files_touched)} files are touched. "
                              "TRIVIAL is only valid for single-file, non-interface changes.",
                remediation = "Either reduce scope to one file or upgrade to STANDARD complexity.",
            ))

    passed = not any(i.severity in (Severity.CRITICAL, Severity.HIGH) for i in issues)
    notes  = "PASSED" if passed else "BLOCKED: authorization or trivial-path violation."
    _write_receipt(root, passed=passed, notes=notes, complexity=complexity)

    return StageResult(
        stage     = StageID.PRVE,
        passed    = passed,
        artifacts = found,
        issues    = issues,
        notes     = notes,
    )


# ---- Helpers ----------------------------------------------------------------

def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"_load_error": str(exc)}


def _write_receipt(root: Path, *, passed: bool, notes: str, complexity: str = "STANDARD") -> None:
    import datetime
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "stage":      "S1_PRVE",
        "passed":     passed,
        "complexity": complexity,
        "notes":      notes,
        "time_utc":   datetime.datetime.utcnow().isoformat() + "Z",
    }
    (receipts / "s1_prve_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
