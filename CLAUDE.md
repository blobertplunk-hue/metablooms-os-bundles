# CLAUDE.md - MetaBlooms OS Bundles

## Project Overview

This is a **binary artifact storage repository** for the MetaBlooms project. It stores versioned OS bundles, chat data exports, driver installers, and educational resources. There is no application source code — this repo is purely for distribution and versioning of large binary files via Git LFS.

## Repository Structure

```
metablooms-os-bundles/
├── .gitattributes        # Git LFS tracking rules
├── CLAUDE.md             # This file
└── os_bundles/           # All binary artifacts (90 files)
    ├── MetaBlooms_OS_*.zip         # OS bundle snapshots
    ├── Metablooms_OS_*.zip         # OS bundle snapshots (alt casing)
    ├── MB_CHAT*_*.zip              # Chat data exports (chunked)
    ├── CHAT7_FULL_MNT_DATA_EXPORT.part* # Segmented chat archives
    ├── *.exe                       # Driver/utility installers
    └── *.rtf                       # Educational content
```

## Key Conventions

### Git LFS

All large binary files are tracked via Git LFS. Tracked extensions (defined in `.gitattributes`):

- Archives: `*.zip`, `*.7z`, `*.tar.gz`, `*.iso`, `*.bin`
- Executables: `*.exe`, `*.dmg`
- AI models: `*.gguf`, `*.safetensors`, `*.pt`, `*.onnx`
- Databases: `*.db`

**Important:** Always ensure Git LFS is installed and initialized before cloning or pushing. New binary file types should be added to `.gitattributes` before committing.

### Bundle Naming Conventions

OS bundles follow a structured naming pattern:

```
[Date_]MetaBlooms_OS_<FEATURE_CHAIN>_[TIMESTAMP].zip
```

- **Date prefix**: `2026-01-17_` format (optional, used for early bundles)
- **Timestamps**: ISO 8601 format `YYYYMMDDTHHMMSSZ` (e.g., `20260128T164100Z`)
- **Feature chain**: Underscore-separated feature/phase descriptors joined with `PLUS`
- **Version qualifiers**:
  - `BASELINE` — initial version of a feature set
  - `WIRED` / `FULLY_WIRED` — integrated/connected components
  - `MASTERY_ENFORCED` / `MASTERY_INTEGRATED` — quality-gated releases
  - `PATCHED` — bug fix applied to a prior bundle
  - `CANONICAL` — authoritative/reference version
  - `VALIDATED_EXPORT` — QA-verified release
  - `FROZEN_FULL_EXPORT` — immutable snapshot
  - `RCA_ENABLED` — root cause analysis instrumentation included
  - `SHIP_GATED` — production-ready, gated for release
  - `LTS` — long-term support version
- **Phase markers**: `P0`, `P1`, `P2`, `P3` indicate development phases

### Chat Data Exports

Chat data follows two patterns:
- Chunked ZIPs: `MB_CHAT<N>_MNTDATA_CHUNK<NNN>_<DATE>.zip`
- Segmented archives: `CHAT<N>_FULL_MNT_DATA_EXPORT.part<NNN>`

## Development Workflow

### Adding New Bundles

1. Ensure the file extension is tracked in `.gitattributes` (add it if not)
2. Place the file in `os_bundles/`
3. Follow the naming conventions above
4. Commit with a descriptive message listing files and total size

### Modifying LFS Configuration

Edit `.gitattributes` to add new patterns:
```
*.newext filter=lfs diff=lfs merge=lfs -text
```

## Important Notes for AI Assistants

- **No build system, tests, or linters** exist in this repo. Do not attempt to run build/test commands.
- **Do not attempt to read or extract binary files** — they are LFS pointers or large binaries.
- **File operations should be limited to**: adding/removing bundles, updating `.gitattributes`, and updating documentation.
- **Commit messages** should list the number of files and approximate total size when adding bundles.
- The repository uses a **local proxy** for its remote origin — network-dependent git operations may need retries.
