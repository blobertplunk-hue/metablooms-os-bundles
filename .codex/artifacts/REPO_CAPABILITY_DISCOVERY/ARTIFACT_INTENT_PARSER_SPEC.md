# Artifact Intent Parser Specification

Version: 1.0
Generated: 2026-02-09

## Purpose

This document specifies how to parse, validate, interpret, and invoke each artifact type found in the MetaBlooms OS Bundles repository. It serves as the contract for any automated system or human operator that needs to interact with repository artifacts.

---

## 1. JSON Schemas (`.schema.json`)

### Location
- `.codex/schemas/*.schema.json`
- `MetaBlooms_OS/schemas/*.schema.json`

### How to Validate

1. Load the schema file as JSON.
2. Verify it contains a `title` or `$schema` field (structural minimum).
3. Use a JSON Schema validator (e.g., Python `jsonschema` library) to validate artifact instances against the schema.
4. The `run_schema_validation_gate.py` provides a reference implementation.

### Parsing Rules

- **Required fields**: Every schema defines `required` and `properties` at the root level.
- **Enum validation**: Some schemas define closed enums (e.g., `category` in `MMD_REPORT.schema.json`). New values require schema updates.
- **Nested objects**: Follow `$ref` or inline `properties` recursively.
- **Array items**: Check `items` subschema for arrays (e.g., `findings` in MMD, `bundles` in BUNDLE_CATALOG).

### Known Schemas and Their Targets

| Schema | Validates |
|--------|-----------|
| `BUNDLE_ENTRY.schema.json` | Each entry in `BUNDLE_CATALOG.json` |
| `BUNDLE_LINEAGE.schema.json` | `BUNDLE_LINEAGE.json` root object |
| `MMD_REPORT.schema.json` | `MMD_REPORT.json` root object |
| `MASTERY_DEFINITION.schema.json` | `MDEF-*.json` artifacts |
| `DECISION_RECORD.schema.json` | `DR-*.json` artifacts |
| `LESSON_PROMOTION.schema.json` | Lesson entries in `MB_STATE.json` |
| `TURN_RECEIPT.schema.json` | `TURN_RECEIPT.json` receipts |
| `INTENT_IR.schema.json` | MBQL intent intermediate representations |
| `LEARNING_EVENT.schema.json` | Learning event records |
| `TOOLBOX_REALITY.schema.json` | Toolbox reality declarations |
| `ROBUSTNESS_METRICS.schema.json` | Robustness metric reports |
| `SCENARIO_SET.schema.json` | Scenario set definitions |
| `DELTA_LEDGER.schema.json` | Delta ledger entries |

---

## 2. JSON Artifacts (`.json`)

### Location
- `.codex/artifacts/*.json`
- `.codex/receipts/*.json`
- `MetaBlooms_OS/artifacts/*.json`
- `MetaBlooms_OS/receipts/*.json`
- `MetaBlooms_OS/research/*.json`
- `MetaBlooms_OS/state/MB_STATE.json`
- `MetaBlooms_OS/patterns/MB_PATTERN_CATALOG.json`

### How to Read

1. Parse as JSON using any standard JSON parser (`json.load()` in Python).
2. Check for a top-level identifier field that indicates the artifact type:
   - `mastery_id` -> MASTERY_DEFINITION
   - `decision_id` -> DECISION_RECORD
   - `receipt_type` -> TURN_RECEIPT or FAIL_RECEIPT or BOOT_RECEIPT
   - `report_version` -> MMD_REPORT
   - `catalog_id` -> Pattern Catalog
   - `version` + `sessions_count` -> MB_STATE
   - `entries` or `bundles` -> BUNDLE_CATALOG
3. Validate against the corresponding schema (see Section 1).
4. All timestamps use ISO 8601 format with UTC timezone suffix (`Z` or `+00:00`).

### Artifact Categories

#### State File (`MB_STATE.json`)
- **Intent**: Cross-session persistent intelligence store.
- **Key sections**: `mastery_definitions` (dict), `decision_records` (dict), `lesson_promotions` (list), `source_reputation` (list), `query_patterns` (list), `intelligence_level` (int).
- **Read pattern**: Load at session start via `StateManager.__init__`, save at session end via `StateManager.save()`.
- **Staleness check**: Compare `last_boot_utc` to current time.

