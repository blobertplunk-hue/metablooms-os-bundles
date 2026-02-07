# CLAUDE.md - MetaBlooms OS Bundles

## Project Overview

This is a **binary artifact storage repository** for the MetaBlooms project. It stores versioned OS bundles, chat data exports, driver installers, and educational resources. There is no application source code — this repo is purely for distribution and versioning of large binary files via Git LFS.

## Repository Structure

```
metablooms-os-bundles/
├── .gitattributes                    # Git LFS tracking rules
├── CLAUDE.md                         # This file
├── .codex/                           # Governance scaffolding
│   ├── kernel/
│   │   └── BOOT.md                   # Governance bootstrap contract
│   ├── receipts/                     # Execution receipts
│   │   └── BOOT_RECEIPT.json         # Boot acknowledgment receipt
│   ├── artifacts/                    # Generated outputs
│   │   ├── BUNDLE_CATALOG.json       # Full catalog of all 90 files
│   │   └── MMD_REPORT.json           # Missing Middle Detection report
│   ├── schemas/                      # JSON schemas
│   │   ├── BUNDLE_ENTRY.schema.json  # Per-file metadata schema
│   │   ├── BUNDLE_LINEAGE.schema.json # Bundle evolution tracking
│   │   ├── MMD_REPORT.schema.json    # MMD report structure
│   │   └── TURN_RECEIPT.schema.json  # Turn receipt structure
│   ├── policies/                     # Governance policies
│   │   ├── SUPER_PROMPT_v2.3.md      # Governed execution prompt
│   │   ├── DELTAGATE_v1.md           # Change admission policy
│   │   ├── RRP_v1.md                 # Recursive refinement protocol
│   │   └── SEE_ENGINE_v1.md          # Search for Evidence Engine spec
│   └── research/                     # Evidence artifacts
└── os_bundles/                       # Binary artifacts (90 files)
    ├── MetaBlooms_OS_*.zip           # OS bundle snapshots (~50 files)
    ├── Metablooms_OS_*.zip           # OS bundle snapshots, alt casing (~17 files)
    ├── MB_CHAT*_*.zip                # Chat data exports, chunked (~6 files)
    ├── CHAT7_FULL_MNT_DATA_EXPORT.part* # Segmented chat archive (8 parts)
    ├── chat_4_RETRY_*.zip.part*      # Segmented chat archive (2 parts)
    ├── *.exe                         # Driver/utility installers (6 files)
    ├── *.rtf                         # Educational content (1 file)
    └── (misc)                        # Non-project, recovery, uploader bundles
```

## Governance System

This repository uses a structured governance framework under `.codex/`. See `.codex/kernel/BOOT.md` for the full contract.

### Key Governance Concepts

| Framework | Purpose |
|-----------|---------|
| **Kernel Law** | Agent operates under external authority only — produces artifacts, not enforcement |
| **DeltaGate** | Changes require explicit external admission |
| **SEE** | Every factual claim must cite evidence |
| **RRP** | Outputs go through BUILD → EVALUATE → REWRITE cycle |
| **ECL** | Agent declares its capabilities honestly |
| **CDR** | Every decision must explain WHY, constraints, and failure modes |

### Running a Governed Session

1. The execution prompt is at `.codex/policies/SUPER_PROMPT_v2.3.md`
2. Copy that prompt into your AI tool of choice
3. Fill in the `TASK_INPUT` section with your specific task
4. The agent will execute the Mandatory Process Pipeline (phases -1 through 7)
5. All outputs land in `.codex/` subdirectories
6. Review the `TURN_RECEIPT.json` for the execution summary

## Key Conventions

### Git LFS

All large binary files are tracked via Git LFS. Tracked extensions (defined in `.gitattributes`):

- Archives: `*.zip`, `*.7z`, `*.tar.gz`, `*.iso`, `*.bin`
- Executables: `*.exe`, `*.dmg`
- AI models: `*.gguf`, `*.safetensors`, `*.pt`, `*.onnx`
- Databases: `*.db`
- Segmented archives: `*.part[0-9]*`
- Documents: `*.rtf`

**Important:** Always ensure Git LFS is installed and initialized before cloning or pushing. New binary file types should be added to `.gitattributes` before committing.

### Bundle Naming Conventions

OS bundles follow a structured naming pattern:

