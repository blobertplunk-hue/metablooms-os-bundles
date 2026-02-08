#!/usr/bin/env python3
"""
GATE: Invariant Evaluation
EXIT 0 = PASS, EXIT 14 = FAIL

Evaluates all ACTIVE invariants in INVARIANT_REGISTRY.json.
Each invariant has a verification_method and evidence_sources that
describe how to check it. This gate performs mechanical checks.
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
failures = []
checked = 0


def check_mb_inv_nlq_required_v1():
    """
    MB_INV_NLQ_REQUIRED_V1: NLQ translator must exist and be complete.
    Checks:
    1. MBQL_v1.md exists
    2. INTENT_IR.schema.json exists
    3. MBQL_v1.md contains all 9 intent types
    """
    global checked
    checked += 1

    mbql = ROOT / ".codex" / "policies" / "MBQL_v1.md"
    intent_schema = ROOT / ".codex" / "schemas" / "INTENT_IR.schema.json"

    if not mbql.exists():
        failures.append("  MB_INV_NLQ_REQUIRED_V1: MBQL_v1.md not found")
        return
    if not intent_schema.exists():
        failures.append("  MB_INV_NLQ_REQUIRED_V1: INTENT_IR.schema.json not found")
        return

    # Verify schema has all 9 intent types
    schema = json.loads(intent_schema.read_text())
    intent_enum = (
        schema.get("properties", {})
        .get("intent", {})
        .get("enum", [])
    )
    expected_intents = {
        "INVENTORY", "LOOKUP", "LINEAGE", "STATUS",
        "INTEGRITY", "TEMPORAL", "AGGREGATE", "GAP", "INVARIANT",
    }
    missing = expected_intents - set(intent_enum)
    if missing:
        failures.append(f"  MB_INV_NLQ_REQUIRED_V1: INTENT_IR schema missing intents: {missing}")


def check_mb_inv_bundle_internals_v1():
    """
    MB_INV_BUNDLE_INTERNALS_AS_EVIDENCE_V1: SEE must recognize bundle events.
    Checks:
    1. SEE_ENGINE_v1.md exists and contains "BUNDLE_INTERNAL_EVENTS"
    2. SEE_ENGINE_v1.md ranks it as DIRECT_OBSERVATION
    3. LEARNING_EVENT.schema.json exists
    """
    global checked
    checked += 1

    see = ROOT / ".codex" / "policies" / "SEE_ENGINE_v1.md"
    event_schema = ROOT / ".codex" / "schemas" / "LEARNING_EVENT.schema.json"

    if not see.exists():
        failures.append("  MB_INV_BUNDLE_INTERNALS_V1: SEE_ENGINE_v1.md not found")
        return
    if not event_schema.exists():
        failures.append("  MB_INV_BUNDLE_INTERNALS_V1: LEARNING_EVENT.schema.json not found")
        return

    see_content = see.read_text()
    if "BUNDLE_INTERNAL_EVENTS" not in see_content:
        failures.append(
            "  MB_INV_BUNDLE_INTERNALS_V1: BUNDLE_INTERNAL_EVENTS not defined in SEE"
        )
    if "DIRECT_OBSERVATION" not in see_content:
        failures.append(
            "  MB_INV_BUNDLE_INTERNALS_V1: DIRECT_OBSERVATION quality rank not found in SEE"
        )

    # Verify schema has event types
    schema = json.loads(event_schema.read_text())
    event_enum = (
        schema.get("properties", {})
        .get("event_type", {})
        .get("enum", [])
    )
    if len(event_enum) < 10:
        failures.append(
            f"  MB_INV_BUNDLE_INTERNALS_V1: LEARNING_EVENT schema has only {len(event_enum)} event types (expected 13)"
        )


def check_mb_inv_maturity_pipeline_v1():
    """
    MB_INV_MATURITY_PIPELINE_V1: Maturity pipeline must be enforced.
    Checks:
    1. ARTIFACT_MATURITY.json exists
    2. ARTIFACT_MATURITY_v1.md policy exists
    3. run_maturity_gate.py validator exists
    4. MATURITY gate is registered in master runner
    """
    global checked
    checked += 1

    maturity_tracker = ROOT / ".codex" / "artifacts" / "ARTIFACT_MATURITY.json"
    maturity_policy = ROOT / ".codex" / "policies" / "ARTIFACT_MATURITY_v1.md"
    maturity_gate = ROOT / ".codex" / "validators" / "run_maturity_gate.py"
    master_runner = ROOT / ".codex" / "validators" / "run_governance_gate.py"

    if not maturity_tracker.exists():
        failures.append("  MB_INV_MATURITY_PIPELINE_V1: ARTIFACT_MATURITY.json not found")
        return
    if not maturity_policy.exists():
        failures.append("  MB_INV_MATURITY_PIPELINE_V1: ARTIFACT_MATURITY_v1.md not found")
        return
    if not maturity_gate.exists():
        failures.append("  MB_INV_MATURITY_PIPELINE_V1: run_maturity_gate.py not found")
        return

    # Check MATURITY gate is registered
    runner_content = master_runner.read_text()
    if '"MATURITY"' not in runner_content:
        failures.append("  MB_INV_MATURITY_PIPELINE_V1: MATURITY gate not registered in master runner")


def check_mb_inv_claim_strength_v1():
    """
    MB_INV_CLAIM_STRENGTH_REQUIRED_V1: Claim strength policy must exist
    and schemas must include claim_strength fields.
    Checks:
    1. CLAIM_STRENGTH_v1.md exists
    2. Schemas with normative claims include claim_strength field
    3. Wikipedia prohibition is documented
    """
    global checked
    checked += 1

    policy = ROOT / ".codex" / "policies" / "CLAIM_STRENGTH_v1.md"
    if not policy.exists():
        failures.append("  MB_INV_CLAIM_STRENGTH_REQUIRED_V1: CLAIM_STRENGTH_v1.md not found")
        return

    content = policy.read_text()
    if "Wikipedia" not in content:
        failures.append(
            "  MB_INV_CLAIM_STRENGTH_REQUIRED_V1: Wikipedia prohibition not documented in policy"
        )

    # Check that at least one schema has claim_strength field
    schemas_dir = ROOT / ".codex" / "schemas"
    found_claim_strength = False
    for schema_file in schemas_dir.glob("*.schema.json"):
        try:
            schema = json.loads(schema_file.read_text())
            props = schema.get("properties", {})
            if "claim_strength" in props:
                found_claim_strength = True
                break
        except json.JSONDecodeError:
            continue

    if not found_claim_strength:
        failures.append(
            "  MB_INV_CLAIM_STRENGTH_REQUIRED_V1: No schema contains claim_strength field"
        )


def check_mb_inv_toolbox_reality_v1():
    """
    MB_INV_TOOLBOX_REALITY_R25_V1: R2.5 must be wired.
    Checks:
    1. TOOLBOX_REALITY.schema.json exists
    2. run_toolbox_reality_gate.py exists
    3. TOOLBOX_REALITY gate is registered in master runner
    4. SUPER_PROMPT mentions Phase 2.5
    """
    global checked
    checked += 1

    schema = ROOT / ".codex" / "schemas" / "TOOLBOX_REALITY.schema.json"
    gate = ROOT / ".codex" / "validators" / "run_toolbox_reality_gate.py"
    master = ROOT / ".codex" / "validators" / "run_governance_gate.py"
    prompt = ROOT / ".codex" / "policies" / "SUPER_PROMPT_v2.3.md"

    if not schema.exists():
        failures.append("  MB_INV_TOOLBOX_REALITY_R25_V1: TOOLBOX_REALITY.schema.json not found")
        return
    if not gate.exists():
        failures.append("  MB_INV_TOOLBOX_REALITY_R25_V1: run_toolbox_reality_gate.py not found")
        return

    master_content = master.read_text()
    if '"TOOLBOX_REALITY"' not in master_content:
        failures.append("  MB_INV_TOOLBOX_REALITY_R25_V1: TOOLBOX_REALITY gate not registered in master runner")

    if prompt.exists():
        prompt_content = prompt.read_text()
        if "Phase 2.5" not in prompt_content and "R2.5" not in prompt_content:
            failures.append("  MB_INV_TOOLBOX_REALITY_R25_V1: SUPER_PROMPT does not document Phase 2.5")


def check_mb_inv_wikipedia_prohibition_v1():
    """
    MB_INV_WIKIPEDIA_PROHIBITION_V1: Wikipedia prohibition documented.
    Checks:
    1. CLAIM_STRENGTH_v1.md exists and mentions Wikipedia prohibition
    """
    global checked
    checked += 1

    policy = ROOT / ".codex" / "policies" / "CLAIM_STRENGTH_v1.md"
    if not policy.exists():
        failures.append("  MB_INV_WIKIPEDIA_PROHIBITION_V1: CLAIM_STRENGTH_v1.md not found")
        return

    content = policy.read_text()
    if "Wikipedia" not in content or "load-bearing" not in content.lower():
        failures.append(
            "  MB_INV_WIKIPEDIA_PROHIBITION_V1: Wikipedia load-bearing prohibition not found in policy"
        )


# Registry of invariant checkers
INVARIANT_CHECKERS = {
    "MB_INV_NLQ_REQUIRED_V1": check_mb_inv_nlq_required_v1,
    "MB_INV_BUNDLE_INTERNALS_AS_EVIDENCE_V1": check_mb_inv_bundle_internals_v1,
    "MB_INV_MATURITY_PIPELINE_V1": check_mb_inv_maturity_pipeline_v1,
    "MB_INV_CLAIM_STRENGTH_REQUIRED_V1": check_mb_inv_claim_strength_v1,
    "MB_INV_TOOLBOX_REALITY_R25_V1": check_mb_inv_toolbox_reality_v1,
    "MB_INV_WIKIPEDIA_PROHIBITION_V1": check_mb_inv_wikipedia_prohibition_v1,
}


def main():
    global checked

    registry_path = ROOT / ".codex" / "artifacts" / "INVARIANT_REGISTRY.json"
    if not registry_path.exists():
        print("INVARIANT_GATE FAIL: INVARIANT_REGISTRY.json not found", file=sys.stderr)
        sys.exit(14)

    registry = json.loads(registry_path.read_text())
    invariants = registry.get("invariants", [])

    for inv in invariants:
        inv_id = inv.get("invariant_id", "?")
        status = inv.get("status", "")

        if status != "ACTIVE":
            continue

        checker = INVARIANT_CHECKERS.get(inv_id)
        if checker:
            checker()
        else:
            checked += 1
            failures.append(f"  {inv_id}: no mechanical checker registered (manual review required)")

    if failures:
        print(f"INVARIANT_GATE FAIL: {len(failures)} issues across {checked} invariants", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(14)
    else:
        print(f"INVARIANT_GATE: PASS ({checked} invariants evaluated)")
        sys.exit(0)


if __name__ == "__main__":
    main()
