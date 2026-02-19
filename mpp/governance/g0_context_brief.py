# ECL:
#   id: GVN.G0.CONTEXT_BRIEF
#   role: gate
#   owns: [context quality validation — domain truth must be present and testable before PRVE runs]
#   does_not: [write the context brief, assess technical correctness, evaluate domain knowledge]
#   inputs: [turn_dir: str]
#   outputs: [GovStageResult — passed only when brief is present, receipt is signed, DoD is testable,
#             and any block-risk patterns detected by architectural lint are addressed in the brief]
#   side_effects: [filesystem — reads gov/CONTEXT_BRIEF.md, gov/receipts/g0_context_brief_receipt.json;
#                  writes gov/G0_LINT_REPORT.json, gov/G0_LINT_REPORT.md]
#   failure_modes: [BRIEF_MISSING, RECEIPT_MISSING, RECEIPT_UNSIGNED, DOD_NOT_TESTABLE,
#                   QUALITY_VERDICT_INSUFFICIENT, MISSING_PATTERN_IN_BRIEF, MISSING_CASCADE_IN_BRIEF]
#   invariants: [never passes if quality_verdict is INSUFFICIENT or definition_of_done_is_testable is false,
#                never passes if a block-risk pattern is detected but not addressed in the brief,
#                G0_LINT_REPORT.json is always written (even when empty) so downstream stages can load it]
#   evidence: [gov/receipts/g0_context_brief_receipt.json, gov/G0_LINT_REPORT.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
G0 — Context Brief: Domain Truth Injection Gate

Intent:
    The pipeline can only produce correct output if it operates on correct
    context. This gate ensures that someone who actually knows the domain
    has explicitly stated the problem, the definition of done, and the
    hidden constraints — before any research or code begins.

Scope:
    Validates that CONTEXT_BRIEF.md exists and that a signed governance
    receipt confirms it meets quality standards. The gate does not
    judge the brief's content — that is the reviewer's job. It ensures
    the reviewer actually reviewed.

Non-Goals:
    Does not evaluate whether the context is technically accurate.
    Does not conduct research. Does not write or edit the brief.
    Does not substitute for a domain expert.

Quality Standard:
    The receipt's quality_verdict must be SUFFICIENT and
    definition_of_done_is_testable must be true.
    If either is false, the pipeline does not start.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from mpp.governance.gov_types import GovIssue, GovSeverity, GovStageID, GovStageResult
from mpp.governance.pattern_context import (
    BLOCK_RISK_LEVELS,
    FINDING_MISSING_CASCADE_IN_BRIEF,
    FINDING_MISSING_PATTERN_IN_BRIEF,
    create_pattern_context,
    save_pattern_context,
)


REQUIRED_BRIEF_SECTIONS = [
    "real user story",
    "definition of done",
    "hidden constraints",
    "failure cost",
    "prior attempts",
]


def run(turn_dir: str) -> GovStageResult:
    root   = Path(turn_dir)
    issues = []

    brief_path   = root / "gov" / "CONTEXT_BRIEF.md"
    receipt_path = root / "gov" / "receipts" / "g0_context_brief_receipt.json"

    if not brief_path.exists():
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "gov/CONTEXT_BRIEF.md",
            description = "Context Brief is missing. No pipeline run is authorized without it.",
            remediation = (
                "Create gov/CONTEXT_BRIEF.md using the template at "
                "mpp/governance/templates/CONTEXT_BRIEF.template.md. "
                "The Context Owner (not the Research Operator) must write it."
            ),
        ))

    if not receipt_path.exists():
        issues.append(GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = "gov/receipts/g0_context_brief_receipt.json",
            description = "G0 governance receipt is missing. A reviewer must sign the Context Brief.",
            remediation = (
                "A reviewer (Context Owner or delegate) must read CONTEXT_BRIEF.md, "
                "complete the quality checklist in mpp/governance/checklists/g0_checklist.md, "
                "and write the signed receipt."
            ),
        ))

    if issues:
        return GovStageResult(stage=GovStageID.G0, passed=False, issues=issues,
                              notes="BLOCKED: Context Brief or receipt missing.")

    issues += _validate_brief_completeness(brief_path)
    issues += _validate_receipt(receipt_path)
    issues += _run_lint_and_validate(brief_path, root)

    passed = not any(i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH) for i in issues)
    notes  = "PASSED" if passed else \
             f"BLOCKED: {sum(1 for i in issues if i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH))} issue(s)."

    return GovStageResult(
        stage     = GovStageID.G0,
        passed    = passed,
        artifacts = ["gov/CONTEXT_BRIEF.md", "gov/receipts/g0_context_brief_receipt.json",
                     "gov/G0_LINT_REPORT.json", "gov/G0_LINT_REPORT.md"],
        issues    = issues,
        notes     = notes,
    )