#### Bundle Catalog (`BUNDLE_CATALOG.json`)
- **Intent**: Full inventory of all files in `os_bundles/`.
- **Key sections**: `entries` array, each with `filename`, `category`, `size_bytes`, `sha256`.
- **Staleness check**: Compare listed filenames against actual `os_bundles/` directory listing (`run_staleness_gate.py`).

#### MMD Report (`MMD_REPORT.json`)
- **Intent**: Gap detection results.
- **Key sections**: `findings` array with `id`, `severity`, `category`, `description`; `summary` with severity counts; `total_findings`.
- **Self-consistency**: `total_findings` must equal `len(findings)`; severity counts in `summary` must match actual distribution.

#### Invariant Registry (`INVARIANT_REGISTRY.json`)
- **Intent**: Defines mechanically-verifiable invariants.
- **Key sections**: `invariants` array with `invariant_id`, `severity`, `title`, `status` (ACTIVE/SUPERSEDED/PROPOSED).
- **Evaluation**: Only ACTIVE invariants are evaluated by `run_invariant_gate.py`.

#### Delta Ledger (`DELTA_LEDGER_*.json`)
- **Intent**: Tracks proposed changes and their admission/deferral status.
- **Key sections**: `entries` with `delta_id`, `status` (ADMITTED/DEFERRED/REJECTED), `not_done_reason`.

#### Artifact Maturity (`ARTIFACT_MATURITY.json`)
- **Intent**: Tracks maturity stage of every governance artifact.
- **Key sections**: `artifacts` array with `artifact_path`, `maturity` (DRAFT/VALIDATED/ENFORCED), `schema_path`, `validator_path`, `gate_name`.

#### Pattern Catalog (`MB_PATTERN_CATALOG.json`)
- **Intent**: Architectural patterns for constraint-driven decision making.
- **Key sections**: `patterns` array with `pattern_id`, `strengths`, `weaknesses`, `required_capabilities`, `forbidden_when`.

---

## 3. Python Engines (`.py`)

### Location
- `MetaBlooms_OS/engines/*.py` (6 engines)
- `MetaBlooms_OS/validators/gates.py` (validation gates)
- `MetaBlooms_OS/state/state_manager.py` (persistence)
- `MetaBlooms_OS/mpp.py` (orchestrator)
- `MetaBlooms_OS/boot.py` (boot sequence)

### How to Invoke

#### Boot Sequence (Recommended Entry Point)
```python
# In ChatGPT Code Interpreter or any Python environment:
import sys
sys.path.insert(0, "/path/to/MetaBlooms_OS")
from boot import boot
mpp, state_mgr, os_root = boot()
```

This automatically:
1. Finds the OS root directory
2. Loads or initializes cross-session state
3. Validates the OS tree
4. Runs validation gates
5. Emits boot receipt
6. Returns ready-to-use MPP orchestrator

#### Running the Full Pipeline
```python
# After boot:
ready, ctx = mpp.run_preparation_phases("STRUCTURAL_ANALYSIS", "task description", "domain")
if ready:
    receipt = mpp.run_execution_phases(claims, mastery_definition, build_artifacts, execution_results)
```

#### Individual Engine Invocation
```python
from state.state_manager import StateManager
from engines.mastery_engine import MasteryEngine
from engines.see_engine import SEEEngine
from engines.mmd_engine import MMDEngine
from engines.decision_engine import DecisionEngine
from engines.rrp_engine import RRPEngine
from engines.assimilation_engine import AssimilationEngine

state_mgr = StateManager(os_root)
mastery = MasteryEngine(os_root, state_mgr)
see = SEEEngine(os_root, state_mgr, {"web_access": "NO"})
mmd = MMDEngine(os_root, state_mgr)
decision = DecisionEngine(os_root, state_mgr)
rrp = RRPEngine(os_root)
assimilation = AssimilationEngine(os_root, state_mgr)
```

### Engine Contract Summary

