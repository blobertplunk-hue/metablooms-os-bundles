# ECL:
#   id: GVN.G1.ADVERSARIAL_MMD
#   role: gate
#   owns: [adversarial gap review — an independent party actively tries to break the plan]
#   does_not: [conduct the adversarial review itself, add gaps to MMD_REPORT directly]
#   inputs: [turn_dir: str]
#   outputs: [GovStageResult — passed only when a different reviewer answered all 6 questions]
#   side_effects: [filesystem — reads gov/ADVERSARIAL_MMD.md and gov/receipts/g1_adversarial_receipt.json]
#   failure_modes: [ADVERSARIAL_DOC_MISSING, RECEIPT_MISSING, SAME_REVIEWER_AS_RESEARCH,
#                   NOT_ALL_QUESTIONS_ANSWERED, GAPS_FOUND_BUT_NOT_ADDED_TO_MMD]
#   invariants: [never passes if reviewer is the same as research operator,
#                any new gaps found must be added to MMD_REPORT.json before this gate passes]
#   evidence: [gov/receipts/g1_adversarial_receipt.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
G1 — Adversarial MMD: Active Gap Hunting Gate

Intent:
    The author of a plan cannot see its own blind spots. The adversarial
    reviewer's job is not to check that the MMD report is complete —
    it is to independently find gaps the author missed. The difference
    is the difference between a proofreader and an attacker.

Scope:
    Validates that a different reviewer answered all 6 adversarial
    questions, documented any new gaps found, and confirmed those gaps
    were added to MMD_REPORT.json before proceeding.

Non-Goals:
    Does not conduct the adversarial review. Does not add gaps to
    MMD_REPORT.json itself — that is the research operator's job after
    being handed the adversarial findings.

The Six Adversarial Questions (all required):
    1. Adversarial input: what does a malicious actor send to break this?
    2. Scale failure: what breaks at 10x expected load?
    3. API misuse: what does a distracted junior engineer do wrong?
    4. False assumption: which research claim is most likely wrong?
    5. Missing integration: what existing system is unmentioned?
    6. The obvious unstated: what is so obvious the author forgot to say it?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from mpp.governance.gov_types import GovIssue, GovSeverity, GovStageID, GovStageResult
from mpp.governance.pattern_context import (
    FINDING_MISSING_CASCADE_NODE_IN_G1,
    FINDING_MISSING_MISDIAGNOSIS_REVIEW,
    load_pattern_context,
)

SIX_REQUIRED_QUESTIONS = [
    "adversarial_input",
    "scale_failure",
    "api_misuse",
    "false_assumption",
    "missing_integration",
    "obvious_unstated",
]


def run(turn_dir: str) -> GovStageResult:
    root   = Path(turn_dir)
    issues = []

    doc_path     = root / "gov" / "ADVERSARIAL_MMD.md"
    receipt_path = root / "gov" / "receipts" / "g1_adversarial_receipt.json"

    if not doc_path.exists():
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "gov/ADVERSARIAL_MMD.md",
            description = "Adversarial MMD document is missing.",
            remediation = (
                "An adversarial reviewer (different from the research operator) must "
                "answer all 6 questions in gov/ADVERSARIAL_MMD.md. "
                "Use mpp/governance/templates/ADVERSARIAL_MMD.template.md."
            ),
        ))

    if not receipt_path.exists():
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "gov/receipts/g1_adversarial_receipt.json",
            description = "G1 governance receipt is missing.",
            remediation = "Complete the adversarial review and write the signed receipt.",
        ))

    if issues:
        return GovStageResult(stage=GovStageID.G1, passed=False, issues=issues,
                              notes="BLOCKED: Adversarial review artifacts missing.")

    issues += _validate_adversarial_document(doc_path)
    issues += _validate_receipt(receipt_path, root)
    issues += _validate_pattern_seeding(receipt_path, root)

    passed = not any(i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH) for i in issues)
    notes  = "PASSED" if passed else \
             f"BLOCKED: {sum(1 for i in issues if i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH))} issue(s)."

    return GovStageResult(
        stage     = GovStageID.G1,
        passed    = passed,
        artifacts = ["gov/ADVERSARIAL_MMD.md", "gov/receipts/g1_adversarial_receipt.json"],
        issues    = issues,
        notes     = notes,
    )


# ---- Sub-validators ---------------------------------------------------------

def _validate_adversarial_document(doc_path: Path) -> List[GovIssue]:
    """Every one of the 6 question keys must appear in the document."""
    issues = []
    text   = doc_path.read_text(encoding="utf-8", errors="replace").lower()

    for question_key in SIX_REQUIRED_QUESTIONS:
        display = question_key.replace("_", " ")
        if question_key.replace("_", " ") not in text and question_key not in text:
            issues.append(GovIssue(
                severity    = GovSeverity.HIGH,
                location    = "gov/ADVERSARIAL_MMD.md",
                description = f"Required adversarial question '{display}' not found in document.",
                remediation = (
                    f"Answer the '{display}' question explicitly. "
                    "If genuinely not applicable, write the question and explain why with a specific reason."
                ),
            ))

    if len(text.strip()) < 300:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/ADVERSARIAL_MMD.md",
            description = "Adversarial MMD document is too short to reflect genuine adversarial thinking.",
            remediation = (
                "Each answer should be substantive. 'N/A' without explanation is not accepted. "
                "The adversarial reviewer should spend at least 15 minutes actively trying to break the plan."
            ),
        ))

    return issues


