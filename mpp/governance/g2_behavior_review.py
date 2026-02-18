# ECL:
#   id: GVN.G2.BEHAVIOR_REVIEW
#   role: gate
#   owns: [test quality validation — tests must assert behaviors users care about, not just pass]
#   does_not: [run tests, write tests, fix code, interpret whether assertions are logically correct]
#   inputs: [turn_dir: str]
#   outputs: [GovStageResult — passed only when behavior review is signed SUFFICIENT]
#   side_effects: [filesystem — reads gov/BEHAVIOR_REVIEW.md and gov/receipts/g2_behavior_receipt.json]
#   failure_modes: [REVIEW_MISSING, RECEIPT_MISSING, VERDICT_INSUFFICIENT, HOLLOW_TESTS_UNRESOLVED,
#                   USER_BEHAVIOR_GAPS_UNRESOLVED]
#   invariants: [never passes if verdict is INSUFFICIENT or any hollow test remains unresolved]
#   evidence: [gov/receipts/g2_behavior_receipt.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
G2 — Behavior Review: Test Quality Gate

Intent:
    Tests that pass but assert the wrong things are worse than no tests —
    they create false confidence. The behavior reviewer's job is to check
    that the test suite proves behaviors users actually need, not that
    the code runs without crashing.

Scope:
    Validates that BEHAVIOR_REVIEW.md exists, the reviewer answered
    all 5 behavior questions, and the receipt confirms the verdict is
    SUFFICIENT with no hollow tests remaining unresolved.

Non-Goals:
    Does not run or write tests. Does not evaluate logical correctness
    of assertions. Does not assess coverage percentage (MPP does that).
    Assesses only whether the right behaviors are being tested.

The Five Behavior Questions (all required):
    1. Costly bug test: which test catches the most expensive production failure?
    2. Hollow test: which test passes even if core logic is completely wrong?
    3. User behavior gap: what user-facing behavior has no test?
    4. Assertion quality: are tests asserting specific values or just no-exception?
    5. Edge case match: is every MMD edge case covered by a test?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from mpp.governance.gov_types import GovIssue, GovSeverity, GovStageID, GovStageResult

FIVE_BEHAVIOR_QUESTIONS = [
    "costly bug test",
    "hollow test",
    "user behavior gap",
    "assertion quality",
    "edge case match",
]


def run(turn_dir: str) -> GovStageResult:
    root   = Path(turn_dir)
    issues = []

    review_path  = root / "gov" / "BEHAVIOR_REVIEW.md"
    receipt_path = root / "gov" / "receipts" / "g2_behavior_receipt.json"

    if not review_path.exists():
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "gov/BEHAVIOR_REVIEW.md",
            description = "Behavior Review document is missing.",
            remediation = (
                "A reviewer (not the test author) must answer all 5 behavior questions "
                "in gov/BEHAVIOR_REVIEW.md. "
                "Use mpp/governance/templates/BEHAVIOR_REVIEW.template.md."
            ),
        ))

    if not receipt_path.exists():
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "gov/receipts/g2_behavior_receipt.json",
            description = "G2 governance receipt is missing.",
            remediation = "Complete the behavior review and write the signed receipt.",
        ))

    if issues:
        return GovStageResult(stage=GovStageID.G2, passed=False, issues=issues,
                              notes="BLOCKED: Behavior review artifacts missing.")

    issues += _validate_review_document(review_path)
    issues += _validate_receipt(receipt_path)

    passed = not any(i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH) for i in issues)
    notes  = "PASSED" if passed else \
             f"BLOCKED: {sum(1 for i in issues if i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH))} issue(s)."

    return GovStageResult(
        stage     = GovStageID.G2,
        passed    = passed,
        artifacts = ["gov/BEHAVIOR_REVIEW.md", "gov/receipts/g2_behavior_receipt.json"],
        issues    = issues,
        notes     = notes,
    )


# ---- Sub-validators ---------------------------------------------------------

def _validate_review_document(review_path: Path) -> List[GovIssue]:
    """All five question categories must be addressed in the document."""
    issues = []
    text   = review_path.read_text(encoding="utf-8", errors="replace").lower()

    for question in FIVE_BEHAVIOR_QUESTIONS:
        if question not in text:
            issues.append(GovIssue(
                severity    = GovSeverity.HIGH,
                location    = "gov/BEHAVIOR_REVIEW.md",
                description = f"Required behavior question '{question}' not addressed.",
                remediation = (
                    f"Add a section explicitly addressing '{question}'. "
                    "Answering 'none found' is acceptable with specific justification. "
                    "Omitting the question is not."
                ),
            ))

    if len(text.strip()) < 250:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/BEHAVIOR_REVIEW.md",
            description = "Behavior Review is too short to be substantive.",
            remediation = "Each of the 5 questions warrants a paragraph. Short answers signal rubber-stamping.",
        ))

    return issues


def _validate_receipt(receipt_path: Path) -> List[GovIssue]:
    """Receipt must record verdict, hollow tests found, and user behavior gaps."""
    issues  = []
    receipt = _load_json(receipt_path)

    if not isinstance(receipt, dict):
        return [GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = str(receipt_path),
            description = "G2 receipt is not valid JSON.",
            remediation = "Fix the JSON. See mpp/governance/templates/G2_RECEIPT.template.json.",
        )]

    if not str(receipt.get("reviewer", "")).strip():
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g2_behavior_receipt.json",
            description = "Receipt has no 'reviewer' field.",
            remediation = "Add \"reviewer\": \"name or role\" to the receipt.",
        ))

    verdict = str(receipt.get("verdict", "")).upper()
    if verdict == "INSUFFICIENT":
        hollow  = receipt.get("hollow_tests_found", [])
        gaps    = receipt.get("user_behavior_gaps", [])
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g2_behavior_receipt.json",
            description = (
                f"Behavior Review verdict is INSUFFICIENT. "
                f"Hollow tests: {hollow}. User behavior gaps: {gaps}."
            ),
            remediation = (
                "Fix the test suite to address hollow tests and user behavior gaps, "
                "then re-run the behavior review."
            ),
        ))
    elif verdict not in ("SUFFICIENT",):
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g2_behavior_receipt.json",
            description = f"verdict is '{verdict}' — must be SUFFICIENT or INSUFFICIENT.",
            remediation = "Set verdict to SUFFICIENT or INSUFFICIENT.",
        ))

    # Check for unresolved hollow tests
    hollow_tests = receipt.get("hollow_tests_found", [])
    if isinstance(hollow_tests, list) and len(hollow_tests) > 0:
        resolved = receipt.get("hollow_tests_resolved", False)
        if not resolved:
            issues.append(GovIssue(
                severity    = GovSeverity.HIGH,
                location    = "gov/receipts/g2_behavior_receipt.json",
                description = (
                    f"{len(hollow_tests)} hollow test(s) found but hollow_tests_resolved is not true: "
                    f"{hollow_tests}"
                ),
                remediation = (
                    "Rewrite hollow tests so they assert specific expected behaviors. "
                    "Then set \"hollow_tests_resolved\": true in the receipt."
                ),
            ))

    return issues


# ---- Helpers ----------------------------------------------------------------

def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
