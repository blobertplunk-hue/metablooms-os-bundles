# CAP-024: Git Hook Installer

> **System ID**: SYS-024
> **Type**: CREATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

One-time setup script that installs the governance pre-commit hook, connecting the gate system to git workflow.

## Source Files

- .codex/validators/install_hooks.sh

## Entry Points

- main (shell script, single entry point)

## Contract

### Inputs

- Git repository root (string, auto-detected)

### Outputs

- .git/hooks/pre-commit (executable hook that runs run_governance_gate.py)

### Preconditions

Inside a git repository, .codex/validators/run_governance_gate.py exists

### Postconditions

pre-commit hook installed and executable, governance gates run on every commit

### Failure Mode

DEGRADED — prompts before overwriting existing hook, does not force-install

## Dependencies

- SYS-012 (Master Governance Gate)

## Patterns Used

IDEMPOTENT (safe to re-run)

## Evidence

Creates .git/hooks/pre-commit that invokes python3 .codex/validators/run_governance_gate.py. Blocks commits when any governance gate fails.

## Governance

- **MPP Phase**: N/A (one-time setup)
- **Gate**: N/A
- **Schema**: N/A
