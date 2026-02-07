# Bundle Lifecycle Policy v1

## Rationale (CDR Pillar 1)

**Problem:** The repository has 90 files with no rules governing what
happens when bundles are superseded, duplicated, or become obsolete.
14 correction bundles (PATCHED, REBUILT, REPAIRED, etc.) imply parent
bundles they replace, but nothing marks those parents as superseded.
5 files are download duplicates with `(1)` / `(2)` suffixes. Without
lifecycle rules, the repository only grows and old bundles create
confusion about which version is current.

**Chosen solution:** A status-based lifecycle where every bundle gets
a lifecycle status, protected classes are exempt from deprecation, and
duplicates are resolved by keeping the original and removing the copy.

**Rejected alternative:** Directory-based archival (moving old bundles
to `os_bundles/archive/`). Rejected because Git LFS tracks by path —
renaming/moving LFS files breaks pointer references and inflates the
repo. Status fields in the catalog are cheaper and non-destructive.

## Constraints (CDR Pillar 2)

**Optimizes for:** Non-destructive lifecycle management. No files are
deleted or moved — only metadata changes.

**Sacrifices:** Disk space. Superseded bundles remain on disk. This is
acceptable because the repo is a Git LFS store where physical size is
managed by the LFS backend, not the working directory.

## Lifecycle Statuses

Every bundle in `BUNDLE_CATALOG.json` must have a `lifecycle_status`:

| Status          | Meaning                                                |
|-----------------|--------------------------------------------------------|
| `ACTIVE`        | Current, valid, in use                                 |
| `SUPERSEDED`    | Replaced by a newer bundle in the same lineage chain   |
| `DEPRECATED`    | Marked for eventual removal (retention clock started)  |
| `FROZEN`        | Immutable snapshot — exempt from deprecation            |
| `DUPLICATE`     | Identical to another file (download artifact)          |
| `ORPHANED`      | Part file without a complete set, or context lost      |

### Status Transitions

```
ACTIVE → SUPERSEDED    (when a correction bundle exists)
ACTIVE → DEPRECATED    (when explicitly marked by authority)
ACTIVE → FROZEN        (when qualifier is FROZEN_FULL_EXPORT, LTS, or VALIDATED_EXPORT)
SUPERSEDED → DEPRECATED (after retention period)
DEPRECATED → (removed)  (only by external authority, via DeltaGate)
FROZEN → (no transition) (frozen bundles never deprecate)
DUPLICATE → (removed)   (after verification, via DeltaGate)
```

No status may be changed without DeltaGate admission.

## Duplicate Resolution

### What Constitutes a Duplicate

A file is a DUPLICATE if its filename matches another file with an
added `(N)` suffix (where N is a number). This indicates a browser
or OS download collision, not a distinct version.

### Known Duplicates (as of catalog v1.0)

| Duplicate                                                          | Original                                                    |
|--------------------------------------------------------------------|-------------------------------------------------------------|
| `MB_CHAT3_MNT_DATA_PART2_20260121T185046Z (1).zip`                | `MB_CHAT3_MNT_DATA_PART2_20260121T185046Z.zip`              |
| `MetaBlooms_GitHubUploader_RunPack_20260124T224700Z_PATCHED (2).zip` | (original not in repo — `(2)` suggests prior downloads lost) |
| `MetaBlooms_OS_WHOLEOS_BASELINE_..._SHAFIX_v2 (1).zip`            | `MetaBlooms_OS_WHOLEOS_BASELINE_..._SHAFIX_v2.zip`          |
| `Metablooms_OS_EXPORT_WITH_CHAT_INDEX_20260129T060156Z (1).zip`   | `Metablooms_OS_EXPORT_WITH_CHAT_INDEX_20260129T060156Z.zip` |
| `git_uploader_bundle_reupload_20260127T145213Z (2).zip`           | (original not in repo — `(2)` suggests prior downloads lost) |

### Resolution Process

1. Mark the `(N)` file as `lifecycle_status: DUPLICATE` in the catalog
2. If the original exists: the duplicate is redundant
3. If the original does NOT exist (e.g., `(2)` without `(1)`):
   the file is the only surviving copy — mark as `ACTIVE` with a
   note that the filename reflects a download artifact
4. Actual removal requires DeltaGate admission

## Supersession Rules

### When Is a Bundle Superseded?

A bundle is SUPERSEDED when a correction bundle exists that explicitly
fixes, patches, rebuilds, or reissues it.

