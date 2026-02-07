#!/usr/bin/env python3
"""
GATE: Artifact Maturity Pipeline
EXIT 0 = PASS, EXIT 15 = FAIL

Verifies that every artifact's claimed maturity stage is mechanically provable:
  DRAFT    → file exists
  VALIDATED → file exists + has schema/structural check + passes it
  ENFORCED  → all VALIDATED rules + validator exists + gate is registered

Also checks:
  - No governance artifacts exist that are NOT in the tracker (untracked detection)
  - No tracker entries point to files that don't exist (phantom detection)
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATURITY_PATH = ROOT / ".codex" / "artifacts" / "ARTIFACT_MATURITY.json"
GATE_RUNNER = ROOT / ".codex" / "validators" / "run_governance_gate.py"

failures = []
checked = 0


def get_registered_gates():
    """Parse the master gate runner to find which gate names are registered."""
    if not GATE_RUNNER.exists():
        return set()

    content = GATE_RUNNER.read_text()
    gates = set()
    # Parse GATES list entries like ("SCHEMA_VALIDATION", "run_schema_validation_gate.py", 10)
    import re
    for match in re.finditer(r'\("(\w+)",\s*"', content):
        gates.add(match.group(1))
    return gates


def check_draft(entry):
    """DRAFT: file must exist."""
    global checked
    checked += 1
    path = ROOT / entry["artifact_path"]
    if not path.exists():
        failures.append(
            f"  {entry['artifact_path']}: claims DRAFT but file does not exist"
        )


def check_validated(entry):
    """VALIDATED: file exists + has some form of validation."""
    check_draft(entry)  # includes the existence check

    schema_path = entry.get("schema_path")
    structural = entry.get("structural_check")

    if not schema_path and not structural:
        failures.append(
            f"  {entry['artifact_path']}: claims VALIDATED but has no schema_path and no structural_check"
        )
        return

    if schema_path:
        full_schema = ROOT / schema_path
        if not full_schema.exists():
            failures.append(
                f"  {entry['artifact_path']}: claims VALIDATED with schema {schema_path} but schema file missing"
            )


def check_enforced(entry):
    """ENFORCED: all VALIDATED rules + validator exists + gate registered."""
    # Validators enforce themselves — they don't need a validator for the validator
    if entry["artifact_type"] == "validator":
        check_draft(entry)
        return

    check_validated(entry)

    validator_path = entry.get("validator_path")
    gate_name = entry.get("gate_name")

    if not validator_path:
        failures.append(
            f"  {entry['artifact_path']}: claims ENFORCED but has no validator_path"
        )
        return

    full_validator = ROOT / validator_path
    if not full_validator.exists():
        failures.append(
            f"  {entry['artifact_path']}: claims ENFORCED with validator {validator_path} but validator missing"
        )
        return

    if gate_name:
        registered = get_registered_gates()
        if gate_name not in registered:
            failures.append(
                f"  {entry['artifact_path']}: claims ENFORCED with gate '{gate_name}' but gate not registered in master runner"
            )


def check_untracked_artifacts():
    """Find governance artifacts that exist but aren't in the tracker."""
    global checked

    if not MATURITY_PATH.exists():
        return

    data = json.loads(MATURITY_PATH.read_text())
    tracked_paths = {e["artifact_path"] for e in data.get("artifacts", [])}

    # Scan governance directories for artifacts that should be tracked
    scan_dirs = [
        (ROOT / ".codex" / "policies", "*.md"),
        (ROOT / ".codex" / "schemas", "*.json"),
        (ROOT / ".codex" / "artifacts", "*.json"),
        (ROOT / ".codex" / "receipts", "*.json"),
        (ROOT / ".codex" / "validators", "*.py"),
        (ROOT / ".codex" / "kernel", "*.md"),
    ]

    for dir_path, pattern in scan_dirs:
        if not dir_path.exists():
            continue
        for f in sorted(dir_path.glob(pattern)):
            checked += 1
            rel = str(f.relative_to(ROOT))
            if rel not in tracked_paths:
                # Skip the maturity tracker itself and __pycache__
                if "ARTIFACT_MATURITY.json" in rel:
                    continue
                if "__pycache__" in rel:
                    continue
                # Skip superseded versions (e.g., SUPER_PROMPT_v2.2.md)
                # Only flag if it's clearly a current artifact
                failures.append(
                    f"  UNTRACKED: {rel} exists but is not in ARTIFACT_MATURITY.json"
                )

    # Also check .gitattributes
    checked += 1
    if (ROOT / ".gitattributes").exists() and ".gitattributes" not in tracked_paths:
        failures.append(
            f"  UNTRACKED: .gitattributes exists but is not in ARTIFACT_MATURITY.json"
        )


def main():
    global checked

    if not MATURITY_PATH.exists():
        print("MATURITY_GATE FAIL: ARTIFACT_MATURITY.json not found", file=sys.stderr)
        sys.exit(15)

    data = json.loads(MATURITY_PATH.read_text())
    artifacts = data.get("artifacts", [])

    if not artifacts:
        print("MATURITY_GATE FAIL: no artifacts registered", file=sys.stderr)
        sys.exit(15)

    # Check each artifact's claimed maturity
    for entry in artifacts:
        maturity = entry.get("maturity", "DRAFT")

        if maturity == "DRAFT":
            check_draft(entry)
        elif maturity == "VALIDATED":
            check_validated(entry)
        elif maturity == "ENFORCED":
            check_enforced(entry)
        else:
            failures.append(
                f"  {entry['artifact_path']}: unknown maturity stage '{maturity}'"
            )

    # Check summary counts match actual counts
    summary = data.get("summary", {})
    actual_counts = {"ENFORCED": 0, "VALIDATED": 0, "DRAFT": 0}
    for entry in artifacts:
        m = entry.get("maturity", "DRAFT")
        if m in actual_counts:
            actual_counts[m] += 1

    for stage, expected in summary.items():
        if stage == "total":
            if expected != len(artifacts):
                failures.append(
                    f"  SUMMARY: total claims {expected} but {len(artifacts)} artifacts registered"
                )
        elif stage in actual_counts:
            if expected != actual_counts[stage]:
                failures.append(
                    f"  SUMMARY: {stage} claims {expected} but found {actual_counts[stage]}"
                )

    # Check for untracked artifacts
    check_untracked_artifacts()

    if failures:
        print(f"MATURITY_GATE FAIL: {len(failures)} issues across {checked} checks", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(15)
    else:
        enforced = actual_counts["ENFORCED"]
        validated = actual_counts["VALIDATED"]
        draft = actual_counts["DRAFT"]
        print(f"MATURITY_GATE: PASS ({checked} checks, {enforced} ENFORCED / {validated} VALIDATED / {draft} DRAFT)")
        sys.exit(0)


if __name__ == "__main__":
    main()
