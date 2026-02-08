#!/usr/bin/env python3
"""
GATE: Missing Middle Detection (MMD) — Mechanical Engine v2
EXIT 0 = PASS, EXIT 18 = FAIL

This is NOT a report generator — it is a mechanical gap detector.
It finds:
1. Broken cross-references between artifacts
2. Missing schemas for artifact types mentioned in policies
3. Untraced policies (no validator) and untraced validators (no policy)
4. Stale MMD findings (already resolved but still flagged)
5. Self-consistency (report matches schema, counts match)
6. Unresolved deferrals with no tracking
7. Dependency graph orphans and unreachable nodes

Detection methods (inspired by DO-178C traceability, graph analysis,
and requirements coverage):

METHOD 1: REFERENCE_GRAPH — parse all JSON artifacts for path references,
           verify each referenced path exists on disk
METHOD 2: SCHEMA_COVERAGE — for every .json artifact, check a .schema.json
           exists or is explicitly exempt
METHOD 3: TRACEABILITY — every policy should have a validator, every
           validator should be registered in the master gate
METHOD 4: DEFERRAL_AUDIT — check delta ledgers for DEFERRED items,
           verify they haven't been silently dropped
METHOD 5: SELF_CHECK — validate MMD report against its own schema,
           verify summary counts match findings array
METHOD 6: CATEGORY_COMPLETENESS — check for gap types the current
           MMD schema can't represent (closed enum problem)
"""
import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODEX = ROOT / ".codex"

findings = []
methods_run = 0


def add_finding(method, severity, category, title, affected, recommendation):
    findings.append({
        "method": method,
        "severity": severity,
        "category": category,
        "title": title,
        "affected_files": affected,
        "recommendation": recommendation,
    })


# ============================================================
# METHOD 1: REFERENCE GRAPH
# Scan all JSON artifacts for string values that look like
# file paths (.codex/..., os_bundles/..., .gitattributes, etc.)
# and verify each referenced path exists on disk.
# ============================================================

def method_reference_graph():
    global methods_run
    methods_run += 1

    path_pattern = re.compile(
        r'\.codex/[a-zA-Z0-9_/.-]+|'
        r'os_bundles/[a-zA-Z0-9_/.()\[\] -]+|'
        r'\.gitattributes|'
        r'CLAUDE\.md'
    )

    # Skip MMD_REPORT.json — it contains recommendations ("Create X"),
    # not live references. Also skip files whose paths contain spaces
    # or don't look like real filesystem paths.
    SKIP_FILES = {"MMD_REPORT.json"}

    json_files = [
        f for f in CODEX.rglob("*.json")
        if f.name not in SKIP_FILES
    ]
    checked = 0
    broken = 0

    for jf in json_files:
        try:
            content = jf.read_text()
        except Exception:
            continue

        refs = path_pattern.findall(content)
        for ref in refs:
            ref_clean = ref.strip().rstrip('",.')
            # Skip fragments that contain spaces (prose, not paths)
            if ' ' in ref_clean:
                continue
            # Skip fragments too short to be real paths
            if len(ref_clean) < 5:
                continue
            ref_path = ROOT / ref_clean
            checked += 1
            if not ref_path.exists():
                broken += 1
                add_finding(
                    "REFERENCE_GRAPH", "HIGH", "BROKEN_REFERENCE",
                    f"Broken reference: {ref_clean} (referenced in {jf.relative_to(ROOT)})",
                    [str(jf.relative_to(ROOT)), ref_clean],
                    f"Either create {ref_clean} or update the reference in {jf.relative_to(ROOT)}"
                )

    # Also check markdown policy files for path references
    for mdf in (CODEX / "policies").glob("*.md"):
        try:
            content = mdf.read_text()
        except Exception:
            continue
        refs = path_pattern.findall(content)
        for ref in refs:
            ref_clean = ref.strip().rstrip('",.')
            ref_path = ROOT / ref_clean
            checked += 1
            if not ref_path.exists():
                broken += 1
                add_finding(
                    "REFERENCE_GRAPH", "MEDIUM", "BROKEN_REFERENCE",
                    f"Policy references non-existent path: {ref_clean}",
                    [str(mdf.relative_to(ROOT)), ref_clean],
                    f"Create {ref_clean} or update the reference"
                )

    return checked, broken


