#!/usr/bin/env python3
"""
GATE: Schema Validation
EXIT 0 = PASS, EXIT 10 = FAIL

Validates all JSON artifacts in .codex/ against their declared schemas.
"""
import sys
import json
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("SCHEMA_GATE FAIL: jsonschema not installed (pip install jsonschema)", file=sys.stderr)
    sys.exit(10)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / ".codex" / "schemas"
ARTIFACTS_DIR = ROOT / ".codex" / "artifacts"

# Map: artifact file -> schema file
ARTIFACT_SCHEMA_MAP = {
    ARTIFACTS_DIR / "BUNDLE_CATALOG.json": SCHEMA_DIR / "BUNDLE_ENTRY.schema.json",
    ARTIFACTS_DIR / "BUNDLE_LINEAGE.json": SCHEMA_DIR / "BUNDLE_LINEAGE.schema.json",
    ARTIFACTS_DIR / "MMD_REPORT.json": SCHEMA_DIR / "MMD_REPORT.schema.json",
}

failures = []
checked = 0


def validate_catalog(catalog_path, entry_schema_path):
    """BUNDLE_CATALOG has a .bundles array; each entry must match BUNDLE_ENTRY schema."""
    global checked
    schema = json.loads(entry_schema_path.read_text())
    catalog = json.loads(catalog_path.read_text())

    bundles = catalog.get("entries", catalog.get("bundles", []))
    if not bundles:
        failures.append(f"  {catalog_path.name}: 'bundles' array is empty or missing")
        return

    for i, entry in enumerate(bundles):
        checked += 1
        try:
            jsonschema.validate(instance=entry, schema=schema)
        except jsonschema.ValidationError as e:
            failures.append(
                f"  {catalog_path.name}[{i}] ({entry.get('filename', '?')}): {e.message}"
            )


def validate_lineage(lineage_path, schema_path):
    """Validate BUNDLE_LINEAGE against its schema."""
    global checked
    schema = json.loads(schema_path.read_text())
    data = json.loads(lineage_path.read_text())
    checked += 1
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        failures.append(f"  {lineage_path.name}: {e.message}")


def validate_mmd(mmd_path, schema_path):
    """Validate MMD_REPORT against its schema."""
    global checked
    schema = json.loads(schema_path.read_text())
    data = json.loads(mmd_path.read_text())
    checked += 1
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        failures.append(f"  {mmd_path.name}: {e.message}")


def validate_boot_receipt(receipt_path):
    """Basic structural checks on BOOT_RECEIPT (no separate schema yet)."""
    global checked
    checked += 1
    data = json.loads(receipt_path.read_text())
    required = ["receipt_type", "boot_version", "boot_file_sha256", "governance_frameworks"]
    missing = [k for k in required if k not in data]
    if missing:
        failures.append(f"  BOOT_RECEIPT.json: missing required fields: {missing}")


def validate_invariant_registry(registry_path):
    """Basic structural checks on INVARIANT_REGISTRY."""
    global checked
    checked += 1
    data = json.loads(registry_path.read_text())
    invariants = data.get("invariants", [])
    if not invariants:
        failures.append(f"  INVARIANT_REGISTRY.json: no invariants defined")
        return
    for i, inv in enumerate(invariants):
        checked += 1
        required = ["invariant_id", "severity", "title", "status"]
        missing = [k for k in required if k not in inv]
        if missing:
            failures.append(
                f"  INVARIANT_REGISTRY.json[{i}] ({inv.get('invariant_id', '?')}): missing {missing}"
            )


def main():
    global checked

    # 1. Validate catalog entries against BUNDLE_ENTRY schema
    cat_path = ARTIFACTS_DIR / "BUNDLE_CATALOG.json"
    entry_schema = SCHEMA_DIR / "BUNDLE_ENTRY.schema.json"
    if cat_path.exists() and entry_schema.exists():
        validate_catalog(cat_path, entry_schema)
    else:
        if not cat_path.exists():
            failures.append("  BUNDLE_CATALOG.json: FILE NOT FOUND")
        if not entry_schema.exists():
            failures.append("  BUNDLE_ENTRY.schema.json: FILE NOT FOUND")

    # 2. Validate lineage
    lin_path = ARTIFACTS_DIR / "BUNDLE_LINEAGE.json"
    lin_schema = SCHEMA_DIR / "BUNDLE_LINEAGE.schema.json"
    if lin_path.exists() and lin_schema.exists():
        validate_lineage(lin_path, lin_schema)
    elif not lin_path.exists():
        failures.append("  BUNDLE_LINEAGE.json: FILE NOT FOUND")

    # 3. Validate MMD report
    mmd_path = ARTIFACTS_DIR / "MMD_REPORT.json"
    mmd_schema = SCHEMA_DIR / "MMD_REPORT.schema.json"
    if mmd_path.exists() and mmd_schema.exists():
        validate_mmd(mmd_path, mmd_schema)
    elif not mmd_path.exists():
        failures.append("  MMD_REPORT.json: FILE NOT FOUND")

    # 4. Validate BOOT_RECEIPT
    receipt_path = ROOT / ".codex" / "receipts" / "BOOT_RECEIPT.json"
    if receipt_path.exists():
        validate_boot_receipt(receipt_path)
    else:
        failures.append("  BOOT_RECEIPT.json: FILE NOT FOUND")

    # 5. Validate INVARIANT_REGISTRY
    inv_path = ARTIFACTS_DIR / "INVARIANT_REGISTRY.json"
    if inv_path.exists():
        validate_invariant_registry(inv_path)
    else:
        failures.append("  INVARIANT_REGISTRY.json: FILE NOT FOUND")

    # 6. Validate all JSON files parse cleanly
    for json_file in (ROOT / ".codex").rglob("*.json"):
        checked += 1
        try:
            json.loads(json_file.read_text())
        except json.JSONDecodeError as e:
            failures.append(f"  {json_file.relative_to(ROOT)}: INVALID JSON: {e}")

    # Report
    if failures:
        print(f"SCHEMA_GATE FAIL: {len(failures)} errors across {checked} checks", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(10)
    else:
        print(f"SCHEMA_GATE: PASS ({checked} checks)")
        sys.exit(0)


if __name__ == "__main__":
    main()
