# ECL:
#   id: MPP.S5.ECL
#   role: gate
#   owns: [code clarity enforcement — every module is idiot-proof or it doesn't ship]
#   does_not: [execute code, run tests, fix clarity violations]
#   inputs: [turn_dir: str]
#   outputs: [StageResult with per-file clarity issues]
#   side_effects: [filesystem — writes s5_ecl_receipt.json, writes ecl/ECL_SCAN_REPORT.json]
#   failure_modes: [MISSING_ECL_HEADER, BAD_HEADER_FIELD, AESTHETIC_VIOLATION,
#                   BEAUTY_AUDIT_FAIL, NO_SOURCE_FILES]
#   invariants: [all critical-path files must pass at 100%; medium issues warn but don't block]
#   evidence: [receipts/s5_ecl_receipt.json, ecl/ECL_SCAN_REPORT.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
Stage 5 — ECL: Extraordinary Code Law

Intent:
    Make every module idiot-proof to any reader — human or machine.
    Clarity is not a courtesy; it is a structural property. If a
    competent reader cannot understand a function in 30 seconds without
    external context, the function violates ECL.

Scope:
    Scans all .py files in turn_dir for ECL headers, validates header
    completeness, and runs the beauty audit against the CDR aesthetic contract.
    Critical-path roles (entrypoint, gate, orchestrator) must pass at 100%.

Non-Goals:
    Does not run, interpret, or execute code.
    Does not evaluate logic correctness — only structural clarity.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mpp.stages import Issue, Severity, StageID, StageResult

CRITICAL_PATH_ROLES = {"entrypoint", "orchestrator", "gate"}

ECL_HEADER_REQUIRED_KEYS = [
    "id", "role", "owns", "does_not", "inputs", "outputs",
    "side_effects", "failure_modes", "invariants", "evidence",
]

VALID_ROLES = {
    "entrypoint", "orchestrator", "gate", "validator",
    "adapter", "schema", "io", "tool", "library",
}

# Beauty rules (enforced against aesthetic contract, with safe defaults)
BEAUTY_DEFAULT_MAX_LINES    = 60
BEAUTY_DEFAULT_MAX_NESTING  = 4
BEAUTY_DEFAULT_MAX_LINE_LEN = 120

VAGUE_NAMES = {"x", "y", "z", "tmp", "temp", "data", "result", "res", "val",
               "item", "obj", "foo", "bar", "baz", "stuff", "thing"}


def run(turn_dir: str) -> StageResult:
    root      = Path(turn_dir)
    contract  = _load_aesthetic_contract(root)
    issues    = []

    py_files = _collect_python_files(root)
    if not py_files:
        issues.append(Issue(
            severity    = Severity.MEDIUM,
            location    = str(root),
            description = "No .py files found in turn directory. ECL has nothing to validate.",
            remediation = "Ensure source files are present in the turn directory.",
        ))
        _write_receipt(root, passed=True, scanned=0, issues=[])
        return StageResult(stage=StageID.ECL, passed=True, issues=issues,
                           notes="WARN: no source files found.")

    scan_results = []
    for py_file in py_files:
        file_issues = _scan_file(py_file, root, contract)
        issues += file_issues
        scan_results.append({
            "file":   str(py_file.relative_to(root)),
            "issues": [i.severity.value + ": " + i.description for i in file_issues],
        })

    _write_ecl_scan_report(root, scan_results)

    critical_path_failures = [
        i for i in issues
        if i.severity == Severity.HIGH and "critical-path" in i.description
    ]
    blocking = [i for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH)]

    passed = len(blocking) == 0
    notes  = "PASSED" if passed else f"BLOCKED: {len(blocking)} clarity violation(s) on critical-path files."
    _write_receipt(root, passed=passed, scanned=len(py_files), issues=blocking)

    return StageResult(
        stage     = StageID.ECL,
        passed    = passed,
        artifacts = ["ecl/ECL_SCAN_REPORT.json"],
        issues    = issues,
        notes     = notes,
    )


# ---- File scanner -----------------------------------------------------------

def _scan_file(path: Path, root: Path, contract: Dict[str, Any]) -> List[Issue]:
    issues = []
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [Issue(Severity.HIGH, str(path), "Cannot read file.", "Check file permissions.")]

    relative = str(path.relative_to(root))

    header, role = _parse_ecl_header(source)
    if header is None:
        sev = Severity.HIGH if role in CRITICAL_PATH_ROLES else Severity.MEDIUM
        issues.append(Issue(
            severity    = sev,
            location    = relative,
            description = f"No ECL header found. {'critical-path' if sev == Severity.HIGH else 'non-critical'} file.",
            remediation = "Add an ECL YAML block comment at the top of the file. See MPP_SPEC.md.",
        ))
        return issues  # Can't do beauty audit without knowing the role

    for key in ECL_HEADER_REQUIRED_KEYS:
        if key not in header:
            sev = Severity.HIGH if role in CRITICAL_PATH_ROLES else Severity.MEDIUM
            issues.append(Issue(
                severity    = sev,
                location    = f"{relative}::ECL::{key}",
                description = f"ECL header missing required field '{key}'. {'critical-path' if sev == Severity.HIGH else ''}",
                remediation = f"Add '# {key}: ...' to the ECL header block.",
            ))

    if role and role not in VALID_ROLES:
        issues.append(Issue(
            severity    = Severity.MEDIUM,
            location    = f"{relative}::ECL::role",
            description = f"ECL role '{role}' is not a recognized role.",
            remediation = f"Use one of: {', '.join(sorted(VALID_ROLES))}.",
        ))

    issues += _beauty_audit(source, relative, role, contract)
    return issues