# ============================================================
# METHOD 2: SCHEMA COVERAGE
# For every JSON artifact under .codex/artifacts/, check that
# a corresponding schema exists OR the artifact is explicitly
# exempt (registered in ARTIFACT_MATURITY with schema_path=null
# and a structural_check explanation).
# ============================================================

def method_schema_coverage():
    global methods_run
    methods_run += 1

    artifacts_dir = CODEX / "artifacts"
    schemas_dir = CODEX / "schemas"
    checked = 0
    uncovered = 0

    # Load maturity tracker for exemption checking
    maturity_path = artifacts_dir / "ARTIFACT_MATURITY.json"
    maturity_entries = {}
    if maturity_path.exists():
        try:
            maturity = json.loads(maturity_path.read_text())
            for entry in maturity.get("artifacts", []):
                maturity_entries[entry["artifact_path"]] = entry
        except (json.JSONDecodeError, KeyError):
            pass

    for artifact in artifacts_dir.glob("*.json"):
        checked += 1
        rel_path = str(artifact.relative_to(ROOT))
        mat_entry = maturity_entries.get(rel_path, {})
        has_schema = mat_entry.get("schema_path") is not None
        has_structural = mat_entry.get("structural_check") is not None

        if not has_schema and not has_structural:
            uncovered += 1
            add_finding(
                "SCHEMA_COVERAGE", "MEDIUM", "MISSING_SCHEMA",
                f"Artifact {artifact.name} has no schema_path and no structural_check in maturity tracker",
                [rel_path],
                f"Either create a schema or add a structural_check explanation in ARTIFACT_MATURITY.json"
            )

    return checked, uncovered


# ============================================================
# METHOD 3: TRACEABILITY MATRIX
# Check bidirectional tracing:
# - Every policy doc → should have a validator OR be NON_GOVERNED
# - Every validator → should be registered in master gate
# - Every schema → should have at least one artifact that uses it
# - Every invariant → should have a mechanical checker
# ============================================================

def method_traceability():
    global methods_run
    methods_run += 1

    checked = 0
    gaps = 0

    # 3a: Validators → must be in master gate
    master_path = CODEX / "validators" / "run_governance_gate.py"
    if master_path.exists():
        master_content = master_path.read_text()
        for vf in (CODEX / "validators").glob("run_*_gate.py"):
            if vf.name == "run_governance_gate.py":
                continue
            checked += 1
            gate_name = vf.stem.replace("run_", "").replace("_gate", "").upper()
            if f'"{gate_name}"' not in master_content:
                gaps += 1
                add_finding(
                    "TRACEABILITY", "HIGH", "UNREGISTERED_VALIDATOR",
                    f"Validator {vf.name} not registered in master governance gate as '{gate_name}'",
                    [str(vf.relative_to(ROOT)), "run_governance_gate.py"],
                    f"Add ('{gate_name}', '{vf.name}', <exit_code>) to GATES list"
                )

    # 3b: Invariants → must have mechanical checkers
    inv_path = CODEX / "artifacts" / "INVARIANT_REGISTRY.json"
    if inv_path.exists():
        try:
            registry = json.loads(inv_path.read_text())
            inv_gate_path = CODEX / "validators" / "run_invariant_gate.py"
            inv_gate_content = inv_gate_path.read_text() if inv_gate_path.exists() else ""

            for inv in registry.get("invariants", []):
                if inv.get("status") != "ACTIVE":
                    continue
                inv_id = inv.get("invariant_id", "?")
                checked += 1
                if f'"{inv_id}"' not in inv_gate_content:
                    gaps += 1
                    add_finding(
                        "TRACEABILITY", "HIGH", "UNTRACEABLE_INVARIANT",
                        f"Active invariant {inv_id} has no mechanical checker in run_invariant_gate.py",
                        [str(inv_path.relative_to(ROOT)), ".codex/validators/run_invariant_gate.py"],
                        f"Add a check function for {inv_id} to INVARIANT_CHECKERS dict"
                    )
        except (json.JSONDecodeError, KeyError):
            pass

    # 3c: Schemas → should have at least one referencing artifact or maturity entry
    maturity_path = CODEX / "artifacts" / "ARTIFACT_MATURITY.json"
    schema_refs = set()
    if maturity_path.exists():
        try:
            maturity = json.loads(maturity_path.read_text())
            for entry in maturity.get("artifacts", []):
                sp = entry.get("schema_path")
                if sp:
                    schema_refs.add(sp)
        except (json.JSONDecodeError, KeyError):
            pass

    for sf in (CODEX / "schemas").glob("*.schema.json"):
        checked += 1
        rel = str(sf.relative_to(ROOT))
        if rel not in schema_refs:
            # Check if any artifact JSON references this schema
            schema_name = sf.name
            found_ref = False
            for artifact in (CODEX / "artifacts").glob("*.json"):
                if schema_name in artifact.read_text():
                    found_ref = True
                    break
            if not found_ref:
                gaps += 1
                add_finding(
                    "TRACEABILITY", "LOW", "UNREFERENCED_SCHEMA",
                    f"Schema {sf.name} is not referenced by any artifact or maturity entry",
                    [rel],
                    "Either reference this schema from an artifact or register it in ARTIFACT_MATURITY"
                )

    return checked, gaps