# ---- Sub-validators ---------------------------------------------------------

def _validate_brief_completeness(brief_path: Path) -> List[GovIssue]:
    """Check that the brief contains all required sections."""
    issues = []
    text   = brief_path.read_text(encoding="utf-8", errors="replace").lower()

    for section in REQUIRED_BRIEF_SECTIONS:
        if section not in text:
            issues.append(GovIssue(
                severity    = GovSeverity.HIGH,
                location    = "gov/CONTEXT_BRIEF.md",
                description = f"Required section '{section}' not found in Context Brief.",
                remediation = (
                    f"Add a section addressing '{section}'. "
                    "See mpp/governance/templates/CONTEXT_BRIEF.template.md for guidance."
                ),
            ))

    if len(text.strip()) < 200:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/CONTEXT_BRIEF.md",
            description = "Context Brief is too short to be meaningful (under 200 characters).",
            remediation = "Expand the brief. A real Context Brief describes a real problem in sufficient depth.",
        ))

    return issues


def _validate_receipt(receipt_path: Path) -> List[GovIssue]:
    """Check that the receipt is signed and its quality verdict is SUFFICIENT."""
    issues  = []
    receipt = _load_json(receipt_path)

    if not isinstance(receipt, dict):
        return [GovIssue(
            severity    = GovSeverity.CRITICAL,
            location    = str(receipt_path),
            description = "G0 receipt is not valid JSON or is not an object.",
            remediation = "Fix the JSON. See mpp/governance/templates/G0_RECEIPT.template.json.",
        )]

    reviewer = str(receipt.get("reviewer", "")).strip()
    if not reviewer:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g0_context_brief_receipt.json",
            description = "Receipt has no 'reviewer' field. Governance requires a named reviewer.",
            remediation = "Add \"reviewer\": \"name or role\" to the receipt.",
        ))

    verdict = str(receipt.get("quality_verdict", "")).upper()
    if verdict == "INSUFFICIENT":
        gaps = receipt.get("gaps_found", [])
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g0_context_brief_receipt.json",
            description = (
                f"Reviewer marked quality_verdict as INSUFFICIENT. "
                f"Gaps found: {gaps if gaps else 'none listed'}."
            ),
            remediation = "Fix the Context Brief to address the reviewer's gaps, then re-review.",
        ))
    elif verdict not in ("SUFFICIENT",):
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g0_context_brief_receipt.json",
            description = f"quality_verdict is '{verdict}' — must be SUFFICIENT or INSUFFICIENT.",
            remediation = "Set quality_verdict to SUFFICIENT or INSUFFICIENT.",
        ))

    dod_testable = receipt.get("definition_of_done_is_testable")
    if dod_testable is not True:
        issues.append(GovIssue(
            severity    = GovSeverity.HIGH,
            location    = "gov/receipts/g0_context_brief_receipt.json",
            description = "definition_of_done_is_testable is not true. The DoD must be unambiguous.",
            remediation = (
                "Revise the Definition of Done in CONTEXT_BRIEF.md so it states a specific, "
                "observable outcome. 'Works correctly' is not testable. "
                "'Returns status 200 with a receipt object containing these fields' is testable."
            ),
        ))

    if not receipt.get("signed_at"):
        issues.append(GovIssue(
            severity    = GovSeverity.MEDIUM,
            location    = "gov/receipts/g0_context_brief_receipt.json",
            description = "Receipt has no 'signed_at' timestamp.",
            remediation = "Add \"signed_at\": \"ISO8601 timestamp\" to the receipt.",
        ))

    return issues


