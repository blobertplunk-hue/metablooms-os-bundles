# CAP-020: Toolbox Reality Gate

> **System ID**: SYS-020
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Validates that the Toolbox Reality contract is properly defined and referenced, ensuring the agent's declared capabilities match the environment's actual capabilities as required by governance rule R2.5.

## Source Files

- `.codex/validators/run_toolbox_reality_gate.py`

## Entry Points

- `main` — orchestrates all toolbox reality checks and emits final pass/fail exit code
- `check_schema_exists` — verifies TOOLBOX_REALITY.schema.json exists and has title "ToolboxReality"
- `check_environment_declaration` — verifies ENVIRONMENT_DECLARATION.json exists and includes `filesystem_write` capability
- `check_policy_references` — scans policy documents for references to TOOLBOX_REALITY or R2.5

## Contract

### Inputs

- `TOOLBOX_REALITY.schema.json` — JSON schema defining the toolbox reality contract structure
- `ENVIRONMENT_DECLARATION.json` — environment capability declaration including filesystem_write
- `.codex/policies/*.md` — policy documents that must reference TOOLBOX_REALITY or R2.5

### Outputs

- `EXIT 0` — all toolbox reality checks pass
- `EXIT 17` — one or more toolbox reality checks fail

### Preconditions

- The `.codex/schemas/` directory must exist
- At least one policy document must exist in `.codex/policies/`

### Postconditions

- TOOLBOX_REALITY.schema.json exists and contains a "title" field set to "ToolboxReality"
- ENVIRONMENT_DECLARATION.json exists and declares `filesystem_write` capability
- At least one policy document references TOOLBOX_REALITY or R2.5

### Failure Mode

FAIL_CLOSED — missing schema, missing environment declaration, or missing policy references cause the gate to reject with EXIT 17.

## Dependencies

None

## Patterns Used

- **FAIL_CLOSED** — any missing component blocks the gate

## Evidence

Enforces R2.5: schema exists with title ToolboxReality, environment declaration has filesystem_write, policy doc references TOOLBOX_REALITY or R2.5. Prevents the agent from operating under false capability assumptions.

## Governance

- **MPP Phase**: Phase 5 (VALIDATE)
- **Gate**: Toolbox Reality Gate (EXIT 17)
- **Schema**: TOOLBOX_REALITY.schema.json
