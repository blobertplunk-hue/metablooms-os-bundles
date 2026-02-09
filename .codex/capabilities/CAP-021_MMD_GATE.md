# CAP-021: MMD Gate

> **System ID**: SYS-021
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Performs Missing Middle Detection across all governance artifacts, identifying structural gaps such as broken references, unschema'd artifacts, unregistered validators, and unexplained deferrals, inspired by DO-178C safety-critical verification methodology.

## Source Files

- `.codex/validators/run_mmd_gate.py`

## Entry Points

- `main` — orchestrates all 6 MMD methods, aggregates findings, and emits final pass/fail exit code
- `method_reference_graph` — detects broken cross-references between governance artifacts
- `method_schema_coverage` — identifies JSON artifacts that lack a corresponding schema
- `method_traceability` — verifies validators are registered and invariants have associated checkers
- `method_deferral_audit` — flags deferrals that lack an explanation or rationale
- `method_self_check` — validates the MMD report itself against its own schema
- `method_category_completeness` — detects open enums that should be closed (closed enum enforcement)

## Contract

### Inputs

- All `.codex/` JSON artifacts (schemas, reports, registries, catalogs)
- All `.codex/` markdown policies

### Outputs

- `EXIT 0` — pass (no findings) or pass_with_warnings (non-CRITICAL findings only)
- `EXIT 18` — CRITICAL findings detected

### Preconditions

- The `.codex/` directory must exist and contain at least one artifact or policy
- MMD_REPORT.schema.json must exist for the self-check method

### Postconditions

- All cross-references between artifacts resolve to existing files
- All JSON artifacts have a governing schema
- All validators are registered in the governance gate
- All invariants have associated checker implementations
- All deferrals have documented explanations
- The MMD report itself validates against MMD_REPORT.schema.json
- All enum-like categories are verified as closed sets

### Failure Mode

FAIL_CLOSED — CRITICAL findings cause the gate to reject with EXIT 18. Warnings are reported but do not block (pass_with_warnings).

## Dependencies

None

## Patterns Used

- **FAIL_CLOSED** — CRITICAL-severity findings block the gate unconditionally

## Evidence

6 methods: REFERENCE_GRAPH (broken refs), SCHEMA_COVERAGE (unschema'd artifacts), TRACEABILITY (validators registered, invariants have checkers), DEFERRAL_AUDIT (unexplained deferrals), SELF_CHECK (MMD report validates against own schema), CATEGORY_COMPLETENESS (closed enum detection). Inspired by DO-178C safety-critical software verification. Warnings pass; only CRITICAL findings block.

## Governance

- **MPP Phase**: Phase 5 (VALIDATE)
- **Gate**: MMD Gate (EXIT 18)
- **Schema**: MMD_REPORT.schema.json
