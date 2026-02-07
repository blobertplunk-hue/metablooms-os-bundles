# BOOT v1 — MetaBlooms OS Bundles Governance Bootstrap

## Purpose

This file establishes the governance contract for any AI execution agent
operating on the `metablooms-os-bundles` repository. Reading and acknowledging
this file is a prerequisite for any governed work session.

## Scope

This governance applies to:
- All files under `os_bundles/`
- All governance artifacts under `.codex/`
- The `.gitattributes` LFS configuration
- The `CLAUDE.md` project documentation

## Repository Identity

| Field               | Value                                    |
|---------------------|------------------------------------------|
| Repository          | metablooms-os-bundles                    |
| Owner               | blobertplunk-hue                         |
| Type                | Binary artifact storage (Git LFS)        |
| Source code          | None — this repo stores only binaries and documentation |
| Bundle count         | See BUNDLE_CATALOG.json for current count |
| Governance root      | `.codex/`                               |

## Governance Frameworks Referenced

### Kernel Law
The execution agent operates under external authority only. The agent
produces artifacts and evidence. It does NOT enforce, admit, or reject.
All enforcement decisions are made by a human operator or external CI system.

### DeltaGate
Changes to the bundle catalog, directory structure, or LFS configuration
require explicit admission. The agent may PROPOSE changes. It may NOT
declare them accepted.

### SEE (Search for Evidence Engine)
Any factual or architectural claim must cite evidence. If web access is
unavailable, the agent must declare SOURCE-LIMITED MODE and flag
uncitable claims explicitly.

### RRP (Recursive Refinement Protocol)
Outputs must go through: BUILD → EVALUATE (read-only) → REWRITE (fixes only).
No new scope may be introduced during refinement.

### ECL (Explicit Control Logic)
The agent must declare its capabilities and limitations honestly at the
start of each session. No enforcement language unless enforcement
infrastructure actually exists.

### CDR (Coding Done Right)
Every design decision must include: WHY it was chosen, WHAT constraints
apply, and HOW it could fail. Unexplained logic is a defect.

## Bundle Classification Taxonomy

The agent must classify every file in `os_bundles/` using these categories:

| Category            | Pattern Examples                         |
|---------------------|------------------------------------------|
| `os_bundle`         | `MetaBlooms_OS_*.zip`                    |
| `os_bundle_part`    | `MetaBlooms_OS_*.zip.part*`              |
| `chat_export`       | `MB_CHAT*_*.zip`, `CHAT*_FULL_*`         |
| `chat_export_part`  | `CHAT*_FULL_*.part*`, `chat_*_*.zip.part*` |
| `driver`            | `*.exe` (NVIDIA, printer, GPU utilities) |
| `utility`           | `GitHubDesktopSetup*.exe`, `gpg4win*.exe` |
| `educational`       | `*ELAR*`, `*Lesson*`                     |
| `non_project`       | `MetaBlooms_NON_PROJECT_FILES_*`         |
| `ship_bundle`       | `MB_SHIP_BUNDLE_*`                       |
| `recovery`          | `payload_recovery_*`                     |
| `uploader`          | `*uploader*`, `*RunPack*`                |
| `misc_archive`      | `Archive*.zip`, `drive-download-*`       |

## Version Qualifier Definitions

| Qualifier              | Meaning                                              |
|------------------------|------------------------------------------------------|
| `BASELINE`             | Initial version of a feature set                     |
| `WIRED` / `FULLY_WIRED` | Components integrated and connected                |
| `MASTERY_ENFORCED`     | Quality gates applied                                |
| `MASTERY_INTEGRATED`   | Quality gates merged into mainline                   |
| `PATCHED`              | Bug fix applied to a prior bundle                    |
| `REMEDIATED`           | Issue identified and corrected                       |
| `REPAIRED`             | Structural fix applied                               |
| `FIXED`                | Targeted defect resolution                           |
| `CANONICAL`            | Authoritative reference version                      |
| `VALIDATED_EXPORT`     | QA-verified release                                  |
| `FROZEN_FULL_EXPORT`   | Immutable snapshot — do not modify                   |
| `RCA_ENABLED`          | Root cause analysis instrumentation included         |
| `SHIP_GATED`           | Production-ready, gated for release                  |
| `TRACE_DRIFT_ENABLED`  | Drift detection instrumentation included             |
| `LTS`                  | Long-term support version                            |
| `REHYDRATED`           | Previously dehydrated/pointer-only bundle restored   |
| `REBUILT`              | Regenerated from source components                   |
| `REISSUE` / `RESHIPPED`| Re-released after correction                        |
| `EXECUTION_ENFORCED`   | Runtime execution gates applied                      |
| `UIUX_ENFORCED`        | UI/UX quality gates applied                          |
| `CHASSISGATE`          | Chassis-level integration gate applied               |
| `BOOT_HARDENED`        | Boot sequence hardening applied                      |
| `CBPPP`                | Component-Based Production Pipeline Protocol         |