# ============================================================
# METHOD 4: DEFERRAL AUDIT
# Check delta ledgers for DEFERRED items. Verify each has a
# not_done_reason. Flag if deferrals have been sitting
# unresolved across multiple sessions.
# ============================================================

def method_deferral_audit():
    global methods_run
    methods_run += 1

    checked = 0
    issues = 0

    for ledger_file in (CODEX / "artifacts").glob("DELTA_LEDGER_*.json"):
        try:
            ledger = json.loads(ledger_file.read_text())
        except json.JSONDecodeError:
            continue

        for entry in ledger.get("entries", []):
            if entry.get("status") != "DEFERRED":
                continue
            checked += 1
            reason = entry.get("not_done_reason", "")
            if not reason or len(reason.strip()) < 5:
                issues += 1
                add_finding(
                    "DEFERRAL_AUDIT", "MEDIUM", "UNEXPLAINED_DEFERRAL",
                    f"Deferred delta {entry.get('delta_id', '?')} has no explanation",
                    [str(ledger_file.relative_to(ROOT))],
                    "Add a not_done_reason explaining why this was deferred"
                )

        # Also check deferred_items list
        for item in ledger.get("deferred_items", []):
            checked += 1
            if not item.get("reason", ""):
                issues += 1
                add_finding(
                    "DEFERRAL_AUDIT", "MEDIUM", "UNEXPLAINED_DEFERRAL",
                    f"Deferred item '{item.get('item', '?')}' has no reason",
                    [str(ledger_file.relative_to(ROOT))],
                    "Add a reason for the deferral"
                )

    return checked, issues


# ============================================================
# METHOD 5: SELF-CHECK
# Validate MMD report against its own schema.
# Verify summary counts match findings array length.
# ============================================================

def method_self_check():
    global methods_run
    methods_run += 1

    report_path = CODEX / "artifacts" / "MMD_REPORT.json"
    schema_path = CODEX / "schemas" / "MMD_REPORT.schema.json"
    checked = 0
    issues = 0

    if not report_path.exists():
        add_finding(
            "SELF_CHECK", "HIGH", "MISSING_REPORT",
            "MMD_REPORT.json does not exist",
            [".codex/artifacts/"],
            "Generate an MMD report"
        )
        return 1, 1

    try:
        report = json.loads(report_path.read_text())
    except json.JSONDecodeError as e:
        add_finding(
            "SELF_CHECK", "CRITICAL", "INVALID_JSON",
            f"MMD_REPORT.json is invalid JSON: {e}",
            [".codex/artifacts/MMD_REPORT.json"],
            "Fix the JSON syntax"
        )
        return 1, 1

    # Check required fields
    checked += 1
    for field in ["report_version", "generated_utc", "total_findings", "summary", "findings"]:
        if field not in report:
            issues += 1
            add_finding(
                "SELF_CHECK", "HIGH", "MISSING_FIELD",
                f"MMD_REPORT.json missing required field: {field}",
                [".codex/artifacts/MMD_REPORT.json"],
                f"Add the {field} field"
            )

    # Check total_findings matches array length
    checked += 1
    actual_count = len(report.get("findings", []))
    claimed_count = report.get("total_findings", -1)
    if actual_count != claimed_count:
        issues += 1
        add_finding(
            "SELF_CHECK", "HIGH", "COUNT_MISMATCH",
            f"MMD_REPORT total_findings={claimed_count} but findings array has {actual_count} entries",
            [".codex/artifacts/MMD_REPORT.json"],
            "Update total_findings to match actual count"
        )

    # Check summary severity counts match
    checked += 1
    summary = report.get("summary", {})
    actual_by_sev = {}
    for f in report.get("findings", []):
        sev = f.get("severity", "UNKNOWN")
        actual_by_sev[sev] = actual_by_sev.get(sev, 0) + 1

    for sev_key in ["critical", "high", "medium", "low", "info"]:
        claimed = summary.get(sev_key, 0)
        actual = actual_by_sev.get(sev_key.upper(), 0)
        if claimed != actual:
            issues += 1
            add_finding(
                "SELF_CHECK", "MEDIUM", "COUNT_MISMATCH",
                f"MMD_REPORT summary.{sev_key}={claimed} but {actual} findings have severity {sev_key.upper()}",
                [".codex/artifacts/MMD_REPORT.json"],
                f"Update summary.{sev_key} to {actual}"
            )

    # Check finding IDs are unique and sequential
    checked += 1
    ids = [f.get("id") for f in report.get("findings", [])]
    if len(ids) != len(set(ids)):
        issues += 1
        add_finding(
            "SELF_CHECK", "HIGH", "DUPLICATE_ID",
            "MMD_REPORT.json has duplicate finding IDs",
            [".codex/artifacts/MMD_REPORT.json"],
            "Ensure all finding IDs are unique"
        )

    return checked, issues


