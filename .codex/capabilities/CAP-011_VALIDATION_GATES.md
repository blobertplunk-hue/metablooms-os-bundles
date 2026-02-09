# CAP-011: Validation Gates (MetaBlooms_OS)

> **System ID**: SYS-011
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Provides a suite of structural validation gates that verify the integrity of the MetaBlooms OS tree, ensuring all required schemas, policies, JSON artifacts, state files, and the pattern catalog are present and well-formed before the system is allowed to boot.

## Source Files

- `MetaBlooms_OS/validators/gates.py`

## Entry Points

- `ValidationGates.run_all` — executes every registered gate and returns a combined result
- `gate_schema_existence` — confirms that all 5 required JSON schemas exist under `.codex/schemas/`
- `gate_policy_existence` — confirms that all 5 required policy documents exist under `.codex/policies/`
- `gate_json_validity` — parses all JSON artifacts and verifies they are syntactically valid
- `gate_state_integrity` — checks that persisted state files are consistent and uncorrupted
- `gate_pattern_catalog` — verifies the pattern catalog is present and structurally complete

## Contract

### Inputs

- `os_root` path (absolute path to the MetaBlooms_OS directory)

### Outputs

- Combined gate result object: `{overall: PASS|FAIL, gates: [{name, result, detail}], validated_utc: ISO8601}`

### Preconditions

- `os_root` must be a valid, readable directory
- Expected subdirectories (`.codex/schemas/`, `.codex/policies/`, `.codex/artifacts/`) must exist

### Postconditions

- If `overall` is `PASS`, all 5 schemas, 5 policies, all JSON artifacts, state files, and pattern catalog have been confirmed present and valid
- If `overall` is `FAIL`, at least one gate failed and the `gates` array identifies which ones

### Failure Mode

FAIL_CLOSED — any single gate failure causes the overall result to be FAIL, which blocks boot in SYS-010.

## Dependencies

- None (standalone validation system)

## Patterns Used

- `FAIL_CLOSED` — no partial pass; all gates must succeed

## Evidence

5 schemas checked for existence; 5 policies checked for existence; all JSON artifacts parsed and validated; state integrity confirmed; pattern catalog verified. Combined result includes per-gate detail and UTC timestamp.

## Governance

- **MPP Phase**: Pre-MPP (used by boot)
- **Gate**: Self — this system is itself the gate system
- **Schema**: None (output is consumed programmatically by SYS-010, not persisted as a governed artifact)