## Phase Markers

| Phase | Meaning                          |
|-------|----------------------------------|
| `P0`  | Foundation / core infrastructure |
| `P1`  | Primary feature integration      |
| `P2`  | Secondary features and polish    |
| `P3`  | Hardening and release prep       |

## Feature Chain Components

These appear in bundle names as underscore-separated segments joined by `PLUS`:

| Component                    | Domain                          |
|------------------------------|---------------------------------|
| `PASS3_BYTE_TRUTH`          | Data integrity verification     |
| `SEE_LOOP`                  | Evidence engine integration     |
| `SECURITY_AXIS`             | Security layer                  |
| `RESOURCE_CONCURRENCY`      | Concurrency/resource management |
| `PORTABILITY_CONFIG`        | Cross-platform configuration    |
| `FILE_HANDLING`             | File I/O subsystem              |
| `SHIPPING_PROCEDURE`        | Release/deployment pipeline     |
| `PHASEC3_MATERIALIZED`      | Phase C3 artifacts realized     |
| `AUTO_MMD_CONTRACT_AUDIT`   | Automated missing-middle detection |
| `SEE_MMD_ECL_INVARIANTS`    | Combined governance invariants  |
| `DELTA_SEE_UBIQUITY`        | Delta-aware evidence coverage   |
| `RUNTIME_FULL_GOVERNANCE`   | Full runtime governance stack   |

## LFS Requirements

All binary files MUST be tracked by Git LFS. The following extensions
MUST appear in `.gitattributes`:

- `*.zip`, `*.7z`, `*.tar.gz`, `*.iso`, `*.bin`
- `*.exe`, `*.dmg`
- `*.gguf`, `*.safetensors`, `*.pt`, `*.onnx`
- `*.db`
- `*.part[0-9]*` (segmented archives)
- `*.rtf` (educational content)

## Canonical Directory Structure

```
metablooms-os-bundles/
├── .gitattributes                    # LFS tracking rules
├── CLAUDE.md                         # Project documentation
├── .codex/                           # Governance scaffolding
│   ├── kernel/
│   │   └── BOOT.md                   # This file
│   ├── receipts/                     # Execution receipts
│   │   ├── BOOT_RECEIPT.json
│   │   ├── TURN_RECEIPT.json
│   │   ├── ENFORCEMENT_CAPABILITY.json
│   │   ├── ENVIRONMENT_DECLARATION.json
│   │   ├── EVALUATION_REPORT.json
│   │   ├── REWRITE_REPORT.json
│   │   └── SELF_VERIFICATION.json
│   ├── artifacts/                    # Generated outputs
│   │   ├── BUNDLE_CATALOG.json
│   │   ├── CLAIM_REGISTRY.json
│   │   ├── MMD_REPORT.json
│   │   └── PROPOSED_STRUCTURE.md
│   ├── schemas/                      # JSON schemas
│   │   └── BUNDLE_ENTRY.schema.json
│   ├── policies/                     # Governance policies
│   └── research/                     # Evidence artifacts
│       ├── SEE_QUERY_LOG.json
│       └── SOURCE_LEDGER.json
└── os_bundles/                       # Binary artifacts (90 files)
```

## Standalone Policy Documents

Each governance framework has a detailed policy specification:

| Framework  | Policy Document                            |
|------------|--------------------------------------------|
| DeltaGate  | `.codex/policies/DELTAGATE_v1.md`          |
| RRP        | `.codex/policies/RRP_v1.md`                |
| SEE        | `.codex/policies/SEE_ENGINE_v1.md`         |

Frameworks without standalone docs (Kernel Law, ECL, CDR) are defined
in this file. They may be extracted to standalone docs in future versions.

## Forbidden Language Scope

The forbidden language list (enforced, verified, running, active, wired,
booted, compliant, guaranteed) applies ONLY to **agent-emitted output**.

It does NOT apply to:
- Bundle filenames (e.g., `MASTERY_ENFORCED` is a valid qualifier)
- Governance documents quoting the forbidden list itself
- Historical references in receipts

## FAIL CLOSED Definition

When the prompt says "FAIL CLOSED," the agent MUST:

1. Stop the current phase immediately
2. Emit a receipt explaining:
   - Which phase failed
   - Why it failed
   - What was completed before failure
3. Write the receipt to `.codex/receipts/FAIL_RECEIPT.json`
4. Do NOT continue to subsequent phases
5. Do NOT emit a TURN_RECEIPT (the FAIL_RECEIPT replaces it)

## Boot Contract

By reading this file, the execution agent acknowledges:

1. It operates under external governance — it does not self-govern.
2. It must produce artifacts, not prose-only answers.
3. It must fail closed when evidence or capability is lacking.
4. It must not use forbidden enforcement language.
5. It must emit receipts for every execution turn.
6. All paths are relative to the repository root.
7. The BOOT_RECEIPT.json must be emitted after reading this file.
