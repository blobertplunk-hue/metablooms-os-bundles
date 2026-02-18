# ECL:
#   id: MPP.S6.TEST
#   role: gate
#   owns: [test gate — correctness, coverage, and output quality are verified here]
#   does_not: [write tests, fix code, interpret test output for correctness]
#   inputs: [turn_dir: str]
#   outputs: [StageResult with coverage, output quality, and regression check results]
#   side_effects: [filesystem — writes s6_test_receipt.json, runs pytest subprocess]
#   failure_modes: [TESTS_MISSING, COVERAGE_BELOW_THRESHOLD, OUTPUT_QUALITY_FAIL,
#                   REGRESSION_DETECTED, TEST_RUNNER_ERROR]
#   invariants: [passes only when all tests pass AND coverage meets threshold AND output quality passes]
#   evidence: [receipts/s6_test_receipt.json, tests/coverage_report.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
Stage 6 — TEST: Explicit Test Gate

Intent:
    Evidence that the code does exactly what it claims. No behavior
    survives without a test. Output quality is tested, not just logic.
    The CDR aesthetic contract is enforced on all produced output.

Scope:
    Discovers and runs the test suite. Checks coverage threshold.
    Validates that every MMD edge case has a corresponding test.
    Validates output quality against the CDR aesthetic contract.

Non-Goals:
    Does not write tests. Does not fix code. Does not interpret
    whether passing tests mean the code is "right" — only that
    the claimed behaviors are proven.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from mpp.stages import Issue, Severity, StageID, StageResult

COVERAGE_THRESHOLD_DEFAULT = 90  # percent


def run(turn_dir: str) -> StageResult:
    root      = Path(turn_dir)
    issues    = []
    artifacts = []

    # ---- 1. Check tests directory exists ------------------------------------
    tests_dir = root / "tests"
    if not tests_dir.exists() or not any(tests_dir.rglob("test_*.py")):
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/",
            description = "No test files (test_*.py) found. Tests are mandatory.",
            remediation = (
                "Create tests/ directory with at least one test_*.py file. "
                "Every claimed behavior in the MMD report must have a test."
            ),
        ))
        _write_receipt(root, passed=False, coverage=0, tests_run=0)
        return StageResult(stage=StageID.TEST, passed=False, issues=issues,
                           notes="BLOCKED: no test files found.")

    # ---- 2. Validate edge case test coverage --------------------------------
    issues += _check_edge_case_coverage(root)

    # ---- 3. Run pytest with coverage ----------------------------------------
    run_result = _run_pytest(root)
    artifacts.append("tests/")

    if run_result["error"]:
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/",
            description = f"Test runner error: {run_result['error']}",
            remediation = "Ensure pytest is installed and test files are importable.",
        ))

    if not run_result.get("all_passed", False):
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/",
            description = f"{run_result.get('failed', '?')} test(s) failed.",
            remediation = "Fix failing tests before this stage can pass.",
        ))

    coverage = run_result.get("coverage_pct", 0)
    threshold = _load_coverage_threshold(root)
    if coverage < threshold:
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/coverage_report.json",
            description = f"Coverage is {coverage:.1f}% — below the {threshold}% threshold.",
            remediation = (
                f"Add tests to bring coverage to {threshold}%. "
                "Focus on the MMD edge cases and critical-path functions."
            ),
        ))

    # ---- 4. Output quality check --------------------------------------------
    issues += _check_output_quality(root)

    # ---- 5. Regression check ------------------------------------------------
    issues += _check_regression(root, run_result)

    passed = not any(i.severity in (Severity.CRITICAL, Severity.HIGH) for i in issues)
    notes  = "PASSED" if passed else \
             f"BLOCKED: {sum(1 for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH))} issue(s)."
    _write_receipt(root, passed=passed, coverage=coverage,
                   tests_run=run_result.get("tests_run", 0))

    return StageResult(
        stage     = StageID.TEST,
        passed    = passed,
        artifacts = artifacts,
        issues    = issues,
        notes     = notes,
    )


# ---- Sub-checks -------------------------------------------------------------

def _check_edge_case_coverage(root: Path) -> List[Issue]:
    """Every MMD edge case should have a corresponding test in tests/edge_cases/."""
    issues  = []
    mmd     = _load_json(root / "mmd" / "MMD_REPORT.json") or {}
    ec_list = mmd.get("edge_cases", [])
    if not ec_list:
        return issues  # MMD stage already flagged this

    ec_dir = root / "tests" / "edge_cases"
    if not ec_dir.exists():
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/edge_cases/",
            description = f"{len(ec_list)} edge cases in MMD_REPORT but tests/edge_cases/ does not exist.",
            remediation = "Create tests/edge_cases/ and write a test for each MMD edge case.",
        ))
        return issues

    test_files = list(ec_dir.rglob("test_*.py"))
    if len(test_files) < len(ec_list):
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/edge_cases/",
            description = (
                f"{len(ec_list)} edge cases documented in MMD but only "
                f"{len(test_files)} edge case test file(s) found."
            ),
            remediation = "Add one test per MMD edge case. Each test file should reference its edge case ID.",
        ))
    return issues