```
[Date_]MetaBlooms_OS_<FEATURE_CHAIN>_[TIMESTAMP].zip
```

- **Date prefix**: `2026-01-17_` format (optional, used for early bundles)
- **Timestamps**: ISO 8601 format `YYYYMMDDTHHMMSSZ` (e.g., `20260128T164100Z`)
- **Feature chain**: Underscore-separated feature/phase descriptors joined with `PLUS`
- **Version qualifiers** (full list in `.codex/kernel/BOOT.md`):
  - `BASELINE` — initial version of a feature set
  - `CANONICAL` — authoritative/reference version
  - `PATCHED` / `REMEDIATED` / `REPAIRED` / `FIXED` — corrections
  - `VALIDATED_EXPORT` — QA-verified release
  - `FROZEN_FULL_EXPORT` — immutable snapshot
  - `RCA_ENABLED` — root cause analysis instrumentation
  - `SHIP_GATED` — production-ready, gated for release
  - `LTS` — long-term support version
  - `WIRED` / `FULLY_WIRED` — integrated components
  - `MASTERY_ENFORCED` / `MASTERY_INTEGRATED` — quality-gated
  - `BOOT_HARDENED` — boot sequence hardening
  - `CHASSISGATE` — chassis-level integration gate
  - `EXECUTION_ENFORCED` / `UIUX_ENFORCED` — runtime gates
- **Phase markers**: `P0`, `P1`, `P2`, `P3` indicate development phases

### Bundle Classification Taxonomy

| Category          | Pattern                              | Count |
|-------------------|--------------------------------------|-------|
| `os_bundle`       | `MetaBlooms_OS_*.zip`                | 52    |
| `os_bundle_part`  | `*.zip.part*`                        | 2     |
| `chat_export`     | `MB_CHAT*_*.zip`, `CHAT_DELTA_*`     | 7     |
| `chat_export_part`| `CHAT*_FULL_*.part*`                 | 10    |
| `driver`          | NVIDIA, printer, GPU scan .exe       | 4     |
| `utility`         | GitHubDesktop, gpg4win .exe          | 2     |
| `educational`     | ELAR resource, Lesson plans          | 2     |
| `non_project`     | `MetaBlooms_NON_PROJECT_FILES_*`     | 5     |
| `ship_bundle`     | `MB_SHIP_BUNDLE_*`                   | 1     |
| `recovery`        | `payload_recovery_*`                 | 1     |
| `uploader`        | `*uploader*`, `*RunPack*`            | 2     |
| `misc_archive`    | `Archive*.zip`, `drive-download-*`   | 2     |

Full catalog with per-file metadata: `.codex/artifacts/BUNDLE_CATALOG.json`

### Chat Data Exports

Chat data follows two patterns:
- Chunked ZIPs: `MB_CHAT<N>_MNTDATA_CHUNK<NNN>_<DATE>.zip`
- Segmented archives: `CHAT<N>_FULL_MNT_DATA_EXPORT.part<NNN>`

### Segment Groups

| Group                        | Parts | Total Size |
|------------------------------|-------|------------|
| CHAT7_FULL_MNT_DATA_EXPORT   | 8     | ~770 MB    |
| chat_4_RETRY_full_mnt_data   | 2     | ~135 MB    |
| MetaBlooms_OS_VALIDATED_EXPORT | 2   | ~183 MB    |

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

### Updating the Bundle Catalog

After adding or removing files from `os_bundles/`, regenerate
`.codex/artifacts/BUNDLE_CATALOG.json` to keep the catalog current.

## Important Notes for AI Assistants

- **No build system, tests, or linters** exist in this repo. Do not attempt to run build/test commands.
- **Do not attempt to read or extract binary files** — they are LFS pointers or large binaries.
- **File operations should be limited to**: adding/removing bundles, updating `.gitattributes`, updating documentation, and generating governance artifacts under `.codex/`.
- **Commit messages** should list the number of files and approximate total size when adding bundles.
- The repository uses a **local proxy** for its remote origin — network-dependent git operations may need retries.
- **Governance**: If operating under the super-prompt, follow the Mandatory Process Pipeline. All receipts go to `.codex/receipts/`, all artifacts to `.codex/artifacts/`.
- **Schema reference**: Bundle entries must conform to `.codex/schemas/BUNDLE_ENTRY.schema.json`.
