# CAP-016: Forbidden Language Detection Gate

> **System ID**: SYS-016
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Scans agent-produced artifacts for forbidden words that imply unwarranted certainty or active system status, enforcing the governance principle that agent output must not contain language suggesting autonomous authority or self-verification.

## Source Files

- `.codex/validators/run_forbidden_language_gate.py`

## Entry Points

- `main` — CLI entry point; discovers scannable files and runs the forbidden word scan
- `scan_file` — scans a single file for forbidden words using word-boundary regex matching; returns a list of violations with line numbers and context
- `get_bundle_filenames` — collects `os_bundles/` filenames to build the exemption list for bundle filename references

## Contract

### Inputs

- `.codex/receipts/*.json` — agent-produced receipt files
- `.codex/research/*.json` — agent-produced research artifacts
- `os_bundles/` filenames — used to build exemption list (not scanned)

### Outputs

- `EXIT 0` — no forbidden language detected in scanned files
- `EXIT 13` — at least one forbidden word found in agent output

### Preconditions

- Scannable files must exist under `.codex/receipts/` and/or `.codex/research/`
- `os_bundles/` directory must be readable (for building exemption list)

### Postconditions

- If EXIT 0: no instance of any of the 8 forbidden words appears in agent-produced artifacts (outside exempted contexts)
- If EXIT 13: at least one violation is reported with file path, line number, and matched word

### Failure Mode

FAIL_CLOSED — any forbidden word detection causes the gate to fail, blocking the commit via SYS-012.

## Dependencies

- None (standalone validation gate)

## Patterns Used

- `FAIL_CLOSED` — any violation blocks the commit

## Evidence

8 forbidden words scanned: enforced, verified, running, active, wired, booted, compliant, guaranteed. Exemptions applied for: human-authored documents (policies, BOOT.md), bundle filenames in `os_bundles/`, JSON fields containing bundle filenames. Word-boundary regex (`\b...\b`) prevents false positives on substrings.

## Governance

- **MPP Phase**: N/A (registered as gate in SYS-012)
- **Gate**: Registered as a sub-gate in the Master Governance Gate (SYS-012)
- **Schema**: None (output is exit codes and violation reports)
