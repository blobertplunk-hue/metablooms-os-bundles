#!/usr/bin/env python3
"""
GATE: Preparation (Phase 2.75)
EXIT 0 = PASS, EXIT 19 = FAIL

Refuses execution unless the system is prepared. Checks:
1. MASTERY_DEFINITION.schema.json exists (the contract)
2. DECISION_RECORD.schema.json exists (architectural decisions are recordable)
3. LESSON_PROMOTION.schema.json exists (assimilation is possible)
4. MB_MASTER_SPEC_v1.md exists (the specification is documented)
5. All 3 schemas are valid JSON

This gate enforces Phase 4 of MB_MASTER_SPEC:
"No guessing. No good enough. No vibes. No execution without
defined mastery criteria."

In a live MPP run, this gate would also check:
- MASTERY_DEFINITION.json exists for the current task
- All knowledge_gaps have status != OPEN
- All success_criteria are defined
But those are runtime checks, not at-rest checks.
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODEX = ROOT / ".codex"

failures = []
checked = 0


def check_file(path, description):
    global checked
    checked += 1
    if not path.exists():
        failures.append(f"  {description}: {path.relative_to(ROOT)} not found")
        return False
    return True


def check_valid_json(path, description):
    global checked
    checked += 1
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            failures.append(f"  {description}: not a JSON object")
            return False
        if "title" not in data and "$schema" not in data:
            failures.append(f"  {description}: missing title or $schema field")
            return False
        return True
    except json.JSONDecodeError as e:
        failures.append(f"  {description}: invalid JSON: {e}")
        return False


def main():
    print("PREPARATION_GATE: Checking readiness for execution...")

    # 1. Master spec exists
    check_file(
        CODEX / "policies" / "MB_MASTER_SPEC_v1.md",
        "Master specification"
    )

    # 2. Mastery definition schema exists and is valid
    mastery_schema = CODEX / "schemas" / "MASTERY_DEFINITION.schema.json"
    if check_file(mastery_schema, "Mastery definition schema"):
        check_valid_json(mastery_schema, "Mastery definition schema")

    # 3. Decision record schema exists and is valid
    decision_schema = CODEX / "schemas" / "DECISION_RECORD.schema.json"
    if check_file(decision_schema, "Decision record schema"):
        check_valid_json(decision_schema, "Decision record schema")

    # 4. Lesson promotion schema exists and is valid
    lesson_schema = CODEX / "schemas" / "LESSON_PROMOTION.schema.json"
    if check_file(lesson_schema, "Lesson promotion schema"):
        check_valid_json(lesson_schema, "Lesson promotion schema")

    # 5. Verify master spec mentions all six phases
    spec_path = CODEX / "policies" / "MB_MASTER_SPEC_v1.md"
    if spec_path.exists():
        global checked
        checked += 1
        content = spec_path.read_text()
        required_phases = ["SURFACE", "DETECT", "PREPARE", "REFUSE", "EXECUTE", "ASSIMILATE"]
        missing_phases = [p for p in required_phases if p not in content]
        if missing_phases:
            failures.append(
                f"  Master spec missing phases: {', '.join(missing_phases)}"
            )

    if failures:
        print(f"PREPARATION_GATE FAIL: {len(failures)} issues across {checked} checks",
              file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(19)
    else:
        print(f"PREPARATION_GATE: PASS ({checked} checks)")
        sys.exit(0)


if __name__ == "__main__":
    main()
