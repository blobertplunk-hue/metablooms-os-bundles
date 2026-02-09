# CAP-014: Staleness Detection Gate

> **System ID**: SYS-014
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Detects stale governance artifacts by verifying that receipts, catalogs, and policy references remain synchronized with their upstream sources, preventing commits that contain outdated or desynchronized metadata.

## Source Files

- `.codex/validators/run_staleness_gate.py`

## Entry Points

- `main` — CLI entry point; runs all staleness checks in sequence
- `check_boot_sha` — compares the SHA-256 hash of `BOOT.md` against the hash recorded in `BOOT_RECEIPT.json`
- `check_catalog_coverage` — verifies that `BUNDLE_CATALOG.json` covers every file in `os_bundles/` with no uncataloged files and no phantom entries
- `check_policy_doc_refs` — confirms that all policy document references in governance artifacts point to files that actually exist

## Contract

### Inputs

- `.codex/receipts/BOOT_RECEIPT.json` — contains recorded SHA-256 of BOOT.md
- `.codex/kernel/BOOT.md` — authoritative boot contract
- `.codex/artifacts/BUNDLE_CATALOG.json` — catalog of all bundle files
- `os_bundles/` directory listing — actual files on disk

### Outputs

- `EXIT 0` — all staleness checks pass; artifacts are current
- `EXIT 11` — at least one staleness check failed

### Preconditions

- `BOOT_RECEIPT.json` must exist and contain a `boot_md_sha256` field
- `BOOT.md` must exist
- `BUNDLE_CATALOG.json` must exist and be valid JSON
- `os_bundles/` directory must be readable

### Postconditions

- If EXIT 0: SHA-256 of BOOT.md matches the receipt, catalog covers every file in os_bundles/ with no phantoms, and all policy references resolve to existing files
- If EXIT 11: at least one artifact is stale or desynchronized

### Failure Mode

FAIL_CLOSED — any staleness detection causes the gate to fail, blocking the commit via SYS-012.

## Dependencies

- None (standalone validation gate)

## Patterns Used

- `BIJECTION` — enforces a one-to-one mapping between catalog entries and actual files in `os_bundles/` (no uncataloged files, no phantom entries)

## Evidence

SHA-256 match of BOOT.md verified against BOOT_RECEIPT.json; catalog covers every file in os_bundles/ with no uncataloged files and no phantom entries; policy document references confirmed to point to existing files.

## Governance

- **MPP Phase**: N/A (registered as gate in SYS-012)
- **Gate**: Registered as a sub-gate in the Master Governance Gate (SYS-012)
- **Schema**: None (reads but does not produce schema-governed output)
