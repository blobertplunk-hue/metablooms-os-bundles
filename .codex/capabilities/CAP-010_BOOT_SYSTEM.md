# CAP-010: Boot System

> **System ID**: SYS-010
> **Type**: ORCHESTRATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Bootstraps the MetaBlooms OS runtime by locating the OS root directory, validating the directory tree structure, loading persisted state, and initializing the MPP orchestrator so that all downstream systems can operate on a known-good foundation.

## Source Files

- `MetaBlooms_OS/boot.py`

## Entry Points

- `boot` — top-level entry; orchestrates the full bootstrap sequence from root discovery through receipt emission
- `find_os_root` — searches 3 candidate paths (`./MetaBlooms_OS`, `../MetaBlooms_OS`, environment variable override) and returns the first valid OS root
- `load_state` — deserializes persisted state from the StateManager backing store
- `validate_os_tree` — checks for 9 required directories and 12 required files under the OS root; delegates to SYS-011 validation gates
- `emit_boot_receipt` — writes `BOOT_RECEIPT.json` with boot timestamp, validation results, and intelligence summary

## Contract

### Inputs

- Filesystem presence of a `MetaBlooms_OS` directory at one of 3 candidate paths

### Outputs

- `BOOT_RECEIPT.json` — structured receipt recording boot outcome
- Initialized `MPPOrchestrator` instance ready for phase execution
- Loaded `StateManager` with persisted state
- Resolved `os_root` path

### Preconditions

- At least one of the 3 candidate paths must contain a valid `MetaBlooms_OS` directory
- The OS tree must contain all 9 required directories and 12 required files
- Filesystem must be readable

### Postconditions

- `BOOT_RECEIPT.json` exists and is valid against `BOOT_RECEIPT.schema.json`
- `MPPOrchestrator` is initialized and ready to execute phases
- `StateManager` holds current state
- `os_root` is an absolute, resolved path

### Failure Mode

FAIL_CLOSED — if OS tree validation fails, boot aborts and no downstream systems are initialized. No partial boot state is persisted.

## Dependencies

- **SYS-001** (MPP) — initializes the MPP orchestrator
- **SYS-008** (State) — loads and manages persisted state
- **SYS-011** (Validation Gates) — runs structural validation of the OS tree

## Patterns Used

- `FAIL_CLOSED` — boot refuses to proceed on any validation failure

## Evidence

3 candidate paths searched in priority order; 9 required directories and 12 required files validated; validation gates from SYS-011 executed; intelligence summary printed to stdout on successful boot; BOOT_RECEIPT.json emitted with full validation trace.

## Governance

- **MPP Phase**: Pre-MPP (bootstrap)
- **Gate**: SYS-011 (Validation Gates) runs during boot
- **Schema**: `.codex/schemas/BOOT_RECEIPT.schema.json` (constrains BOOT_RECEIPT.json output)