def _validate_receipt(receipt_path: Path, root: Path) -> List[GovIssue]:
    """Receipt must be signed by a different reviewer than the research operator."""
    issues  = []
    receipt = _load_json(receipt_path)

    if not isinstance(receipt, dict):
        return [GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = str(receipt_path),
            description = "G1 receipt is not valid JSON.",
            remediation = "Fix the JSON. See mpp/governance/templates/G1_RECEIPT.template.json.",
        )]

    adversarial_reviewer = str(receipt.get("reviewer", "")).strip().lower()
    if not adversarial_reviewer:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g1_adversarial_receipt.json",
            description = "G1 receipt has no 'reviewer' field.",
            remediation = "Add \"reviewer\": \"name or role\" to the receipt.",
        ))

    # Cross-check against G0 receipt to enforce different-reviewer rule
    g0_receipt = _load_json(root / "gov" / "receipts" / "g0_context_brief_receipt.json") or {}
    research_reviewer = str(g0_receipt.get("reviewer", "")).strip().lower()
    if (adversarial_reviewer and research_reviewer
            and adversarial_reviewer == research_reviewer):
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g1_adversarial_receipt.json",
            description = (
                f"Adversarial reviewer '{adversarial_reviewer}' is the same person "
                "as the G0 reviewer. The adversarial review must be independent."
            ),
            remediation = (
                "A different person must conduct the adversarial review. "
                "For solo operation: start a new session and explicitly switch roles "
                "before writing the adversarial document."
            ),
        ))

    if not receipt.get("all_six_questions_answered"):
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g1_adversarial_receipt.json",
            description = "Receipt does not confirm all six adversarial questions were answered.",
            remediation = "Set \"all_six_questions_answered\": true after answering all questions in ADVERSARIAL_MMD.md.",
        ))

    new_gaps = receipt.get("new_gaps_found", [])
    gaps_added_to_mmd = receipt.get("new_gaps_added_to_mmd_report", False)
    if isinstance(new_gaps, list) and len(new_gaps) > 0 and not gaps_added_to_mmd:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g1_adversarial_receipt.json",
            description = (
                f"{len(new_gaps)} new gap(s) found in adversarial review but "
                "new_gaps_added_to_mmd_report is not true."
            ),
            remediation = (
                "Add the adversarial gaps to mmd/MMD_REPORT.json, then set "
                "\"new_gaps_added_to_mmd_report\": true in the G1 receipt."
            ),
        ))

    return issues


# ---- Pattern seeding validator ----------------------------------------------

def _validate_pattern_seeding(receipt_path: Path, root: Path) -> List[GovIssue]:
    """
    Verify the adversarial reviewer was seeded with the G0 pattern context.

    If G0 detected any patterns, the G1 receipt must contain:
      misdiagnosis_cards_reviewed: [pattern_id, ...]
      cascade_nodes_addressed:     [pattern_id, ...]

    For block-risk patterns, ALL cascade nodes must appear in
    cascade_nodes_addressed or the gate blocks.
    """
    ctx = load_pattern_context(str(root))
    if ctx is None or not ctx.detected:
        return []   # No pattern context — skip gracefully.

    receipt = _load_json(receipt_path)
    if not isinstance(receipt, dict):
        return []   # Already caught by _validate_receipt().

    issues: List[GovIssue] = []

    reviewed  = [str(x) for x in receipt.get("misdiagnosis_cards_reviewed", [])]
    addressed = [str(x) for x in receipt.get("cascade_nodes_addressed", [])]

    # Every detected pattern should appear in misdiagnosis_cards_reviewed.
    for pattern in ctx.detected:
        if pattern.pattern_id not in reviewed:
            issues.append(GovIssue(
                severity    = GovSeverity.HIGH,
                location    = "gov/receipts/g1_adversarial_receipt.json",
                description = (
                    f"[{FINDING_MISSING_MISDIAGNOSIS_REVIEW}] Pattern '{pattern.pattern_id}' "
                    "was detected at G0 but is not listed in misdiagnosis_cards_reviewed. "
                    "The adversarial reviewer must consult the misdiagnosis entries for this pattern "
                    "to avoid reproducing the same cognitive errors in production incidents."
                ),
                remediation = (
                    f"Add '{pattern.pattern_id}' to misdiagnosis_cards_reviewed in the G1 receipt. "
                    "Read its misdiagnosis entries in the pattern card before signing. "
                    "See gov/G0_LINT_REPORT.md for the full pattern list."
                ),
            ))

    # For block-risk patterns, all cascade nodes must be addressed.
    for pattern in ctx.block_patterns:
        for node_id in pattern.cascade_chain:
            if node_id not in addressed:
                issues.append(GovIssue(
                    severity    = GovSeverity.HIGH,
                    location    = "gov/receipts/g1_adversarial_receipt.json",
                    description = (
                        f"[{FINDING_MISSING_CASCADE_NODE_IN_G1}] Cascade node '{node_id}' "
                        f"(downstream of block-risk pattern '{pattern.pattern_id}') "
                        "is not listed in cascade_nodes_addressed. "
                        "The adversarial reviewer must actively probe whether this cascade node "
                        "can be triggered by the proposed design under load."
                    ),
                    remediation = (
                        f"Add '{node_id}' to cascade_nodes_addressed in the G1 receipt after "
                        "explicitly testing whether the design resists this cascade. "
                        "If it does, document the specific mechanism that prevents it."
                    ),
                ))

    return issues


# ---- Helpers ----------------------------------------------------------------

def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