| Engine | Primary Method | Input | Output |
|--------|---------------|-------|--------|
| `MasteryEngine` | `create_mastery_definition(...)` | Task + domain + criteria | `MDEF-*.json` |
| `SEEEngine` | `run(claims)` | Claim list | Evidence map + query log |
| `MMDEngine` | `run(mastery_def, see_results)` | Phase results | MMD report (PASS/FAIL) |
| `DecisionEngine` | `make_decision(type, context, ...)` | Constraints + candidates | `DR-*.json` |
| `RRPEngine` | `evaluate(artifacts, mastery)` | Build artifacts | Defect list |
| `AssimilationEngine` | `run(mastery, results, mmd, rrp)` | Execution artifacts | Lessons + promotions |
| `StateManager` | `save()` / `store_*()` | Various | `MB_STATE.json` |

### Error Handling
- All engines return `(result, errors)` tuples where applicable.
- Non-empty `errors` list indicates failure; `result` will be `None`.
- FAIL CLOSED pattern: critical failures halt the pipeline via `MPPOrchestrator.fail_closed()`.

---

## 4. Shell Scripts (`.sh`)

### Location
- `scripts/mb-upload.sh` (upload pipeline)
- `.codex/validators/install_hooks.sh` (hook installer)

### How to Run

#### mb-upload.sh (Android/Termux)
```bash
# First-time setup:
mb-upload --setup

# List available files:
mb-upload --list

# Dry run (preview without uploading):
mb-upload --dry-run

# Upload all files:
mb-upload

# Upload filtered:
mb-upload "*.zip"

# Upload specific file:
mb-upload somefile.zip
```

**Prerequisites**: Termux with `git`, `git-lfs`, `coreutils`, `openssh`. Storage access via `termux-setup-storage`.

**Behavioral Patterns**:
- IDEMPOTENT: Re-running skips files already in `os_bundles/`.
- FAIL_CLOSED: Unknown extensions are rejected unless user explicitly adds to `.gitattributes`.
- MONOTONIC: Files are only added, never removed or modified.
- Push retry: 4 attempts with exponential backoff (2s, 4s, 8s, 16s).

#### install_hooks.sh (Git Hook Setup)
```bash
sh .codex/validators/install_hooks.sh
```

Installs a pre-commit hook at `.git/hooks/pre-commit` that runs `run_governance_gate.py`. Prompts before overwriting existing hooks.

---

## 5. Markdown Policies (`.md`)

### Location
- `.codex/policies/*.md` (13 policy documents)
- `.codex/kernel/BOOT.md` (bootstrap contract)
- `MetaBlooms_OS/policies/*.md` (duplicate set for sandbox)
- `MetaBlooms_OS/BOOT_PROMPT.md` (boot prompt)

### How to Interpret

Markdown policies are **normative documents** that define governance rules. They are not executable code but are mechanically validated for structural completeness by `run_policy_structure_gate.py`.

#### Structural Requirements by Policy

| Policy | Required Content |
|--------|-----------------|
| `SUPER_PROMPT_v2.3.md` | All MPP phases (0-7), FORBIDDEN LANGUAGE section, BOOT reference |
| `CDR_v2.md` | 7 pillars (Proactive Rationale through Mandatory Attestation), violation classes |
| `SEE_ENGINE_v1.md` | Evidence sources, method selection, quality ranks (DIRECT_OBSERVATION, COMPUTED_VERIFICATION), evidence strengths (CONFIRMED, SUPPORTED, UNSUPPORTED), BUNDLE_INTERNAL_EVENTS |
| `RRP_v1.md` | BUILD/EVALUATE/REWRITE cycle, max iteration bound, convergence test |
| `DELTAGATE_v1.md` | PROPOSE/ADMIT/REJECT flow |
| `BUNDLE_LIFECYCLE_v1.md` | 6 lifecycle statuses: ACTIVE, SUPERSEDED, DEPRECATED, FROZEN, DUPLICATE, ORPHANED |
| `LEARNING_PIPELINE_v1.md` | RCA, EVT_FAIL, EVT_LEARNING, corrective actions |
| `MBQL_v1.md` | NLQ section, FROM/WHERE/SELECT/INTENT_IR concepts, INVARIANT evaluation |
| `ARTIFACT_MATURITY_v1.md` | DRAFT/VALIDATED/ENFORCED stages, demotion rules |
| `MB_MASTER_SPEC_v1.md` | 6 phases: SURFACE, DETECT, PREPARE, REFUSE, EXECUTE, ASSIMILATE |

#### Interpretation Rules

