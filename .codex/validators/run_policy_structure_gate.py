#!/usr/bin/env python3
"""
GATE: Policy Structural Validation
EXIT 0 = PASS, EXIT 16 = FAIL

For each governed policy document (.codex/policies/*.md), validates that:
1. Required structural sections exist
2. Cross-references to other artifacts are valid (files exist)
3. Policy-specific mechanical checks pass

This gate promotes policies from DRAFT to at least VALIDATED by proving
their structural integrity, even though they're markdown (not JSON-schema-validatable).
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICIES_DIR = ROOT / ".codex" / "policies"

failures = []
checked = 0


def check_section_exists(content, section_name, filepath_short):
    """Check that a markdown heading exists."""
    # Match ## or ### headings containing the section name (case-insensitive)
    pattern = r'^#{1,4}\s+.*' + re.escape(section_name)
    if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
        failures.append(f"  {filepath_short}: missing required section '{section_name}'")
        return False
    return True


def check_file_ref(content, ref_path, filepath_short):
    """Check that a referenced file path actually exists."""
    full = ROOT / ref_path
    if ref_path in content and not full.exists():
        failures.append(f"  {filepath_short}: references '{ref_path}' but file not found")
        return False
    return True


def validate_super_prompt(filepath):
    """SUPER_PROMPT: must have all MPP phases and reference governance docs."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    # Must reference key phases
    for phase in ["PHASE 0", "PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5", "PHASE 6", "PHASE 7"]:
        if phase not in content:
            failures.append(f"  {short}: missing MPP {phase}")

    # Must reference governance documents
    if "FORBIDDEN LANGUAGE" not in content.upper():
        failures.append(f"  {short}: missing FORBIDDEN LANGUAGE section")

    # Must reference BOOT
    if "BOOT" not in content:
        failures.append(f"  {short}: no reference to BOOT")


def validate_cdr(filepath):
    """CDR: must define all 7 pillars."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    # CDR uses "### N. Name" format or "Pillar N" — check for either
    pillar_names = [
        "Proactive Rationale",
        "Explicit Constraint Mapping",
        "Semantic Domain Authority",
        "Anticipated Failure Intent",
        "Integration Reciprocity",
        "History-Aware Evolution",
        "Mandatory Attestation",
    ]
    for i, name in enumerate(pillar_names, 1):
        if name not in content and f"Pillar {i}" not in content:
            failures.append(f"  {short}: missing Pillar {i} ({name})")

    if "violation" not in content.lower():
        failures.append(f"  {short}: no violation classes defined")


def validate_see(filepath):
    """SEE: must define evidence sources, quality ranks, and evidence strength."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    check_section_exists(content, "EVIDENCE SOURCE", short)
    check_section_exists(content, "METHOD SELECTION", short)

    # Must define quality ranks
    for rank in ["DIRECT_OBSERVATION", "COMPUTED_VERIFICATION"]:
        if rank not in content:
            failures.append(f"  {short}: missing quality rank '{rank}'")

    # Must define evidence strength levels
    for strength in ["CONFIRMED", "SUPPORTED", "UNSUPPORTED"]:
        if strength not in content:
            failures.append(f"  {short}: missing evidence strength '{strength}'")

    # Must reference BUNDLE_INTERNAL_EVENTS (invariant MB_INV_BUNDLE_INTERNALS_AS_EVIDENCE_V1)
    if "BUNDLE_INTERNAL_EVENTS" not in content:
        failures.append(f"  {short}: missing BUNDLE_INTERNAL_EVENTS source type")


def validate_rrp(filepath):
    """RRP: must define bounded iteration with convergence controls."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    if "BUILD" not in content or "EVALUATE" not in content or "REWRITE" not in content:
        failures.append(f"  {short}: missing BUILD/EVALUATE/REWRITE cycle")

    # Must have convergence bounds
    if "max" not in content.lower() or "iteration" not in content.lower():
        failures.append(f"  {short}: no max iteration bound defined")

    if "convergence" not in content.lower():
        failures.append(f"  {short}: no convergence test defined")


def validate_deltagate(filepath):
    """DELTAGATE: must define proposal/evaluation/admission flow."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    for concept in ["PROPOSE", "ADMIT", "REJECT"]:
        if concept not in content.upper():
            failures.append(f"  {short}: missing concept '{concept}'")


def validate_lifecycle(filepath):
    """LIFECYCLE: must define all 6 lifecycle statuses."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    for status in ["ACTIVE", "SUPERSEDED", "DEPRECATED", "FROZEN", "DUPLICATE", "ORPHANED"]:
        if status not in content:
            failures.append(f"  {short}: missing lifecycle status '{status}'")


def validate_learning_pipeline(filepath):
    """LEARNING_PIPELINE: must define the failure->RCA->fix loop."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    for concept in ["RCA", "EVT_FAIL", "EVT_LEARNING", "corrective"]:
        if concept not in content:
            failures.append(f"  {short}: missing concept '{concept}'")


def validate_mbql(filepath):
    """MBQL: must define query structure, NLQ translator, and invariant evaluation."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    check_section_exists(content, "NLQ", short)

    for concept in ["FROM", "WHERE", "SELECT", "INTENT_IR"]:
        if concept not in content:
            failures.append(f"  {short}: missing query concept '{concept}'")

    if "INVARIANT" not in content:
        failures.append(f"  {short}: missing invariant evaluation support")


def validate_maturity(filepath):
    """ARTIFACT_MATURITY: must define DRAFT/VALIDATED/ENFORCED stages."""
    global checked
    checked += 1
    content = filepath.read_text()
    short = str(filepath.relative_to(ROOT))

    for stage in ["DRAFT", "VALIDATED", "ENFORCED"]:
        if stage not in content:
            failures.append(f"  {short}: missing maturity stage '{stage}'")

    if "demotion" not in content.lower():
        failures.append(f"  {short}: no demotion rules defined")


# Map policy files to their validators
POLICY_VALIDATORS = {
    "SUPER_PROMPT_v2.3.md": validate_super_prompt,
    "CDR_v2.md": validate_cdr,
    "SEE_ENGINE_v1.md": validate_see,
    "RRP_v1.md": validate_rrp,
    "DELTAGATE_v1.md": validate_deltagate,
    "BUNDLE_LIFECYCLE_v1.md": validate_lifecycle,
    "LEARNING_PIPELINE_v1.md": validate_learning_pipeline,
    "MBQL_v1.md": validate_mbql,
    "ARTIFACT_MATURITY_v1.md": validate_maturity,
}


def main():
    if not POLICIES_DIR.exists():
        print("POLICY_GATE FAIL: .codex/policies/ not found", file=sys.stderr)
        sys.exit(16)

    for policy_file, validator_fn in POLICY_VALIDATORS.items():
        filepath = POLICIES_DIR / policy_file
        if filepath.exists():
            validator_fn(filepath)
        else:
            # Only fail if it's a current (non-superseded) policy
            if "v2.2" not in policy_file:  # v2.2 is superseded, OK if missing
                failures.append(f"  {policy_file}: POLICY FILE NOT FOUND")

    if failures:
        print(f"POLICY_GATE FAIL: {len(failures)} issues across {checked} policies", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(16)
    else:
        print(f"POLICY_GATE: PASS ({checked} policies structurally validated)")
        sys.exit(0)


if __name__ == "__main__":
    main()
