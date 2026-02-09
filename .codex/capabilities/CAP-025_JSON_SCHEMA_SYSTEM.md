# CAP-025: JSON Schema System

> **System ID**: SYS-025
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Structural contracts for all artifact types. Every governance artifact must conform to its schema.

## Source Files

- MetaBlooms_OS/schemas/MASTERY_DEFINITION.schema.json
- MetaBlooms_OS/schemas/DECISION_RECORD.schema.json
- MetaBlooms_OS/schemas/LESSON_PROMOTION.schema.json
- MetaBlooms_OS/schemas/TURN_RECEIPT.schema.json
- MetaBlooms_OS/schemas/MMD_REPORT.schema.json
- MetaBlooms_OS/schemas/BUNDLE_ENTRY.schema.json
- MetaBlooms_OS/schemas/BUNDLE_LINEAGE.schema.json
- MetaBlooms_OS/schemas/INTENT_IR.schema.json
- MetaBlooms_OS/schemas/LEARNING_EVENT.schema.json
- MetaBlooms_OS/schemas/TOOLBOX_REALITY.schema.json
- MetaBlooms_OS/schemas/ROBUSTNESS_METRICS.schema.json
- MetaBlooms_OS/schemas/SCENARIO_SET.schema.json
- MetaBlooms_OS/schemas/DELTA_LEDGER.schema.json
- .codex/schemas/ (dual-homed copies)

## Entry Points

- Used by MasteryEngine._load_schema (runtime validation)
- Used by DecisionEngine._load_schema (runtime validation)
- Used by run_schema_validation_gate.py (pre-commit validation)
- Used by run_invariant_gate.py (invariant checking)

## Contract

### Inputs

- JSON data to validate (any artifact, object)

### Outputs

- Validation pass/fail per entry against schema (boolean)

### Preconditions

Schema file exists for the artifact type being validated

### Postconditions

Validated artifact conforms to structural contract

### Failure Mode

FAIL_CLOSED — schema violations block artifact creation and commit

## Dependencies

None (foundational)

## Patterns Used

BIJECTION (1:1 mapping between schema and artifact type)

## Evidence

13 JSON schemas dual-homed in MetaBlooms_OS/schemas/ and .codex/schemas/. Define structural contracts including required fields, types, enums, and cross-references.

## Governance

- **MPP Phase**: N/A (used across all phases)
- **Gate**: N/A
- **Schema**: N/A
