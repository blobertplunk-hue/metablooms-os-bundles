# CAP-012: Master Governance Gate

> **System ID**: SYS-012
> **Type**: ORCHESTRATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Orchestrates the execution of all 10 registered governance gates in sequence, enforcing a pre-commit quality bar that blocks any commit from landing if any individual gate fails. Installed as a Git pre-commit hook.

## Source Files

- `.codex/validators/run_governance_gate.py`

## Entry Points

- `main` — CLI entry point; parses arguments and invokes `run_gate`
- `run_gate` — executes all 10 registered gates in sequence with a 60-second timeout per gate, collecting per-gate PASS/FAIL results and timing

## Contract

### Inputs

- `--quick` flag (optional) — skips slow gates for rapid iteration
- All `.codex/` artifacts, schemas, policies, receipts, and validators

### Outputs

- `EXIT 0` — all gates passed
- `EXIT 1` — at least one gate failed
- Per-gate PASS/FAIL status with execution timing printed to stdout

### Preconditions

- All 10 sub-gate scripts (SYS-013 through SYS-022) must be present and executable
- `.codex/` directory must contain the expected artifact tree
- Python runtime available

### Postconditions

- If EXIT 0: every registered gate returned PASS within its timeout window; commit proceeds
- If EXIT 1: at least one gate failed or timed out; commit is blocked

### Failure Mode

FAIL_CLOSED — blocks the commit if any gate fails. MONOTONIC — once a gate has passed for a given state, re-running on the same state will produce the same result.

## Dependencies

- **SYS-013** (Schema Validation Gate)
- **SYS-014** (Staleness Detection Gate)
- **SYS-015** (LFS Gap Detection Gate)
- **SYS-016** (Forbidden Language Detection Gate)
- **SYS-017** (Invariant Evaluation Gate)
- **SYS-018** through **SYS-022** (additional registered gates)

## Patterns Used

- `FAIL_CLOSED` — any sub-gate failure blocks the commit
- `MONOTONIC` — gate results are deterministic for a given repository state

## Evidence

Orchestrates 10 gates in sequence with 60-second timeout each; installed as a Git pre-commit hook; prints per-gate PASS/FAIL with timing to stdout; returns EXIT 0 only if all 10 gates pass.

## Governance

- **MPP Phase**: N/A (pre-commit hook, runs outside MPP pipeline)
- **Gate**: Self — this is the master gate orchestrator
- **Schema**: None (output is exit codes and stdout, not a persisted artifact)
