# CAP-018: Artifact Maturity Gate

> **System ID**: SYS-018
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Enforces a monotonic maturity lifecycle (DRAFT, VALIDATED, ENFORCED) on all governance artifacts, ensuring that artifacts can only advance in maturity and that no artifact exists outside the tracked registry.

## Source Files

- `.codex/validators/run_maturity_gate.py`

## Entry Points

- `main` — orchestrates all maturity checks and emits final pass/fail exit code
- `check_draft` — verifies a DRAFT artifact exists on disk
- `check_validated` — verifies a VALIDATED artifact exists and passes its associated JSON schema check
- `check_enforced` — verifies an ENFORCED artifact is validated, has a registered validator, and is registered in a governance gate
- `check_untracked_artifacts` — scans for artifacts that exist on disk but are not listed in the maturity registry
- `get_registered_gates` — reads `run_governance_gate.py` to extract the list of currently registered gate validators

## Contract

### Inputs

- `ARTIFACT_MATURITY.json` — the maturity registry mapping artifact paths to their current maturity level
- `run_governance_gate.py` — used to extract the list of registered gates for ENFORCED-level verification

### Outputs

- `EXIT 0` — all maturity checks pass
- `EXIT 15` — one or more maturity checks fail

### Preconditions

- `ARTIFACT_MATURITY.json` must exist and be valid JSON
- All artifact paths referenced in the maturity registry must be relative to the repository root

### Postconditions

- Every artifact at DRAFT level has a corresponding file on disk
- Every artifact at VALIDATED level passes its schema check
- Every artifact at ENFORCED level has a validator and is registered in the governance gate
- No artifacts exist on disk that are absent from the maturity registry
- Summary counts in the maturity registry are consistent with actual entries

### Failure Mode

FAIL_CLOSED — any maturity violation causes the gate to reject with EXIT 15.

## Dependencies

None

## Patterns Used

- **MONOTONIC** — maturity levels can only increase (DRAFT to VALIDATED to ENFORCED); demotion is prohibited

## Evidence

DRAFT, VALIDATED, ENFORCED lifecycle. Detects untracked artifacts. Validates summary counts. The gate prevents maturity regression and ensures every governance artifact is accounted for in the registry.

## Governance

- **MPP Phase**: Phase 5 (VALIDATE)
- **Gate**: Maturity Gate (EXIT 15)
- **Schema**: ARTIFACT_MATURITY.json (registry format)