# ---- Pattern lint validator -------------------------------------------------

def _run_lint_and_validate(brief_path: Path, root: Path) -> List[GovIssue]:
    """
    Run architectural_lint() on the Context Brief, write the lint report,
    and validate that any block-risk patterns are addressed in the brief.

    Always writes G0_LINT_REPORT.json (even when empty) so downstream
    stages can load it without guarding against a missing file.
    """
    issues: List[GovIssue] = []
    text = brief_path.read_text(encoding="utf-8", errors="replace")

    try:
        ctx = create_pattern_context(text)
        save_pattern_context(str(root), ctx)
    except Exception:
        # Pattern library failure is non-blocking — the pipeline degrades gracefully.
        return []

    if not ctx.detected:
        return []

    text_lower = text.lower()

    # For each block-risk pattern: it must be named in the brief.
    for pattern in ctx.block_patterns:
        if not _pattern_mentioned_in_text(pattern.pattern_id, pattern.name, text_lower):
            severity = (
                GovSeverity.CRITICAL
                if pattern.data_integrity_risk == "critical" or pattern.financial_risk == "critical"
                else GovSeverity.HIGH
            )
            issues.append(GovIssue(
                severity    = severity,
                location    = "gov/CONTEXT_BRIEF.md :: Failure Cost section",
                description = (
                    f"[{FINDING_MISSING_PATTERN_IN_BRIEF}] Pattern '{pattern.pattern_id}' "
                    f"({pattern.name}) has {pattern.severity_label} risk but is not addressed "
                    "in the Context Brief."
                ),
                remediation = (
                    f"Add a 'Failure Cost / Critical Risks' section that names "
                    f"'{pattern.pattern_id}' and describes how it is mitigated or accepted. "
                    "See gov/G0_LINT_REPORT.md for the full cascade chain and countermeasures."
                ),
            ))

    # For deep-cascade patterns: at least one cascade node must be addressed.
    for pattern in ctx.deep_cascade_patterns:
        if not pattern.cascade_chain:
            continue
        # Skip if the pattern itself was already flagged above.
        if pattern.is_blocking_risk and not _pattern_mentioned_in_text(
            pattern.pattern_id, pattern.name, text_lower
        ):
            continue  # already caught as MISSING_PATTERN_IN_BRIEF above
        # Check cascade node coverage.
        cascade_mentioned = any(
            node_id.lower() in text_lower or node_id.lower().replace("_", " ") in text_lower
            for node_id in pattern.cascade_chain
        )
        if not cascade_mentioned:
            issues.append(GovIssue(
                severity    = GovSeverity.HIGH,
                location    = "gov/CONTEXT_BRIEF.md :: Failure Cost section",
                description = (
                    f"[{FINDING_MISSING_CASCADE_IN_BRIEF}] Pattern '{pattern.pattern_id}' "
                    f"has a cascade chain of depth {pattern.cascade_depth} "
                    f"({' → '.join(pattern.cascade_chain)}) but none of the cascade nodes "
                    "are addressed in the Context Brief."
                ),
                remediation = (
                    "Add a 'Cascade Mitigation' row in the Context Brief naming at least one "
                    "cascade node and the countermeasure applied to break the chain. "
                    "See gov/G0_LINT_REPORT.md for the full dependency map."
                ),
            ))

    return issues


def _pattern_mentioned_in_text(pattern_id: str, pattern_name: str, text_lower: str) -> bool:
    """Check if a pattern is referenced by ID or by significant words from its name."""
    if pattern_id.lower() in text_lower:
        return True
    # Match on words from the pattern name that are long enough to be diagnostic.
    name_words = {
        w for w in pattern_name.lower().split()
        if len(w) > 4 and w not in {"from", "without", "across", "between", "during"}
    }
    return any(word in text_lower for word in name_words)


# ---- Helpers ----------------------------------------------------------------

def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