def _run_pytest(root: Path) -> Dict[str, Any]:
    """Run pytest with coverage. Returns a summary dict."""
    coverage_report = root / "tests" / "coverage_report.json"
    cmd = [
        sys.executable, "-m", "pytest",
        str(root / "tests"),
        "--tb=no", "-q",
        f"--cov={root}",
        "--cov-report=json:" + str(coverage_report),
        "--no-header",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=str(root)
        )
        output = proc.stdout + proc.stderr
        failed  = _parse_pytest_failures(output)
        passed  = proc.returncode == 0
        cov_pct = _parse_coverage(coverage_report)
        # Count tests
        tests_run = _parse_tests_run(output)
        return {
            "all_passed":   passed,
            "failed":       failed,
            "tests_run":    tests_run,
            "coverage_pct": cov_pct,
            "error":        None,
        }
    except subprocess.TimeoutExpired:
        return {"all_passed": False, "error": "Pytest timed out after 120s.",
                "coverage_pct": 0, "tests_run": 0, "failed": "?"}
    except FileNotFoundError:
        return {"all_passed": False, "error": "pytest not found. Install with: pip install pytest pytest-cov",
                "coverage_pct": 0, "tests_run": 0, "failed": "?"}


def _check_output_quality(root: Path) -> List[Issue]:
    """Validate that OUTPUT_QUALITY_REPORT.md exists and references the aesthetic contract."""
    issues   = []
    report   = root / "tests" / "OUTPUT_QUALITY_REPORT.md"
    contract = root / "cdr" / "AESTHETIC_CONTRACT.json"

    if not report.exists():
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/OUTPUT_QUALITY_REPORT.md",
            description = "OUTPUT_QUALITY_REPORT.md is missing.",
            remediation = (
                "Create tests/OUTPUT_QUALITY_REPORT.md documenting how each "
                "user-visible output meets the CDR aesthetic contract. "
                "At minimum: confirm output_format and naming_style are honored."
            ),
        ))
        return issues

    report_text = report.read_text(encoding="utf-8", errors="replace")
    if not report_text.strip():
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "tests/OUTPUT_QUALITY_REPORT.md",
            description = "OUTPUT_QUALITY_REPORT.md is empty.",
            remediation = "Document how output meets the CDR aesthetic contract.",
        ))
    elif "AESTHETIC_CONTRACT" not in report_text and "aesthetic" not in report_text.lower():
        issues.append(Issue(
            severity    = Severity.MEDIUM,
            location    = "tests/OUTPUT_QUALITY_REPORT.md",
            description = "OUTPUT_QUALITY_REPORT.md does not reference the aesthetic contract.",
            remediation = "Add a section confirming output_format from AESTHETIC_CONTRACT.json is satisfied.",
        ))
    return issues


def _check_regression(root: Path, run_result: Dict[str, Any]) -> List[Issue]:
    """Compare against the last certified run's test count. Decline = regression."""
    issues = []
    cert_path = root / "MPP_CERTIFICATE.json"
    if not cert_path.exists():
        return issues  # First run — no prior baseline

    cert = _load_json(cert_path)
    if not isinstance(cert, dict):
        return issues

    prior_entries = cert.get("entries", [])
    if not prior_entries:
        return issues

    last_run      = prior_entries[-1]
    prior_tests   = last_run.get("tests_run", 0)
    current_tests = run_result.get("tests_run", 0)

    if current_tests < prior_tests:
        issues.append(Issue(
            severity    = Severity.HIGH,
            location    = "MPP_CERTIFICATE.json",
            description = (
                f"Regression: {current_tests} tests run vs {prior_tests} in last certified run. "
                "Tests were removed or became non-discoverable."
            ),
            remediation = "Restore the missing tests or justify their removal in the CDR delta proposal.",
        ))
    return issues


# ---- Helpers ----------------------------------------------------------------

def _load_coverage_threshold(root: Path) -> int:
    cfg_path = root / "mpp_config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return int(cfg.get("coverage_threshold", COVERAGE_THRESHOLD_DEFAULT))
    except (OSError, json.JSONDecodeError, ValueError):
        return COVERAGE_THRESHOLD_DEFAULT


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _parse_pytest_failures(output: str) -> int:
    import re
    m = re.search(r'(\d+) failed', output)
    return int(m.group(1)) if m else 0


def _parse_tests_run(output: str) -> int:
    import re
    m = re.search(r'(\d+) passed', output)
    return int(m.group(1)) if m else 0


def _parse_coverage(report_path: Path) -> float:
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        return float(data.get("totals", {}).get("percent_covered", 0))
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return 0.0


def _write_receipt(root: Path, *, passed: bool, coverage: float, tests_run: int) -> None:
    import datetime
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "stage":       "S6_TEST",
        "passed":      passed,
        "tests_run":   tests_run,
        "coverage_pct": round(coverage, 2),
        "time_utc":    datetime.datetime.utcnow().isoformat() + "Z",
    }
    (receipts / "s6_test_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