**Supersession qualifiers** (in the newer bundle's name):
- `PATCHED` — bug fix applied
- `REMEDIATED` — issue corrected
- `REPAIRED` — structural fix
- `FIXED` — targeted defect resolution
- `REBUILT` — regenerated from components
- `REISSUE` / `RESHIPPED` — re-released after correction

### How to Identify the Parent

The parent is identified by matching the base name minus the
correction qualifier. Examples:

| Correction Bundle | Supersedes |
|---|---|
| `MetaBlooms_OS_CANONICAL_P0_P1_MASTERY_ENFORCED_V1_CONTENT__PATCHED_20260122.zip` | `MetaBlooms_OS_CANONICAL_P0_P1_MASTERY_ENFORCED_V1_CONTENT.zip` |
| `MetaBlooms_OS_FULL_P0_EXECUTION_ENFORCED_RESHIPPED_20260127T134913Z.zip` | `MetaBlooms_OS_FULL_P0_EXECUTION_ENFORCED_20260127T134057Z.zip` |
| `MetaBlooms_OS_WHOLEOS_CANONICAL_20260121_P0FIX_REMEDIATED.zip` | `MetaBlooms_OS_WHOLEOS_CANONICAL_20260121_PAYLOAD_APPLIED_ACCEPT_OK.zip` (inferred by date+base) |

When the parent cannot be deterministically identified from the
filename alone, the lineage graph must record the relationship
with `confidence: INFERRED` rather than `confidence: DETERMINISTIC`.

### Integration Chains

Some bundles represent progressive integration rather than corrections:

```
BASELINE → WIRED → MASTERY_ENFORCED → MASTERY_INTEGRATED → FULLY_WIRED
```

In an integration chain, the later bundle does NOT supersede the
earlier one — it EXTENDS it. The earlier bundle may still be valid
for deployments that don't need the later features.

**Rule:** Only correction qualifiers (PATCHED, FIXED, etc.) create
supersession. Integration qualifiers (WIRED, INTEGRATED) create
extension, which is tracked in the lineage graph but does NOT change
lifecycle status.

## Retention Classes

### Protected (Never Deprecated)

| Qualifier           | Reason                                            |
|---------------------|---------------------------------------------------|
| `FROZEN_FULL_EXPORT`| Immutable by definition — the whole point is permanence |
| `LTS`              | Long-term support commitment                       |
| `VALIDATED_EXPORT`  | QA-verified — may be needed for audit trails       |

Protected bundles get `lifecycle_status: FROZEN` and are exempt from
all deprecation and archival processes.

### Standard Retention

Bundles not in a protected class follow standard retention:

| Status       | Retention Period | Then What                      |
|--------------|------------------|--------------------------------|
| `ACTIVE`     | Indefinite       | Remains until superseded       |
| `SUPERSEDED` | 90 days          | Transitions to DEPRECATED      |
| `DEPRECATED` | 90 days          | Eligible for removal           |
| `DUPLICATE`  | 0 days           | Eligible for removal immediately |

**Total time from supersession to removal eligibility: 180 days.**

Removal is never automatic. It always requires DeltaGate admission.

### Third-Party Binaries

Driver and utility executables (NVIDIA, printer drivers, GitHubDesktop,
gpg4win) follow vendor versioning, not MetaBlooms lifecycle:

- They are ACTIVE until a newer version of the same vendor tool exists
- They are NEVER FROZEN (vendor binaries are not MetaBlooms snapshots)
- Supersession is determined by vendor version number, not qualifier

## Segment Group Integrity

Segment groups (multi-part archives) have special rules:

1. All parts of a group share the same lifecycle status
2. You cannot deprecate part 3 of 8 — it's all or nothing
3. If any part is missing, the group is `ORPHANED`

### Known Segment Groups

| Group                              | Parts | Status  |
|------------------------------------|-------|---------|
| CHAT7_FULL_MNT_DATA_EXPORT        | 8/8   | ACTIVE  |
| chat_4_RETRY_full_mnt_data        | 2/2   | ACTIVE  |
| MetaBlooms_OS_VALIDATED_EXPORT     | 3/3   | FROZEN  |
| MetaBlooms_NON_PROJECT_FILES       | 4/4   | ACTIVE  |
| MB_CHAT3_MNT_DATA                  | 3/3   | ACTIVE  |
| MB_CHAT6_MNTDATA                   | 3/3   | ACTIVE  |

### Known Orphans

- `CHAT_DELTA_EVIDENCE_PART2.zip` — PART1 does not exist in the repo

## Failure Modes (CDR Pillar 4)

| Failure Mode | Safe State | Recovery |
|---|---|---|
| Bundle marked SUPERSEDED but correction is defective | Revert to ACTIVE status via DeltaGate | Re-mark parent as ACTIVE, mark correction as DEPRECATED |
| Protected bundle needs urgent removal (security issue) | Requires explicit override by external authority | DeltaGate admission with security justification |
| Lineage chain is wrong (parent misidentified) | Lineage graph records `confidence: INFERRED` | Correct the lineage graph and re-evaluate lifecycle statuses |
| Segment group has missing part after deprecation | Group becomes ORPHANED | Restore from LFS history or accept data loss |

## Integration with Other Policies (CDR Pillar 5)

| Policy | How Lifecycle Interacts |
|---|---|
| **DeltaGate** | All status changes and removals require DeltaGate admission |
| **BUNDLE_CATALOG.json** | `lifecycle_status` field added to each entry |
| **BUNDLE_LINEAGE.schema.json** | Supersession chains feed lifecycle status |
| **MMD** | Detects missing lifecycle statuses, orphaned parts, stale statuses |
| **SEE** | Evidence for supersession comes from filename analysis (LOCAL_FS) |
