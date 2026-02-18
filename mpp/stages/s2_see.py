# ECL:
#   id: MPP.S2.SEE
#   role: gate
#   owns: [evidence validation — every claim must be cited before proceeding]
#   does_not: [conduct searches, write research content, interpret sources]
#   inputs: [turn_dir: str]
#   outputs: [StageResult]
#   side_effects: [filesystem — writes s2_see_receipt.json]
#   failure_modes: [MISSING_SEE_ARTIFACTS, UNCITED_CLAIMS, ANTI_PATTERNS_UNDOCUMENTED]
#   invariants: [passes only when all dossier claims appear in citation map]
#   evidence: [receipts/s2_see_receipt.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
Stage 2 — SEE: Sandcrawler Evidence Engine

Intent:
    No claim survives without evidence. Every external fact — about a library,
    a pattern, a best practice — must be traceable to a source that was actually
    consulted. Confidence is not evidence.

Scope:
    Validates that SEE artifacts exist, that each claim in the research dossier
    is mapped to a source, and that anti-patterns have been documented.

Non-Goals:
    Does not conduct searches. Does not judge the quality of sources.
    Does not validate the truth of claims — only that they are cited.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from mpp.stages import Issue, Severity, StageID, StageResult

REQUIRED_SEE_ARTIFACTS = [
    "see/SEE_QUERIES.json",
    "see/SEE_SOURCES.md",
    "see/SEE_CITATION_MAP.json",
    "see/SEE_EVIDENCE_SUMMARY.md",
    "see/SEE_ANTI_PATTERNS.md",
]


def run(turn_dir: str) -> StageResult:
    root   = Path(turn_dir)
    issues = []
    found  = []

    for artifact in REQUIRED_SEE_ARTIFACTS:
        path = root / artifact
        if not path.exists():
            issues.append(Issue(
                severity    = Severity.HIGH,
                location    = artifact,
                description = f"Required SEE artifact '{artifact}' is missing.",
                remediation = f"Create {artifact}. It must document evidence for this turn.",
            ))
        else:
            found.append(artifact)

    if issues:
        _write_receipt(root, passed=False, uncited=[])
        return StageResult(stage=StageID.SEE, passed=False, artifacts=found, issues=issues,
                           notes="BLOCKED: SEE artifacts missing.")

    uncited = _find_uncited_claims(root)
    for claim_id in uncited:
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "research_dossier.json",
            description = f"Claim '{claim_id}' in research_dossier.json is not cited in SEE_CITATION_MAP.json.",
            remediation = (
                f"Add an entry for '{claim_id}' in see/SEE_CITATION_MAP.json mapping it "
                "to a source in SEE_SOURCES.md."
            ),
        ))

    anti_patterns = _load_json(root / "see/SEE_ANTI_PATTERNS.md")
    if not anti_patterns:
        issues.append(Issue(
            severity    = Severity.MEDIUM,
            location    = "see/SEE_ANTI_PATTERNS.md",
            description = "SEE_ANTI_PATTERNS.md is empty. At least one known anti-pattern must be documented.",
            remediation = (
                "Add at least one anti-pattern with evidence of why it should be avoided. "
                "If genuinely none exist, write: '## None known — justification: [reason]'."
            ),
        ))

    passed = not any(i.severity in (Severity.CRITICAL, Severity.HIGH) for i in issues)
    notes  = "PASSED" if passed else f"BLOCKED: {len(uncited)} uncited claim(s)."
    _write_receipt(root, passed=passed, uncited=list(uncited))

    return StageResult(
        stage     = StageID.SEE,
        passed    = passed,
        artifacts = found,
        issues    = issues,
        notes     = notes,
    )


# ---- Helpers ----------------------------------------------------------------

def _find_uncited_claims(root: Path) -> Set[str]:
    """Return claim IDs present in research_dossier but absent from SEE_CITATION_MAP."""
    dossier     = _load_json(root / "research_dossier.json")
    citation    = _load_json(root / "see/SEE_CITATION_MAP.json")
    cited_ids   = set(citation.keys()) if isinstance(citation, dict) else set()
    all_claims  = dossier.get("claims", [])

    if not isinstance(all_claims, list):
        return set()

    uncited = set()
    for claim in all_claims:
        claim_id = claim.get("id") if isinstance(claim, dict) else str(claim)
        if claim_id and claim_id not in cited_ids:
            uncited.add(str(claim_id))
    return uncited


def _load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        return json.loads(text)
    except (json.JSONDecodeError, OSError):
        return None


def _write_receipt(root: Path, *, passed: bool, uncited: List[str]) -> None:
    import datetime
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "stage":         "S2_SEE",
        "passed":        passed,
        "uncited_claims": uncited,
        "time_utc":      datetime.datetime.utcnow().isoformat() + "Z",
    }
    (receipts / "s2_see_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
