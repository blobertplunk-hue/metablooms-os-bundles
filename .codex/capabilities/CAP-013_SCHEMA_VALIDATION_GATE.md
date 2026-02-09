# CAP-013: Schema Validation Gate

> **System ID**: SYS-013
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Validates that every governed JSON artifact in the repository conforms to its corresponding JSON schema, ensuring structural correctness and preventing malformed data from entering the governance system.

## Source Files

- `.codex/validators/run_schema_validation_gate.py`

## Entry Points

- `main` — CLI entry point; discovers artifacts and runs all validators
- `validate_catalog` — validates `BUNDLE_CATALOG.json` against `BUNDLE_ENTRY.schema.json`
- `validate_lineage` — validates `BUNDLE_LINEAGE.json` against `BUNDLE_LINEAGE.schema.json`
- `validate_mmd` — validates `MMD_REPORT.json` against `MMD_REPORT.schema.json`
- `validate_boot_receipt` — validates `BOOT_RECEIPT.json` against `TURN_RECEIPT.schema.json`
- `validate_invariant_registry` — validates `INVARIANT_REGISTRY.json` against its schema

## Contract

### Inputs

- `.codex/artifacts/*.json` — governed artifact files
- `.codex/schemas/*.schema.json` — JSON Schema definitions
- `.codex/receipts/BOOT_RECEIPT.json` — boot receipt artifact

### Outputs

- `EXIT 0` — all artifacts validate against their schemas
- `EXIT 10` — at least one artifact fails validation

### Preconditions

- All schema files must exist under `.codex/schemas/`
- All artifact files must be parseable JSON
- Python `jsonschema` library (or equivalent) available

### Postconditions

- If EXIT 0: BUNDLE_CATALOG, BUNDLE_LINEAGE, MMD_REPORT, BOOT_RECEIPT, and INVARIANT_REGISTRY all conform to their respective schemas and parse as valid JSON
- If EXIT 10: at least one artifact is malformed or schema-non-conformant

### Failure Mode

FAIL_CLOSED — any schema validation failure causes the gate to fail, blocking the commit via SYS-012.

## Dependencies

- None (standalone validation gate)

## Patterns Used

- `BIJECTION` — enforces a one-to-one mapping between schemas and artifacts (every artifact has a schema, every schema has an artifact)

## Evidence

Validates BUNDLE_CATALOG.json, BUNDLE_LINEAGE.json, MMD_REPORT.json, BOOT_RECEIPT.json, and INVARIANT_REGISTRY.json; all JSON parses cleanly; each artifact checked against its paired schema; EXIT 10 on any mismatch.

## Governance

- **MPP Phase**: N/A (registered as gate in SYS-012)
- **Gate**: Registered as a sub-gate in the Master Governance Gate (SYS-012)
- **Schema**: Uses all `.codex/schemas/*.schema.json` — `BUNDLE_ENTRY.schema.json`, `BUNDLE_LINEAGE.schema.json`, `MMD_REPORT.schema.json`, `TURN_RECEIPT.schema.json`