1. **Headings define sections**: `##` and `###` headings delimit policy sections.
2. **ALL CAPS terms are defined terms**: FAIL CLOSED, MASTERY_DEFINITION, etc. have specific meanings.
3. **Cross-references use file paths**: References like `.codex/schemas/MASTERY_DEFINITION.schema.json` must resolve to existing files.
4. **Version suffix**: `_v1.md`, `_v2.md` indicate versioning. Higher versions supersede lower versions.
5. **Forbidden language**: Agent output must not contain: enforced, verified, running, active, wired, booted, compliant, guaranteed (as standalone words). Bundle filenames are exempt.

---

## 6. ZIP Bundles (Binary Artifacts)

### Location
- `os_bundles/*.zip`
- `os_bundles/*.zip.part*` (segmented archives)

### How to Extract and Catalog

#### Extraction
```bash
# Standard ZIP:
unzip -o os_bundles/MetaBlooms_OS_SOME_BUNDLE.zip -d /tmp/extracted/

# Segmented archives (reassemble first):
cat os_bundles/CHAT7_FULL_MNT_DATA_EXPORT.part00{0..7} > /tmp/reassembled.zip
unzip -o /tmp/reassembled.zip -d /tmp/extracted/
```

#### Cataloging
1. For each file in `os_bundles/`, compute SHA-256 hash.
2. Classify by naming pattern (see CLAUDE.md for taxonomy).
3. Record in `BUNDLE_CATALOG.json` with fields conforming to `BUNDLE_ENTRY.schema.json`:
   - `filename`: exact filename
   - `category`: one of `os_bundle`, `chat_export`, `driver`, `utility`, etc.
   - `size_bytes`: file size
   - `sha256`: hex digest
   - `naming_convention_compliant`: boolean
4. For segmented archives, record each part separately and note the segment group.

#### LFS Considerations
- All ZIP bundles are stored via Git LFS (tracked in `.gitattributes`).
- The files in the working tree are LFS pointers (small text files), not the actual binary content.
- To access actual content: `git lfs pull` or `git lfs fetch`.
- Do NOT attempt to read LFS pointer files as binary data -- they contain only pointer metadata.

#### Naming Convention Parsing
```
[Date_]MetaBlooms_OS_<FEATURE_CHAIN>_[TIMESTAMP].zip
```
- **Date prefix**: `2026-01-17_` format (optional)
- **Timestamp suffix**: ISO 8601 `YYYYMMDDTHHMMSSZ`
- **Feature chain**: Underscore-separated descriptors joined with `PLUS`
- **Version qualifiers**: BASELINE, CANONICAL, PATCHED, VALIDATED_EXPORT, FROZEN_FULL_EXPORT, etc.
- **Phase markers**: P0, P1, P2, P3

---

## 7. Executable Installers (`.exe`)

### Location
- `os_bundles/*.exe`

### How to Catalog
- These are third-party driver and utility installers (NVIDIA, printer drivers, GitHub Desktop, gpg4win).
- They do NOT follow MetaBlooms naming conventions.
- Catalog with `category: "driver"` or `category: "utility"`.
- Do NOT attempt to execute or analyze these binaries within the repository context.

---

## 8. Educational Content (`.rtf`)

### Location
- `os_bundles/*.rtf`

### How to Catalog
- Rich Text Format documents containing educational content (ELAR resources, lesson plans).
- Tracked via Git LFS (`.rtf` pattern in `.gitattributes`).
- Catalog with `category: "educational"`.
- Can be opened with any RTF-compatible text editor or word processor.

---

## 9. Segmented Archives (`.part*`)

### Location
- `os_bundles/CHAT7_FULL_MNT_DATA_EXPORT.part00{0..7}`
- `os_bundles/chat_4_RETRY_full_mnt_data_export.zip.part{1,2}`
- `os_bundles/MetaBlooms_OS_VALIDATED_EXPORT_*.zip.part{1,2}`

### How to Reassemble
```bash
# Concatenate parts in order:
cat basename.part000 basename.part001 ... > reassembled.zip
# Then extract:
unzip reassembled.zip
```

### Cataloging Rules
- Each part is cataloged individually.
- Parts share a `segment_group` identifier.
- Total size is the sum of all parts in the group.
- Integrity verification requires reassembling and testing the combined archive.