def _beauty_audit(source: str, location: str, role: Optional[str],
                  contract: Dict[str, Any]) -> List[Issue]:
    """Check aesthetic contract compliance: line length, nesting, naming."""
    issues    = []
    max_lines = int(contract.get("max_function_lines", BEAUTY_DEFAULT_MAX_LINES))
    max_nest  = int(contract.get("max_nesting_depth",  BEAUTY_DEFAULT_MAX_NESTING))
    max_len   = int(contract.get("line_length_limit",  BEAUTY_DEFAULT_MAX_LINE_LEN))

    lines = source.splitlines()

    # Line length check
    for lineno, line in enumerate(lines, 1):
        if len(line) > max_len:
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = f"{location}:{lineno}",
                description = f"Line {lineno} is {len(line)} chars (limit {max_len}).",
                remediation = "Break the line or extract a named helper.",
            ))

    # Nesting depth (indentation proxy — 4 spaces per level)
    for lineno, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        depth  = indent // 4
        if depth > max_nest:
            issues.append(Issue(
                severity    = Severity.MEDIUM,
                location    = f"{location}:{lineno}",
                description = f"Nesting depth {depth} exceeds limit {max_nest}.",
                remediation = "Extract inner logic into a named helper function.",
            ))

    # Vague name detection in function signatures and assignments
    vague_found = set()
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        # Only check assignment-level names, not loop variables in tightly scoped comprehensions
        if re.search(r'\b(?:def\s+\w+\s*\()', stripped):
            for name in VAGUE_NAMES:
                if re.search(rf'\b{name}\b', stripped):
                    vague_found.add((lineno, name))

    for lineno, name in sorted(vague_found):
        issues.append(Issue(
            severity    = Severity.MEDIUM,
            location    = f"{location}:{lineno}",
            description = f"Vague name '{name}' in function signature. Names must say what a thing IS.",
            remediation = "Replace with an expressive name (e.g. 'parsed_record', 'user_id').",
        ))

    # Function length check
    issues += _check_function_lengths(source, location, max_lines)
    return issues


def _check_function_lengths(source: str, location: str, max_lines: int) -> List[Issue]:
    """Flag functions that exceed max_function_lines."""
    issues   = []
    in_func  = False
    func_start = 0
    func_name  = ""
    depth      = 0

    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        m = re.match(r'^def\s+(\w+)\s*\(', stripped)
        if m:
            if in_func and (lineno - func_start) > max_lines:
                issues.append(Issue(
                    severity    = Severity.MEDIUM,
                    location    = f"{location}:{func_start}",
                    description = f"Function '{func_name}' is {lineno - func_start} lines (limit {max_lines}).",
                    remediation = "Break into smaller named helpers. Each function should do one thing.",
                ))
            in_func    = True
            func_name  = m.group(1)
            func_start = lineno

    return issues


# ---- Helpers ----------------------------------------------------------------

def _parse_ecl_header(source: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extract the ECL YAML comment block from the top of a file."""
    header: Dict[str, Any] = {}
    in_ecl = False

    for line in source.splitlines():
        stripped = line.strip()
        if stripped == "# ECL:":
            in_ecl = True
            continue
        if in_ecl:
            if not stripped.startswith("#"):
                break
            content = stripped.lstrip("# ").lstrip("#").strip()
            m = re.match(r'^(\w+):\s*(.*)$', content)
            if m:
                header[m.group(1)] = m.group(2).strip()

    if not header:
        return None, None
    role = str(header.get("role", "")).strip().lower()
    return header, role


def _collect_python_files(root: Path) -> List[Path]:
    return [
        p for p in root.rglob("*.py")
        if "__pycache__" not in str(p) and ".git" not in str(p)
    ]


def _load_aesthetic_contract(root: Path) -> Dict[str, Any]:
    path = root / "cdr" / "AESTHETIC_CONTRACT.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_ecl_scan_report(root: Path, scan_results: List[Dict]) -> None:
    import datetime
    ecl_dir = root / "ecl"
    ecl_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "files_scanned": len(scan_results),
        "results":       scan_results,
    }
    (ecl_dir / "ECL_SCAN_REPORT.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


def _write_receipt(root: Path, *, passed: bool, scanned: int,
                   issues: List[Issue]) -> None:
    import datetime
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = {
        "stage":          "S5_ECL",
        "passed":         passed,
        "files_scanned":  scanned,
        "blocking_count": len(issues),
        "time_utc":       datetime.datetime.utcnow().isoformat() + "Z",
    }
    (receipts / "s5_ecl_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
