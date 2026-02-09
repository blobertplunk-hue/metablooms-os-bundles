# CAP-015: LFS Gap Detection Gate

> **System ID**: SYS-015
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Detects files in `os_bundles/` whose extensions are not covered by any Git LFS tracking pattern in `.gitattributes`, preventing large binary files from being committed directly to the Git object store instead of LFS.

## Source Files

- `.codex/validators/run_lfs_gap_gate.py`

## Entry Points

- `main` — CLI entry point; parses `.gitattributes`, scans `os_bundles/`, and reports gaps
- `parse_lfs_patterns` — extracts all `filter=lfs` glob patterns from `.gitattributes` and normalizes them
- `extension_matches_any_pattern` — tests whether a given file extension matches any of the parsed LFS patterns

## Contract

### Inputs

- `.gitattributes` — Git LFS tracking configuration
- `os_bundles/` directory listing — actual binary files on disk

### Outputs

- `EXIT 0` — every file in `os_bundles/` is covered by an LFS tracking pattern
- `EXIT 12` — at least one file extension is not tracked by LFS

### Preconditions

- `.gitattributes` must exist and contain at least one `filter=lfs` rule
- `os_bundles/` directory must be readable

### Postconditions

- If EXIT 0: every file in `os_bundles/` has an extension matched by a `filter=lfs` pattern in `.gitattributes`
- If EXIT 12: at least one file has an untracked extension; untracked files are reported grouped by extension

### Failure Mode

FAIL_CLOSED — any untracked file extension causes the gate to fail, blocking the commit via SYS-012.

## Dependencies

- None (standalone validation gate)

## Patterns Used

- `BIJECTION` — enforces that LFS tracking patterns cover all actual file extensions in `os_bundles/` (no extension goes untracked)

## Evidence

Parses `.gitattributes` for all `filter=lfs` patterns; checks every file in `os_bundles/` against parsed patterns; groups untracked files by extension in failure output; EXIT 12 on any gap.

## Governance

- **MPP Phase**: N/A (registered as gate in SYS-012)
- **Gate**: Registered as a sub-gate in the Master Governance Gate (SYS-012)
- **Schema**: None (output is exit codes and stdout diagnostics)
