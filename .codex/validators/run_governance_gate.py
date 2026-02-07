#!/usr/bin/env python3
"""
MASTER GOVERNANCE GATE
EXIT 0 = ALL PASS, EXIT 1 = ONE OR MORE FAILED

Runs all governance validators in sequence. Collects results.
Fails hard if any gate fails.

Usage:
  python3 .codex/validators/run_governance_gate.py          # run all gates
  python3 .codex/validators/run_governance_gate.py --quick   # skip slow gates
"""
import sys
import subprocess
import time
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATORS_DIR = ROOT / ".codex" / "validators"

# Gates in execution order. Each tuple: (name, script, exit_code_on_fail)
GATES = [
    ("SCHEMA_VALIDATION", "run_schema_validation_gate.py", 10),
    ("STALENESS", "run_staleness_gate.py", 11),
    ("LFS_GAP", "run_lfs_gap_gate.py", 12),
    ("FORBIDDEN_LANGUAGE", "run_forbidden_language_gate.py", 13),
    ("INVARIANT", "run_invariant_gate.py", 14),
    ("MATURITY", "run_maturity_gate.py", 15),
]

# Gates that can be skipped with --quick
SLOW_GATES = set()  # none are slow currently, but ready for future


def run_gate(name, script):
    """Run a single gate. Returns (pass: bool, output: str, duration_ms: int)."""
    script_path = VALIDATORS_DIR / script
    if not script_path.exists():
        return False, f"  SCRIPT NOT FOUND: {script_path}", 0

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        duration = int((time.time() - start) * 1000)
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output, duration
    except subprocess.TimeoutExpired:
        duration = int((time.time() - start) * 1000)
        return False, f"  TIMEOUT after {duration}ms", duration
    except Exception as e:
        return False, f"  EXCEPTION: {e}", 0


def main():
    parser = argparse.ArgumentParser(description="Master Governance Gate")
    parser.add_argument("--quick", action="store_true", help="Skip slow gates")
    args = parser.parse_args()

    print("=" * 60)
    print("  GOVERNANCE GATE — MetaBlooms OS Bundles")
    print("=" * 60)
    print()

    results = []
    total_start = time.time()

    for name, script, expected_fail_code in GATES:
        if args.quick and name in SLOW_GATES:
            print(f"  [{name}] SKIPPED (--quick)")
            results.append((name, True, "SKIPPED", 0))
            continue

        passed, output, duration = run_gate(name, script)
        status = "PASS" if passed else "FAIL"
        indicator = "+" if passed else "X"
        print(f"  [{indicator}] {name}: {status} ({duration}ms)")
        if not passed:
            # Print failure details indented
            for line in output.splitlines():
                print(f"      {line}")
        results.append((name, passed, output, duration))

    total_duration = int((time.time() - total_start) * 1000)
    print()
    print("-" * 60)

    passed_count = sum(1 for _, p, _, _ in results if p)
    failed_count = len(results) - passed_count

    if failed_count == 0:
        print(f"  GOVERNANCE GATE: ALL PASS ({passed_count}/{len(results)} gates, {total_duration}ms)")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"  GOVERNANCE GATE: FAIL ({failed_count}/{len(results)} gates failed, {total_duration}ms)")
        print()
        print("  Failed gates:")
        for name, passed, output, _ in results:
            if not passed:
                print(f"    - {name}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
