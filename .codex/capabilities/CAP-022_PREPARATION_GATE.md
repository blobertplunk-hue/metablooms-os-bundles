# CAP-022: Preparation Gate

> **System ID**: SYS-022
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Enforces Phase 2.75 readiness — blocks BUILD unless mastery definition and core schemas exist.

## Source Files

- .codex/validators/run_preparation_gate.py

## Entry Points

- main (orchestrator)
- check_file (existence check)
- check_valid_json (JSON parse check)

## Contract

### Inputs

- MB_MASTER_SPEC_v1.md (string, file path)
- MASTERY_DEFINITION.schema.json (string, file path)
- DECISION_RECORD.schema.json (string, file path)
- LESSON_PROMOTION.schema.json (string, file path)

### Outputs

- EXIT 0 (pass)
- EXIT 19 (fail)

### Preconditions

.codex/ directory exists with policies and schemas subdirectories

### Postconditions

Master spec exists with all 6 phases, 3 core schemas exist and are valid JSON

### Failure Mode

FAIL_CLOSED — blocks BUILD without preparation

## Dependencies

- None

## Patterns Used

FAIL_CLOSED

## Evidence

Checks master spec contains SURFACE, DETECT, PREPARE, REFUSE, EXECUTE, ASSIMILATE. Checks 3 schemas have title or $schema.

## Governance

- **MPP Phase**: N/A (pre-commit hook, represents Phase 2.75)
- **Gate**: Registered in Master Governance Gate (SYS-012)
- **Schema**: N/A
