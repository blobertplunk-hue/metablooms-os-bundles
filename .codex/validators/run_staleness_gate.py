#!/usr/bin/env python3
"""
GATE: Staleness Detection
EXIT 0 = PASS, EXIT 11 = FAIL

Checks:
1. BOOT_RECEIPT SHA-256 matches actual BOOT.md hash
2. BUNDLE_CATALOG covers every file in os_bundles/
3. BUNDLE_CATALOG has no entries for files that don't exist
"""
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
failures = []


def check_boot_sha():
    """Verify BOOT_RECEIPT.boot_file_sha256 matches actual BOOT.md."""
    receipt_path = ROOT / ".codex" / "receipts" / "BOOT_RECEIPT.json"
    boot_path = ROOT / ".codex" / "kernel" / "BOOT.md"

    if not receipt_path.exists():
        failures.append("  BOOT_RECEIPT.json: FILE NOT FOUND")
        return
    if not boot_path.exists():
        failures.append("  BOOT.md: FILE NOT FOUND")
        return

    receipt = json.loads(receipt_path.read_text())
    recorded_sha = receipt.get("boot_file_sha256", "")

    actual_sha = hashlib.sha256(boot_path.read_bytes()).hexdigest()

    if recorded_sha != actual_sha:
        failures.append(
            f"  BOOT SHA MISMATCH:\n"
            f"    recorded: {recorded_sha}\n"
            f"    actual:   {actual_sha}\n"
            f"    Fix: update boot_file_sha256 in BOOT_RECEIPT.json"
        )


def check_catalog_coverage():
    """Verify catalog covers all files in os_bundles/ and has no phantom entries."""
    catalog_path = ROOT / ".codex" / "artifacts" / "BUNDLE_CATALOG.json"
    bundles_dir = ROOT / "os_bundles"

    if not catalog_path.exists():
        failures.append("  BUNDLE_CATALOG.json: FILE NOT FOUND")
        return
    if not bundles_dir.exists():
        failures.append("  os_bundles/: DIRECTORY NOT FOUND")
        return

    catalog = json.loads(catalog_path.read_text())
    cataloged_names = {e["filename"] for e in catalog.get("entries", catalog.get("bundles", []))}

    # Actual files on disk (may be LFS pointers, that's fine)
    actual_files = {f.name for f in bundles_dir.iterdir() if f.is_file()}

    # Files on disk but not in catalog
    uncataloged = actual_files - cataloged_names
    if uncataloged:
        failures.append(
            f"  CATALOG MISSING {len(uncataloged)} files:\n"
            + "\n".join(f"    + {f}" for f in sorted(uncataloged))
        )

    # Files in catalog but not on disk
    phantom = cataloged_names - actual_files
    if phantom:
        failures.append(
            f"  CATALOG HAS {len(phantom)} PHANTOM entries (file not on disk):\n"
            + "\n".join(f"    - {f}" for f in sorted(phantom))
        )


def check_policy_doc_refs():
    """Verify all policy_documents in BOOT_RECEIPT actually exist."""
    receipt_path = ROOT / ".codex" / "receipts" / "BOOT_RECEIPT.json"
    if not receipt_path.exists():
        return

    receipt = json.loads(receipt_path.read_text())
    for name, path in receipt.get("policy_documents", {}).items():
        full_path = ROOT / path
        if not full_path.exists():
            failures.append(f"  POLICY REF BROKEN: {name} -> {path} (file not found)")

    for name, path in receipt.get("schemas", {}).items():
        full_path = ROOT / path
        if not full_path.exists():
            failures.append(f"  SCHEMA REF BROKEN: {name} -> {path} (file not found)")


def main():
    check_boot_sha()
    check_catalog_coverage()
    check_policy_doc_refs()

    if failures:
        print(f"STALENESS_GATE FAIL: {len(failures)} issues detected", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(11)
    else:
        print("STALENESS_GATE: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