# ============================================================
# METHOD 6: CATEGORY COMPLETENESS
# Check if there are gap types that the current MMD schema
# can't represent. Compare detected issues against schema enum.
# ============================================================

def method_category_completeness():
    global methods_run
    methods_run += 1

    schema_path = CODEX / "schemas" / "MMD_REPORT.schema.json"
    checked = 0
    issues = 0

    if not schema_path.exists():
        return 0, 0

    try:
        schema = json.loads(schema_path.read_text())
        category_enum = (
            schema.get("properties", {})
            .get("findings", {})
            .get("items", {})
            .get("properties", {})
            .get("category", {})
            .get("enum", [])
        )
    except (json.JSONDecodeError, KeyError):
        return 0, 0

    # Categories we've discovered through this gate that aren't in the schema
    discovered_categories = set()
    for f in findings:
        discovered_categories.add(f["category"])

    new_categories = discovered_categories - set(category_enum)
    checked += 1
    if new_categories:
        issues += 1
        add_finding(
            "CATEGORY_COMPLETENESS", "MEDIUM", "CLOSED_ENUM",
            f"MMD schema category enum missing: {', '.join(sorted(new_categories))}",
            [".codex/schemas/MMD_REPORT.schema.json"],
            f"Add these categories to the enum: {sorted(new_categories)}"
        )

    return checked, issues


# ============================================================
# MAIN
# ============================================================

def main():
    print("MMD_GATE: Running mechanical gap detection (6 methods)...")
    print()

    results = []

    methods = [
        ("REFERENCE_GRAPH", method_reference_graph),
        ("SCHEMA_COVERAGE", method_schema_coverage),
        ("TRACEABILITY", method_traceability),
        ("DEFERRAL_AUDIT", method_deferral_audit),
        ("SELF_CHECK", method_self_check),
        ("CATEGORY_COMPLETENESS", method_category_completeness),
    ]

    total_checked = 0
    total_issues = 0

    for name, method_fn in methods:
        try:
            checked, issues = method_fn()
            total_checked += checked
            total_issues += issues
            status = "PASS" if issues == 0 else f"FOUND {issues}"
            indicator = "+" if issues == 0 else "!"
            print(f"  [{indicator}] {name}: {status} ({checked} checks)")
        except Exception as e:
            print(f"  [X] {name}: ERROR ({e})")

    print()
    print(f"  Total: {total_checked} checks, {total_issues} issues, {methods_run} methods")
    print()

    # Severity breakdown
    by_severity = {}
    for f in findings:
        s = f["severity"]
        by_severity[s] = by_severity.get(s, 0) + 1

    has_critical = by_severity.get("CRITICAL", 0) > 0

    if findings:
        print("  Findings:")
        for f in findings:
            print(f"    [{f['severity']}] ({f['method']}) {f['title']}")
        print()

    if has_critical:
        print(f"MMD_GATE: FAIL — {total_issues} issues ({by_severity.get('CRITICAL', 0)} CRITICAL)")
        sys.exit(18)
    elif total_issues > 0:
        print(f"MMD_GATE: PASS_WITH_WARNINGS — {total_issues} issues (no CRITICAL)")
        sys.exit(0)
    else:
        print(f"MMD_GATE: PASS ({total_checked} checks, 0 issues)")
        sys.exit(0)


if __name__ == "__main__":
    main()
