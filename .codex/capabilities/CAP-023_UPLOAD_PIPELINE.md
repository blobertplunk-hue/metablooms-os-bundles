# CAP-023: Upload Pipeline

> **System ID**: SYS-023
> **Type**: CREATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Termux-based Android script that uploads files from Downloads to GitHub via Git LFS with governance compliance.

## Source Files

- scripts/mb-upload.sh

## Entry Points

- upload (main flow)
- preflight (environment checks)
- list_downloads (show available files)
- ensure_lfs_tracking (check .gitattributes)
- push_with_retry (exponential backoff)
- run_setup (first-time install)
- parse_gitattributes (dynamic LFS pattern extraction)
- is_lfs_tracked (per-file check)

## Contract

### Inputs

- Files from /storage/emulated/0/Download (Android path)
- Optional glob pattern filter (string)
- Flags: --dry-run, --list, --setup, --help (string)

### Outputs

- Files copied to os_bundles/ (binary)
- Git commit with file list and sizes (string)
- Git push with retry (side effect)

### Preconditions

Termux environment, storage permission, git and git-lfs installed, repo cloned

### Postconditions

Files committed and pushed to remote, .gitattributes updated if needed

### Failure Mode

FAIL_CLOSED — rejects files with untracked extensions, aborts on preflight failure

## Dependencies

- git, git-lfs, .gitattributes (external tools, not SYS-*)

## Patterns Used

IDEMPOTENT (skips existing files), FAIL_CLOSED (unknown extensions rejected), MONOTONIC (append-only to os_bundles/)

## Evidence

v2.0-governed. Dynamic .gitattributes parsing. Preflight: storage access, repo clone, git, git-lfs. Exponential backoff push retry (2s/4s/8s/16s). CDR rationale comments in source.

## Governance

- **MPP Phase**: N/A (standalone tool)
- **Gate**: N/A
- **Schema**: N/A
