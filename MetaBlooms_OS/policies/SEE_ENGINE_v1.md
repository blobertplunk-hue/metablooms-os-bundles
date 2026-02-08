# SEE Engine Specification v1.0

## Search for Evidence Engine -- Recursive, Self-Improving Evidence Gathering

**Version:** 1.0
**Status:** PROPOSED (requires external admission)
**Scope:** All governance runs against `metablooms-os-bundles` and any repository adopting BOOT v1
**Replaces:** The informal SEE definition in BOOT.md ("perform web searches and log them")
**Binding authority:** External operator only. This spec is a proposal until admitted.

---

## 0. DESIGN PHILOSOPHY

SEE exists to answer one question: **What evidence supports or refutes this claim?**

SEE is not a search engine wrapper. It is a structured evidence-gathering engine that:

1. Selects the right method for the claim type
2. Ranks evidence by quality
3. Classifies evidence strength
4. Resolves conflicts between sources
5. Tracks its own effectiveness and improves over time

SEE operates under the same constraints as the execution agent: it produces evidence, not verdicts. Evidence is submitted to MMD and ultimately to external authority for admission.

### 0a. Relationship to BOOT v1 Governance

SEE is Phase 1 of the Mandatory Process Pipeline (MPP) defined in SUPER_PROMPT. It receives claims from Phase 0 (Claim Enumeration) and feeds findings into Phase 2 (MMD). SEE does not skip phases, does not enforce, and does not declare compliance. SEE gathers. Others decide.

### 0b. Fail-Closed Principle

If SEE cannot gather evidence for a claim, it marks that claim with an evidence state (UNSUPPORTED or UNFALSIFIABLE). It does not fabricate evidence. It does not infer agreement from silence. Missing evidence is reported, never hidden.

---

## 1. EVIDENCE SOURCE TAXONOMY

Every piece of evidence gathered by SEE must be tagged with exactly one source type. Source types are fixed; adding a new source type requires a version bump to this specification.

### 1.1 LOCAL_FS -- Filesystem Observations

**What it covers:** File existence checks, file size measurement, filename pattern matching, directory listing, file extension extraction, file count enumeration.

**How it works:**
- `ls`, `stat`, `wc`, or equivalent shell commands
- Glob pattern matching against directory contents
- Direct `Read` tool invocations for non-binary files

**Availability requirement:** Filesystem read access (declared in ENVIRONMENT_DECLARATION.json as `filesystem_write: true` or shell access available).

**Produces evidence for:** STRUCTURAL claims, NAMING claims, catalog generation.

**Example evidence record:**
```json
{
  "source_type": "LOCAL_FS",
  "operation": "ls os_bundles/MetaBlooms_OS_VALIDATED_EXPORT.zip",
  "result": "file exists, 134 bytes (LFS pointer)",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.2 GIT_HISTORY -- Git Log, Diff, and Branch Analysis

**What it covers:** Commit messages, commit timestamps, file addition/removal history, branch topology, authorship, merge history.

**How it works:**
- `git log` with appropriate filters (path, date range, author)
- `git diff` between commits or branches
- `git show` for specific commit contents
- `git branch -a` for branch enumeration

**Availability requirement:** Git must be initialized in the repository. Shell access required.

**Produces evidence for:** TEMPORAL claims (when was X added), PROVENANCE claims (who added X, what commit introduced X), STRUCTURAL claims (has the repo structure changed).

**Example evidence record:**
```json
{
  "source_type": "GIT_HISTORY",
  "operation": "git log --oneline --follow -- os_bundles/MetaBlooms_OS_VALIDATED_EXPORT.zip",
  "result": "3 commits touching this file, most recent: abc1234 2026-01-28",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.3 LFS_METADATA -- Git LFS Pointer and Tracking Inspection

**What it covers:** Whether a file is tracked by LFS, LFS pointer file contents (OID, size), `.gitattributes` pattern coverage, `git lfs ls-files` output.

**How it works:**
- `git lfs ls-files` to enumerate tracked files
- Reading `.gitattributes` to determine tracking rules
- Inspecting individual pointer files (first ~200 bytes contain LFS pointer if applicable)
- `git lfs pointer --check` for verification

**Availability requirement:** `git lfs` must be installed and initialized. Declared in ENVIRONMENT_DECLARATION.json as `git_lfs_available: true`.

**Produces evidence for:** INTEGRITY claims, STRUCTURAL claims (LFS tracking gaps), NAMING claims (extension coverage).

**Example evidence record:**
```json
{
  "source_type": "LFS_METADATA",
  "operation": "git lfs ls-files --name-only | grep VALIDATED_EXPORT",
  "result": "MetaBlooms_OS_VALIDATED_EXPORT.zip is LFS-tracked; .part1 and .part2 are NOT tracked",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.4 SCHEMA_VALIDATION -- JSON Schema Conformance Checks

**What it covers:** Validating generated artifacts against their declared JSON schemas. Checking that catalog entries conform to `BUNDLE_ENTRY.schema.json`. Verifying receipt schemas.

**How it works:**
- Parse the JSON artifact
- Parse the schema definition from `.codex/schemas/`
- Validate each field against schema constraints (type, enum, pattern, required)
- Report per-field pass/fail

**Availability requirement:** Ability to read JSON files and perform programmatic validation (shell access with `jq` or equivalent, or agent-internal JSON parsing).

**Produces evidence for:** STRUCTURAL claims (schema compliance), INTEGRITY claims (artifact validity).

**Example evidence record:**
```json
{
  "source_type": "SCHEMA_VALIDATION",
  "operation": "validate BUNDLE_CATALOG.json entries against BUNDLE_ENTRY.schema.json",
  "result": "90/90 entries pass required-field check; 13 entries have lfs_tracked=false (expected per known gap)",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.5 HASH_VERIFICATION -- SHA-256 Computation and Comparison

**What it covers:** Computing SHA-256 (or other cryptographic hashes) of files and comparing them against expected values. Verifying that LFS pointer OIDs match actual file content. Verifying receipt integrity.

**How it works:**
- `sha256sum <filepath>` or equivalent
- Compare computed hash against stored hash in receipts or catalog
- For LFS files: compare OID in pointer against stored OID

**Availability requirement:** Shell access with `sha256sum` or equivalent. Declared in ENVIRONMENT_DECLARATION.json as `real_hashing_available: true`.

**Produces evidence for:** INTEGRITY claims (file not corrupted, file matches expected hash), PROVENANCE claims (receipt chain integrity).

**Important limitation:** For LFS pointer files, the hash of the pointer file itself is NOT the hash of the underlying content. This distinction must be documented in every hash evidence record.

**Example evidence record:**
```json
{
  "source_type": "HASH_VERIFICATION",
  "operation": "sha256sum .codex/receipts/BOOT_RECEIPT.json",
  "result": "9f605e667ff19d3c47b6bdd7e563f2e7ae05b67701f8f3f8d5e3de2dceb0783c",
  "note": "Hash of actual file on disk, not LFS content",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.6 WEB_SEARCH -- Internet Search Queries

**What it covers:** Searching the public internet for documentation, specifications, best practices, community consensus, and authoritative references.

**How it works:**
- Submit a search query via the `WebSearch` tool
- Evaluate returned results for relevance and authority
- Record every query, even those that return no useful results
- Classify each result source (see Section 3: Source Quality Ranking)

**Availability requirement:** Web access must be available. Declared in ENVIRONMENT_DECLARATION.json as `web_access: "YES"`. If `web_access` is `"NO"` or `"UNKNOWN"`, this source type is UNAVAILABLE and SEE enters SOURCE-LIMITED MODE for any claim that requires it.

**Produces evidence for:** ARCHITECTURAL claims, COMPARATIVE claims, PRESCRIPTIVE claims.

**Example evidence record:**
```json
{
  "source_type": "WEB_SEARCH",
  "query": "git lfs best practices large binary repositories 2026",
  "results_evaluated": 5,
  "results_accepted": 2,
  "results_rejected": 3,
  "rejection_reasons": ["outdated (2019)", "unrelated topic", "paywalled"],
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.7 WEB_FETCH -- Targeted URL Retrieval

**What it covers:** Fetching a specific known URL to retrieve documentation, specifications, API references, or other structured content.

**How it works:**
- Submit a URL via the `WebFetch` tool with an extraction prompt
- Parse and evaluate the returned content
- Record the URL, the extraction prompt, and whether the content was useful

**Availability requirement:** Same as WEB_SEARCH -- requires `web_access: "YES"`.

**Produces evidence for:** ARCHITECTURAL claims (official documentation), PRESCRIPTIVE claims (specification text), INTEGRITY claims (upstream version checks).

**Example evidence record:**
```json
{
  "source_type": "WEB_FETCH",
  "url": "https://git-lfs.com/spec/v1",
  "extraction_prompt": "What is the LFS pointer file format specification?",
  "result_useful": true,
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.8 PRIOR_ARTIFACTS -- Evidence from Previous Governance Runs

**What it covers:** Referencing artifacts, receipts, catalogs, and reports from previous SEE runs or governance sessions stored in `.codex/`.

**How it works:**
- Read prior `SEE_QUERY_LOG.json`, `SOURCE_LEDGER.json`, `BUNDLE_CATALOG.json`, `MMD_REPORT.json`, `TURN_RECEIPT.json`, etc.
- Extract specific claims, evidence states, and findings from prior runs
- Compare current observations against prior documented state

**Availability requirement:** Prior artifacts must exist in `.codex/`. Filesystem read access required.

**Produces evidence for:** TEMPORAL claims (has X changed since last run), NAMING claims (convention was established in prior run), STRUCTURAL claims (prior catalog documented this file).

**Staleness rule:** Prior artifacts older than 30 days should be flagged as STALE. They still count as evidence but at reduced quality (see Section 3). The staleness threshold is configurable per deployment.

**Example evidence record:**
```json
{
  "source_type": "PRIOR_ARTIFACTS",
  "artifact_path": ".codex/artifacts/BUNDLE_CATALOG.json",
  "artifact_timestamp_utc": "2026-02-06T00:00:00Z",
  "extracted_fact": "Prior catalog lists 90 files with 13 LFS tracking gaps",
  "staleness": "FRESH",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.9 CROSS_REFERENCE -- Derived Evidence from Combining Sources

**What it covers:** Evidence that is not directly observed from any single source but is derived by comparing, combining, or correlating two or more other evidence items.

**How it works:**
- Take two or more evidence records from other source types
- Apply a logical operation: comparison, intersection, difference, temporal ordering
- Document the input evidence IDs and the derivation logic
- The result is a new evidence record with source_type CROSS_REFERENCE

**Availability requirement:** Requires at least two prior evidence records to combine.

**Produces evidence for:** Any claim type, but always at reduced quality (see Section 3) unless the inputs are both DIRECT_OBSERVATION or COMPUTED_VERIFICATION quality.

**Derivation operations:**
| Operation | Description | Example |
|-----------|-------------|---------|
| COMPARE | Two values match or differ | LFS ls-files count vs. catalog lfs_tracked count |
| TEMPORAL_ORDER | Event A happened before/after B | Commit timestamp vs. bundle timestamp |
| SET_DIFFERENCE | Items in A but not in B | Files on disk not in catalog |
| CONSISTENCY_CHECK | Multiple sources agree on a fact | File size from stat matches catalog size_bytes |
| COVERAGE_ANALYSIS | Fraction of X covered by Y | Extensions in os_bundles/ covered by .gitattributes |

**Example evidence record:**
```json
{
  "source_type": "CROSS_REFERENCE",
  "operation": "SET_DIFFERENCE",
  "input_evidence_ids": ["ev_local_fs_001", "ev_lfs_meta_003"],
  "derivation": "Files present on disk with extensions not covered by .gitattributes LFS rules",
  "result": "13 files with .part* and .rtf extensions are on disk but not LFS-tracked",
  "timestamp_utc": "2026-02-06T12:00:00Z"
}
```

### 1.10 BUNDLE_INTERNAL_EVENTS -- Learning and Failure Events from Inside Bundles

**What it covers:** Structured events emitted by the OS learning pipeline inside bundles — failure events (`EVT_FAIL_*`), learning events (`EVT_LEARNING_*`), RCA reports, guard installation records, and corrective action attestations.

**What this changes:** OS bundles are not opaque blobs. They contain internal architecture: `tools/audit/`, `tools/rca/`, `events/`, and `audit/` directories. The learning pipeline inside the bundle emits queryable NDJSON events that record what failed, why, what changed, and whether the change prevented recurrence.

**How it works:**
- Extract or read `events/LEARNING_EVENTS.ndjson` from inside the bundle
- Parse each line as a JSON event per `LEARNING_EVENT.schema.json`
- Query events by type: `EVT_FAIL_*` for failure history, `EVT_LEARNING_*` for structural changes
- Cross-reference `payload.supersedes_bundle` to establish lineage evidence

**Availability requirement:** Bundle must be extractable and must contain `events/LEARNING_EVENTS.ndjson`. Bundles predating the learning pipeline will not have this directory.

**Produces evidence for:**
- LINEAGE claims (which bundle supersedes which — stronger than filename inference)
- BEHAVIORAL claims (what the system actually does differently now)
- INTEGRITY claims (guards verify preconditions before extraction)
- TEMPORAL claims (event timestamps establish ordering)

**Quality rank:** DIRECT_OBSERVATION — these are machine-emitted, timestamped, tied to specific RCA reports. This is the highest quality evidence for behavioral claims.

**Key event types for SEE:**

| Event Type | What It Proves |
|---|---|
| `EVT_LEARNING_ROOT_CAUSE_IDENTIFIED` | A specific failure was investigated and understood |
| `EVT_LEARNING_CORRECTIVE_ACTION_RATIFIED` | A structural fix was applied — proves supersession |
| `EVT_LEARNING_GUARD_INSTALLED` | A prevention mechanism now exists |
| `EVT_FAIL_*` with `prevented_by` field | A guard caught a failure — proves the learning loop works |

**Example evidence record:**
```json
{
  "source_type": "BUNDLE_INTERNAL_EVENTS",
  "operation": "query events/LEARNING_EVENTS.ndjson WHERE event_type = EVT_LEARNING_CORRECTIVE_ACTION_RATIFIED",
  "result": "1 event found: fs_root_guard.py installed as corrective action for EVT_FAIL_WRITE_PERMISSION",
  "timestamp_utc": "2026-02-07T13:56:32Z"
}
```

**Schema reference:** `.codex/schemas/LEARNING_EVENT.schema.json`
**Policy reference:** `.codex/policies/LEARNING_PIPELINE_v1.md`

### 1.11 BUNDLE_AUDIT_RECEIPTS -- Structured Audit Receipts from Inside Bundles

**What it covers:** JSON receipt files produced by bundle-internal audit tools — `FS_ROOT_RECEIPT.json`, `LEARNING_PIPELINE_RECEIPT.json`, and any future `audit/*.json` files that record the outcome of pre-condition checks, pipeline executions, or compliance gates within an OS bundle.

**What this changes:** While BUNDLE_INTERNAL_EVENTS captures the event stream, BUNDLE_AUDIT_RECEIPTS captures the point-in-time attestations. A receipt proves that a specific check was run, what the result was, and when it happened. Receipts are the bundle's equivalent of governance turn receipts.

**How it works:**
- Extract or read `audit/*.json` from inside the bundle
- Parse each receipt as a JSON object
- Verify receipt structure (must contain at minimum: `receipt_type`, `timestamp_utc`, `status`)
- Cross-reference receipts with learning events for corroboration

**Availability requirement:** Bundle must be extractable and must contain `audit/` directory. Not all bundles will have audit receipts — only those built after the learning pipeline was introduced.

**Produces evidence for:**
- INTEGRITY claims (receipt proves a check was run and passed/failed)
- BEHAVIORAL claims (receipt shows what the bundle's audit tools actually verified)
- TEMPORAL claims (receipt timestamps establish when checks ran)
- LINEAGE claims (pipeline receipts may reference predecessor bundles)

**Quality rank:** COMPUTED_VERIFICATION — receipts are deterministic outputs from specific audit tools, reproducible given the same inputs.

**Example evidence record:**
```json
{
  "source_type": "BUNDLE_AUDIT_RECEIPTS",
  "operation": "read audit/FS_ROOT_RECEIPT.json from MetaBlooms_OS_BOOT_HARDENED_*.zip",
  "result": "FS root guard passed: writable root verified at /target/path, SHA-256 of guard matches expected",
  "timestamp_utc": "2026-02-07T14:00:00Z"
}
```

**Relationship to BUNDLE_INTERNAL_EVENTS:** Events are the stream (what happened over time). Receipts are the snapshots (what was true at a specific moment). Together they provide both history and attestation.

---

## 2. METHOD SELECTION LOGIC

For each claim processed by SEE, the engine must select which evidence sources to consult and in what order. Method selection is determined by claim type. The engine tries methods in priority order and stops when sufficient evidence is gathered (evidence_strength reaches CONFIRMED or SUPPORTED) or all methods are exhausted.

### 2.1 Claim Type Definitions

| Claim Type | Description | Example |
|------------|-------------|---------|
| STRUCTURAL | File exists, file is categorized correctly, directory layout is correct | "MetaBlooms_OS_VALIDATED_EXPORT.zip exists in os_bundles/" |
| NAMING | Naming convention is followed, pattern matches spec | "Bundle follows [Date_]MetaBlooms_OS_<CHAIN>_[TIMESTAMP].zip" |
| INTEGRITY | File is not corrupted, hash matches, LFS pointer is valid | "BOOT_RECEIPT.json SHA-256 matches recorded value" |
| TEMPORAL | Event ordering, freshness, staleness | "Bundle X was added after bundle Y" |
| PROVENANCE | Origin, authorship, chain of custody | "This file was committed by user Z in commit abc1234" |
| ARCHITECTURAL | Design is sound, approach is correct, pattern is appropriate | "Git LFS is appropriate for storing 90 binary bundles" |
| COMPARATIVE | X is better/worse/different than Y | "LFS is more suitable than raw git for files >100MB" |
| PRESCRIPTIVE | You should do X, best practice is Y | "*.part* files should be added to .gitattributes" |

### 2.2 Method Priority Tables

Each table shows methods in priority order (try first method first). The "Fallback" column indicates what to do if the primary method is unavailable.

#### STRUCTURAL Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | LOCAL_FS | File exists on disk, stat returns valid data | None -- if filesystem unavailable, FAIL CLOSED |
| 2 | LFS_METADATA | Extension is tracked, pointer file is valid | Skip if git-lfs unavailable |
| 3 | SCHEMA_VALIDATION | Catalog entry conforms to schema | Skip if schema file missing |
| 4 | PRIOR_ARTIFACTS | Prior catalog agrees with current observation | Skip if no prior artifacts |

**Minimum for CONFIRMED:** LOCAL_FS observation succeeds.
**Minimum for SUPPORTED:** LOCAL_FS + at least one corroborating source.

#### NAMING Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | LOCAL_FS | Filename matches expected pattern via regex | None -- filename must be observable |
| 2 | PRIOR_ARTIFACTS | Prior catalog or policy defines the convention | Skip if no prior artifacts |
| 3 | SCHEMA_VALIDATION | Extracted fields pass schema enum/pattern checks | Skip if schema unavailable |
| 4 | CROSS_REFERENCE | Compare filename against convention doc and flag deviations | Requires at least 2 inputs |

**Minimum for CONFIRMED:** LOCAL_FS pattern match succeeds and pattern is defined in BOOT.md or policy.
**Minimum for SUPPORTED:** LOCAL_FS match + PRIOR_ARTIFACTS agreement.

#### INTEGRITY Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | HASH_VERIFICATION | Compute SHA-256, compare to expected | If hashing unavailable, mark UNFALSIFIABLE |
| 2 | LFS_METADATA | Pointer OID matches, file size matches pointer declared size | Skip if git-lfs unavailable |
| 3 | LOCAL_FS | File size is non-zero and plausible | Always available if filesystem is |
| 4 | CROSS_REFERENCE | Compare hash from current run against prior receipt hash | Requires prior receipt |

**Minimum for CONFIRMED:** HASH_VERIFICATION succeeds with matching hash.
**Minimum for SUPPORTED:** LFS_METADATA + LOCAL_FS both consistent.

#### TEMPORAL Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | GIT_HISTORY | Commit timestamps, log ordering | If git unavailable, try PRIOR_ARTIFACTS |
| 2 | LOCAL_FS | File modification timestamps (less reliable) | Always available |
| 3 | PRIOR_ARTIFACTS | Timestamps recorded in prior catalogs/receipts | Skip if no prior artifacts |
| 4 | CROSS_REFERENCE | Compare timestamps across sources | Requires 2+ inputs |

**Minimum for CONFIRMED:** GIT_HISTORY provides unambiguous ordering.
**Minimum for SUPPORTED:** Two independent timestamp sources agree.

#### PROVENANCE Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | GIT_HISTORY | Author, committer, commit message, GPG signature | If git unavailable, mark UNSUPPORTED |
| 2 | LFS_METADATA | LFS upload metadata if available | Skip if unavailable |
| 3 | PRIOR_ARTIFACTS | Prior receipts documenting who/when/why | Skip if no prior artifacts |

**Minimum for CONFIRMED:** GIT_HISTORY provides author + commit hash.
**Minimum for SUPPORTED:** GIT_HISTORY + PRIOR_ARTIFACTS agree.

#### ARCHITECTURAL Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | WEB_SEARCH | Industry best practices, official documentation | If unavailable, enter SOURCE-LIMITED MODE |
| 2 | WEB_FETCH | Specific documentation URLs | If unavailable, skip |
| 3 | PRIOR_ARTIFACTS | Previous governance runs documented rationale | Skip if no prior artifacts |
| 4 | CROSS_REFERENCE | Combine web findings with local observations | Requires inputs from above |

**Minimum for CONFIRMED:** Authoritative web source explicitly supports the architectural choice.
**Minimum for SUPPORTED:** PRIOR_ARTIFACTS rationale + WEB_SEARCH corroboration.
**SOURCE-LIMITED MODE:** If web is unavailable, mark claim as PARTIAL with explicit note: "Architectural claim cannot be fully evaluated without web access."

#### COMPARATIVE Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | WEB_SEARCH | Benchmarks, comparisons, trade-off analyses | REQUIRED -- if unavailable, mark UNFALSIFIABLE |
| 2 | WEB_FETCH | Specific comparison documents or benchmarks | Skip if unavailable |
| 3 | PRIOR_ARTIFACTS | Prior comparative analysis exists | Skip if none |
| 4 | CROSS_REFERENCE | Synthesize findings | Requires inputs |

**Minimum for CONFIRMED:** At least two independent authoritative sources agree on the comparison.
**Minimum for SUPPORTED:** One authoritative source with no contradicting evidence.
**Hard requirement:** WEB_SEARCH is required. Without it, the claim CANNOT reach CONFIRMED or SUPPORTED.

#### PRESCRIPTIVE Claims

| Priority | Method | What to Check | Fallback |
|----------|--------|---------------|----------|
| 1 | WEB_SEARCH | Best practice documentation, official recommendations | If unavailable, enter SOURCE-LIMITED MODE |
| 2 | WEB_FETCH | Specific recommendation documents (RFCs, specs, guides) | Skip if unavailable |
| 3 | PRIOR_ARTIFACTS | Prior policy decisions, accepted governance recommendations | Skip if none |
| 4 | LOCAL_FS | Does current state already follow the prescription? | Observational only |
| 5 | CROSS_REFERENCE | Combine prescription source with current state observation | Requires inputs |

**Minimum for CONFIRMED:** Authoritative source prescribes the action + current state shows it is needed.
**Minimum for SUPPORTED:** PRIOR_ARTIFACTS policy + LOCAL_FS observation of gap.
**SOURCE-LIMITED MODE:** If web is unavailable, prescriptive claims based solely on PRIOR_ARTIFACTS are capped at PARTIAL strength.

### 2.3 Fallback Chain Summary

When the primary method for a claim type is unavailable:

```
LOCAL_FS unavailable      -> FAIL CLOSED (cannot operate without filesystem)
GIT_HISTORY unavailable   -> Fall back to PRIOR_ARTIFACTS + LOCAL_FS timestamps
LFS_METADATA unavailable  -> Fall back to LOCAL_FS (file size checks) + PRIOR_ARTIFACTS
SCHEMA_VALIDATION unavail -> Fall back to manual field-by-field check via LOCAL_FS reads
HASH_VERIFICATION unavail -> Mark integrity claims as UNFALSIFIABLE
WEB_SEARCH unavailable    -> Enter SOURCE-LIMITED MODE; cap evidence at PARTIAL for claims requiring web
WEB_FETCH unavailable     -> Same as WEB_SEARCH unavailable
PRIOR_ARTIFACTS unavail   -> Proceed without; note "first run, no prior artifacts" in evidence record
CROSS_REFERENCE unavail   -> Always available if 2+ other evidence records exist
```

### 2.4 SOURCE-LIMITED MODE

When `web_access` is not `"YES"`, SEE enters SOURCE-LIMITED MODE. In this mode:

1. All claim types that have WEB_SEARCH or WEB_FETCH in their method priority table are flagged
2. Evidence strength for those claims is capped at PARTIAL
3. The SOURCE_LEDGER must include an entry: `{"mode": "SOURCE-LIMITED", "reason": "web_access != YES", "affected_claim_types": [...]}`
4. MMD (Phase 2) is notified of the limitation so it can flag it in the MMD_REPORT

SOURCE-LIMITED MODE is not a failure. It is an honest declaration of capability constraints.

---

## 3. SOURCE QUALITY RANKING

Every evidence record is assigned a quality rank. Quality ranks are ordered from highest to lowest. When multiple evidence records exist for a claim, the highest-quality record determines the overall evidence quality, but lower-quality records can corroborate.

### 3.1 Quality Ranks

| Rank | Name | Definition | Typical Source Types |
|------|------|------------|---------------------|
| Q1 | DIRECT_OBSERVATION | The agent executed a command or read a file and observed the result firsthand in this session | LOCAL_FS, GIT_HISTORY, LFS_METADATA |
| Q2 | COMPUTED_VERIFICATION | The agent performed a deterministic computation (hash, schema validation) and the result is reproducible | HASH_VERIFICATION, SCHEMA_VALIDATION |
| Q3 | PRIOR_ARTIFACT_REFERENCE | A previous governed run documented this fact; the prior run's receipts are intact | PRIOR_ARTIFACTS |
| Q4 | AUTHORITATIVE_WEB_SOURCE | Official documentation, RFCs, specifications, project maintainer statements | WEB_SEARCH, WEB_FETCH |
| Q5 | COMMUNITY_WEB_SOURCE | Stack Overflow answers, blog posts, tutorials, forum discussions | WEB_SEARCH, WEB_FETCH |
| Q6 | INFERENCE | Derived from other evidence via logical reasoning; no single source directly states the fact | CROSS_REFERENCE |

### 3.2 Quality Assignment Rules

1. **Source type determines the baseline quality.** LOCAL_FS observations are Q1. HASH_VERIFICATION results are Q2. And so on per the table above.

2. **Staleness degrades quality by one rank.** A PRIOR_ARTIFACTS record older than 30 days drops from Q3 to Q4 equivalent. A web source older than 1 year drops one rank.

3. **Contradicted evidence cannot be higher than Q4.** If another evidence record at Q1 or Q2 contradicts a source, that source's effective quality is capped at Q4 regardless of its original rank.

4. **CROSS_REFERENCE quality is bounded by its weakest input.** If a cross-reference combines a Q1 and a Q5 source, the cross-reference result is Q5 (the lower of the two inputs), unless the derivation operation is a CONSISTENCY_CHECK where both inputs agree, in which case it inherits the higher rank.

5. **Multiple Q5 sources do not become Q4.** Quantity does not upgrade quality rank. Three blog posts do not equal official documentation.

### 3.3 Quality in Evidence Records

Every evidence record MUST include:

```json
{
  "evidence_id": "ev_<source_type_abbrev>_<sequence>",
  "source_type": "<one of the 9 types>",
  "quality_rank": "Q1 | Q2 | Q3 | Q4 | Q5 | Q6",
  "quality_justification": "<why this rank was assigned>",
  "staleness": "FRESH | STALE | NOT_APPLICABLE",
  ...
}
```

---

## 4. EVIDENCE STRENGTH CLASSIFICATION

After all evidence has been gathered for a claim, SEE assigns an overall evidence strength. This is the final assessment that gets reported to MMD and recorded in the SOURCE_LEDGER.

### 4.1 Strength Levels

| Strength | Definition | Conditions |
|----------|------------|------------|
| CONFIRMED | Direct observation or computation proves the claim | At least one Q1 or Q2 evidence record directly supports the claim with no contradicting evidence |
| SUPPORTED | Multiple independent sources agree | Two or more evidence records from independent source types agree; highest quality is Q3 or above; no contradictions |
| PARTIAL | Some evidence exists but gaps remain | At least one evidence record exists but it does not fully address the claim, OR the claim is in SOURCE-LIMITED MODE and web evidence was needed but unavailable |
| CONTESTED | Sources disagree | Two or more evidence records contradict each other; conflict resolution (Section 5) has been applied but not fully resolved |
| UNSUPPORTED | No evidence found | All methods in the priority table were attempted (or were unavailable) and none returned relevant evidence |
| UNFALSIFIABLE | Claim cannot be tested with available methods | The claim requires a method that is unavailable (e.g., hash verification when hashing is disabled, comparative claim when web is unavailable) AND no fallback exists |

### 4.2 Strength Assignment Algorithm

```
function assign_strength(claim, evidence_records):
    if evidence_records is empty:
        if all_methods_attempted(claim):
            return UNSUPPORTED
        else if required_method_unavailable(claim):
            return UNFALSIFIABLE
        else:
            return UNSUPPORTED

    supporting = [e for e in evidence_records if e.supports(claim)]
    contradicting = [e for e in evidence_records if e.contradicts(claim)]

    if contradicting is not empty:
        apply_conflict_resolution(supporting, contradicting)  // Section 5
        if conflict_unresolved:
            return CONTESTED

    if any(e.quality_rank in [Q1, Q2] for e in supporting):
        return CONFIRMED

    if len(supporting) >= 2 and independent_sources(supporting):
        best_quality = min(e.quality_rank for e in supporting)  // lower number = higher quality
        if best_quality <= Q3:
            return SUPPORTED

    if len(supporting) >= 1:
        if claim.is_source_limited:
            return PARTIAL
        if supporting[0].quality_rank >= Q4:
            return PARTIAL
        return SUPPORTED

    return UNSUPPORTED
```

### 4.3 Strength in Claim Records

Every claim in the CLAIM_REGISTRY must be updated after SEE completes with:

```json
{
  "claim_id": "CLM_001",
  "claim_text": "...",
  "claim_type": "STRUCTURAL | NAMING | INTEGRITY | ...",
  "evidence_strength": "CONFIRMED | SUPPORTED | PARTIAL | CONTESTED | UNSUPPORTED | UNFALSIFIABLE",
  "evidence_ids": ["ev_local_fs_001", "ev_lfs_meta_003"],
  "source_limited": true | false,
  "methods_attempted": ["LOCAL_FS", "LFS_METADATA", "SCHEMA_VALIDATION"],
  "methods_unavailable": [],
  "see_notes": "optional free-text explanation"
}
```

---

## 5. CONFLICT RESOLUTION

When two or more evidence records for the same claim disagree, SEE must apply a deterministic conflict resolution process. Conflicts are not hidden. They are documented and, if unresolvable, escalated.

### 5.1 Resolution Priority Order

Conflicts are resolved by preferring the higher-priority evidence. Priority is determined by:

1. **DIRECT_OBSERVATION (Q1) over everything.** If you ran the command and saw the result, that takes precedence over any web source, prior artifact, or inference.

2. **COMPUTED_VERIFICATION (Q2) over web sources and inferences.** A hash computation is more reliable than a blog post claiming a different hash.

3. **More recent over older.** Between two evidence records of the same quality rank, prefer the one with the more recent `timestamp_utc`.

4. **AUTHORITATIVE_WEB_SOURCE (Q4) over COMMUNITY_WEB_SOURCE (Q5).** Official documentation beats Stack Overflow.

5. **PRIOR_ARTIFACT_REFERENCE (Q3) is time-sensitive.** A fresh prior artifact (< 30 days) beats a community web source. A stale prior artifact (> 30 days) does not.

### 5.2 Resolution Procedure

```
function resolve_conflict(claim, supporting, contradicting):
    // Step 1: Can direct observation settle it?
    direct = [e for e in (supporting + contradicting) if e.quality_rank == Q1]
    if len(direct) > 0:
        winner = most_recent(direct)
        mark_resolved(claim, winner, "DIRECT_OBSERVATION_OVERRIDE")
        return RESOLVED

    // Step 2: Can computed verification settle it?
    computed = [e for e in (supporting + contradicting) if e.quality_rank == Q2]
    if len(computed) > 0:
        winner = most_recent(computed)
        mark_resolved(claim, winner, "COMPUTED_VERIFICATION_OVERRIDE")
        return RESOLVED

    // Step 3: Recency tiebreak within same quality rank
    all_evidence = supporting + contradicting
    by_quality = group_by_quality(all_evidence)
    best_rank = min(by_quality.keys())
    candidates = by_quality[best_rank]
    if len(set(e.supports_claim for e in candidates)) == 1:
        // All best-quality evidence agrees
        mark_resolved(claim, candidates[0], "QUALITY_RANK_AGREEMENT")
        return RESOLVED

    // Step 4: Unresolvable -- escalate
    mark_contested(claim, supporting, contradicting)
    flag_in_source_ledger(claim, "UNRESOLVED_CONFLICT")
    return CONTESTED
```

### 5.3 Conflict Documentation

Every conflict MUST be recorded in the SOURCE_LEDGER with:

```json
{
  "conflict_id": "CONF_001",
  "claim_id": "CLM_042",
  "supporting_evidence_ids": ["ev_local_fs_012"],
  "contradicting_evidence_ids": ["ev_prior_art_007"],
  "resolution": "RESOLVED | CONTESTED",
  "resolution_method": "DIRECT_OBSERVATION_OVERRIDE | COMPUTED_VERIFICATION_OVERRIDE | QUALITY_RANK_AGREEMENT | RECENCY_TIEBREAK | UNRESOLVED_CONFLICT",
  "winner_evidence_id": "ev_local_fs_012 | null",
  "explanation": "Current filesystem observation shows 90 files; prior catalog listed 88. Filesystem is more recent and direct."
}
```

---

## 6. RECURSIVE SELF-IMPROVEMENT

SEE is not a static specification. It tracks its own performance and proposes improvements. This is the core innovation that separates SEE from a simple "do searches and log them" approach.

**Important constraint:** SEE proposes improvements. It does not self-modify. All changes to this specification require external admission via DeltaGate.

### 6a. Method Effectiveness Tracking

After each governance run, SEE evaluates which methods produced useful evidence and which wasted time or resources.

**Tracked metrics per method:**

| Metric | Definition |
|--------|------------|
| `invocations` | Number of times this method was called |
| `useful_results` | Number of invocations that produced evidence contributing to a CONFIRMED or SUPPORTED strength |
| `empty_results` | Number of invocations that returned no relevant evidence |
| `error_results` | Number of invocations that failed (timeout, permission error, tool unavailable) |
| `avg_time_ms` | Average wall-clock time per invocation (if measurable) |
| `effectiveness_ratio` | `useful_results / invocations` (0.0 to 1.0) |

**Output artifact:** `.codex/research/SEE_METHOD_EFFECTIVENESS.json`

**Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SEE Method Effectiveness Report",
  "type": "object",
  "required": ["see_engine_version", "run_timestamp_utc", "methods"],
  "properties": {
    "see_engine_version": { "type": "string", "const": "1.0" },
    "run_timestamp_utc": { "type": "string", "format": "date-time" },
    "total_claims_evaluated": { "type": "integer" },
    "total_evidence_records": { "type": "integer" },
    "methods": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["invocations", "useful_results", "empty_results", "error_results", "effectiveness_ratio"],
        "properties": {
          "invocations": { "type": "integer" },
          "useful_results": { "type": "integer" },
          "empty_results": { "type": "integer" },
          "error_results": { "type": "integer" },
          "avg_time_ms": { "type": ["number", "null"] },
          "effectiveness_ratio": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

**Example output:**
```json
{
  "see_engine_version": "1.0",
  "run_timestamp_utc": "2026-02-06T12:30:00Z",
  "total_claims_evaluated": 15,
  "total_evidence_records": 42,
  "methods": {
    "LOCAL_FS": {
      "invocations": 20,
      "useful_results": 19,
      "empty_results": 1,
      "error_results": 0,
      "avg_time_ms": 50,
      "effectiveness_ratio": 0.95
    },
    "WEB_SEARCH": {
      "invocations": 5,
      "useful_results": 2,
      "empty_results": 3,
      "error_results": 0,
      "avg_time_ms": 2000,
      "effectiveness_ratio": 0.40
    }
  },
  "recommendations": [
    "WEB_SEARCH effectiveness below 0.5 threshold; consider refining query patterns for ARCHITECTURAL claims",
    "HASH_VERIFICATION not invoked this run; 3 INTEGRITY claims were evaluated without it"
  ]
}
```

### 6b. Query Optimization

SEE tracks which search queries returned useful results and which returned noise. Over multiple runs, this builds a query pattern library.

**Tracked per query:**

| Field | Description |
|-------|-------------|
| `query_text` | The exact query string |
| `claim_type` | The claim type this query served |
| `source_type` | WEB_SEARCH or WEB_FETCH |
| `results_returned` | Number of results |
| `results_useful` | Number of results that contributed to evidence |
| `noise_ratio` | `1 - (results_useful / results_returned)` |
| `pattern_tag` | A category tag for the query pattern (e.g., "git_lfs_best_practice", "naming_convention_lookup") |

**Optimization rules:**

1. If a `pattern_tag` has a `noise_ratio > 0.8` across 3 or more runs, deprioritize queries matching that pattern. Deprioritization means: try other methods first; only use this pattern if all other methods yield insufficient evidence.

2. If a `pattern_tag` has an average `results_useful >= 3` across runs, promote queries matching that pattern. Promotion means: try this pattern earlier in the method sequence.

3. Query patterns are stored in `.codex/research/SEE_QUERY_PATTERNS.json` and accumulate across runs.

**Schema for query pattern entries:**
```json
{
  "pattern_tag": "string",
  "example_queries": ["string"],
  "total_uses": "integer",
  "total_useful_results": "integer",
  "total_noise_results": "integer",
  "avg_noise_ratio": "number (0.0-1.0)",
  "status": "ACTIVE | DEPRIORITIZED | PROMOTED",
  "last_used_utc": "string (ISO 8601)"
}
```

### 6c. Source Reliability Tracking

SEE maintains a reputation ledger for recurring sources (domains, documentation URLs, prior artifact paths). Over time, sources that consistently provide accurate information earn higher trust, while sources that are frequently contradicted or outdated lose trust.

**Tracked per source:**

| Field | Description |
|-------|-------------|
| `source_identifier` | URL domain, specific URL, or artifact path |
| `times_cited` | Total times this source was referenced |
| `times_corroborated` | Times this source's claims were later confirmed by higher-quality evidence |
| `times_contradicted` | Times this source's claims were contradicted by higher-quality evidence |
| `reliability_score` | `corroborated / (corroborated + contradicted)` (undefined if both are 0) |
| `last_cited_utc` | Most recent citation timestamp |

**Reliability thresholds:**

| Score Range | Label | Effect |
|-------------|-------|--------|
| 0.8 - 1.0 | HIGH_RELIABILITY | Source is preferred when multiple sources available |
| 0.5 - 0.79 | MODERATE_RELIABILITY | Source is used normally |
| 0.2 - 0.49 | LOW_RELIABILITY | Source is flagged in evidence record; additional corroboration required |
| 0.0 - 0.19 | UNRELIABLE | Source is excluded from evidence gathering; flagged in SOURCE_LEDGER |

**Output:** Source reliability data is stored within the SOURCE_LEDGER under a `source_reputation` section.

### 6d. Coverage Gap Detection

After evidence gathering is complete for all claims in a run, SEE performs a self-assessment to identify claim types or specific claims where evidence pipelines are weak.

**Gap detection checks:**

1. **Method coverage:** For each claim type, are all priority methods in Section 2.2 available? If not, which are missing?

2. **Strength distribution:** What fraction of claims reached CONFIRMED vs. SUPPORTED vs. PARTIAL vs. worse? If more than 30% of claims are PARTIAL or below, the evidence pipeline has a gap.

3. **Source type utilization:** Were any source types never used? If HASH_VERIFICATION was never invoked but INTEGRITY claims exist, that is a gap.

4. **Unfalsifiable claims:** Any claim marked UNFALSIFIABLE represents a systemic gap. SEE should identify what capability would be needed to make it falsifiable.

5. **Repeated UNSUPPORTED patterns:** If the same claim type is UNSUPPORTED across multiple runs, the method priority table for that claim type may need revision.

**Output:** Coverage gaps are appended to `SEE_METHOD_EFFECTIVENESS.json` under a `coverage_gaps` section:

```json
{
  "coverage_gaps": [
    {
      "gap_id": "GAP_001",
      "description": "INTEGRITY claims lack HASH_VERIFICATION because real_hashing_available=false",
      "affected_claims": ["CLM_010", "CLM_011"],
      "proposed_remedy": "Enable sha256sum in execution environment",
      "severity": "HIGH | MEDIUM | LOW"
    }
  ]
}
```

### 6e. Engine Version Bumping

When SEE identifies improvements through 6a-6d, it packages them into a formal improvement proposal. This proposal is NOT self-executing. It requires external admission.

**Proposal triggers:**

1. A method's `effectiveness_ratio` drops below 0.3 for 3 consecutive runs
2. A new source type is identified that would fill a coverage gap
3. A method priority order change would better serve a claim type (based on effectiveness data)
4. A new claim type is encountered that does not fit the existing taxonomy
5. The conflict resolution procedure produces CONTESTED outcomes on more than 20% of conflicted claims

**Output artifact:** `.codex/research/SEE_IMPROVEMENT_PROPOSAL.json`

**Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SEE Improvement Proposal",
  "type": "object",
  "required": ["proposal_id", "see_engine_version", "proposed_version", "created_utc", "proposals"],
  "properties": {
    "proposal_id": {
      "type": "string",
      "description": "Unique identifier: SEE_IMP_<YYYYMMDD>_<NNN>"
    },
    "see_engine_version": {
      "type": "string",
      "description": "Current engine version this proposal applies to"
    },
    "proposed_version": {
      "type": "string",
      "description": "Version number if all proposals are accepted (e.g., 1.1)"
    },
    "created_utc": {
      "type": "string",
      "format": "date-time"
    },
    "triggering_data": {
      "type": "object",
      "description": "Summary of effectiveness data, gap analysis, and conflict stats that triggered this proposal"
    },
    "proposals": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["proposal_type", "description", "rationale", "risk"],
        "properties": {
          "proposal_type": {
            "type": "string",
            "enum": [
              "ADD_SOURCE_TYPE",
              "REMOVE_SOURCE_TYPE",
              "REORDER_METHOD_PRIORITY",
              "ADD_CLAIM_TYPE",
              "MODIFY_QUALITY_RANK",
              "MODIFY_STRENGTH_THRESHOLD",
              "MODIFY_CONFLICT_RESOLUTION",
              "ADD_QUERY_PATTERN",
              "DEPRECATE_QUERY_PATTERN",
              "MODIFY_STALENESS_THRESHOLD",
              "OTHER"
            ]
          },
          "description": { "type": "string" },
          "rationale": { "type": "string" },
          "risk": { "type": "string" },
          "affected_sections": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Which sections of this spec would change"
          }
        }
      }
    },
    "status": {
      "type": "string",
      "enum": ["PROPOSED", "ADMITTED", "REJECTED"],
      "default": "PROPOSED"
    }
  }
}
```

**Version bump rules:**
- Patch (1.0 -> 1.0.1): Query pattern changes, staleness threshold adjustments
- Minor (1.0 -> 1.1): Method priority reordering, new query patterns, quality rank adjustments
- Major (1.0 -> 2.0): New source types, new claim types, fundamental changes to conflict resolution or strength assignment

---

## 7. OUTPUT ARTIFACTS

SEE produces four primary artifacts per run. All are written to `.codex/research/`. All must be valid JSON. All must include the `see_engine_version` field.

### 7.1 SEE_QUERY_LOG.json

**Purpose:** Complete record of every search, check, read, hash, or computation performed by SEE during the run.

**Path:** `.codex/research/SEE_QUERY_LOG.json`

**Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SEE Query Log",
  "type": "object",
  "required": ["see_engine_version", "run_timestamp_utc", "queries"],
  "properties": {
    "see_engine_version": { "type": "string" },
    "run_timestamp_utc": { "type": "string", "format": "date-time" },
    "mode": {
      "type": "string",
      "enum": ["FULL", "SOURCE-LIMITED"],
      "description": "Whether web access was available"
    },
    "total_queries": { "type": "integer" },
    "queries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["query_id", "source_type", "operation", "timestamp_utc", "result_useful"],
        "properties": {
          "query_id": {
            "type": "string",
            "description": "Unique query identifier: Q_<NNN>"
          },
          "claim_id": {
            "type": "string",
            "description": "The claim this query serves"
          },
          "source_type": {
            "type": "string",
            "enum": ["LOCAL_FS", "GIT_HISTORY", "LFS_METADATA", "SCHEMA_VALIDATION", "HASH_VERIFICATION", "WEB_SEARCH", "WEB_FETCH", "PRIOR_ARTIFACTS", "CROSS_REFERENCE", "BUNDLE_INTERNAL_EVENTS", "BUNDLE_AUDIT_RECEIPTS"]
          },
          "operation": {
            "type": "string",
            "description": "The command, query, or operation performed"
          },
          "result_summary": {
            "type": "string",
            "description": "Brief summary of what was returned"
          },
          "result_useful": {
            "type": "boolean",
            "description": "Whether this query contributed to evidence"
          },
          "evidence_id": {
            "type": ["string", "null"],
            "description": "The evidence record ID produced, if any"
          },
          "duration_ms": {
            "type": ["integer", "null"],
            "description": "Execution time if measurable"
          },
          "timestamp_utc": {
            "type": "string",
            "format": "date-time"
          },
          "error": {
            "type": ["string", "null"],
            "description": "Error message if the query failed"
          }
        }
      }
    }
  }
}
```

### 7.2 SOURCE_LEDGER.json

**Purpose:** Every evidence record evaluated during the run, with quality ranking, strength contribution, and conflict documentation. This is the authoritative record of what SEE found.

**Path:** `.codex/research/SOURCE_LEDGER.json`

**Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SEE Source Ledger",
  "type": "object",
  "required": ["see_engine_version", "run_timestamp_utc", "evidence_records", "claim_evidence_map"],
  "properties": {
    "see_engine_version": { "type": "string" },
    "run_timestamp_utc": { "type": "string", "format": "date-time" },
    "mode": {
      "type": "string",
      "enum": ["FULL", "SOURCE-LIMITED"]
    },
    "evidence_records": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["evidence_id", "source_type", "quality_rank", "operation", "result", "timestamp_utc"],
        "properties": {
          "evidence_id": { "type": "string" },
          "source_type": { "type": "string" },
          "quality_rank": {
            "type": "string",
            "enum": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
          },
          "quality_justification": { "type": "string" },
          "staleness": {
            "type": "string",
            "enum": ["FRESH", "STALE", "NOT_APPLICABLE"]
          },
          "operation": { "type": "string" },
          "result": { "type": "string" },
          "supports_claim": { "type": "boolean" },
          "contradicts_claim": { "type": "boolean" },
          "timestamp_utc": { "type": "string", "format": "date-time" },
          "notes": { "type": ["string", "null"] }
        }
      }
    },
    "claim_evidence_map": {
      "type": "object",
      "description": "Maps claim_id to evidence summary",
      "additionalProperties": {
        "type": "object",
        "required": ["evidence_ids", "evidence_strength", "methods_attempted"],
        "properties": {
          "evidence_ids": {
            "type": "array",
            "items": { "type": "string" }
          },
          "evidence_strength": {
            "type": "string",
            "enum": ["CONFIRMED", "SUPPORTED", "PARTIAL", "CONTESTED", "UNSUPPORTED", "UNFALSIFIABLE"]
          },
          "methods_attempted": {
            "type": "array",
            "items": { "type": "string" }
          },
          "methods_unavailable": {
            "type": "array",
            "items": { "type": "string" }
          },
          "source_limited": { "type": "boolean" }
        }
      }
    },
    "conflicts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["conflict_id", "claim_id", "resolution"],
        "properties": {
          "conflict_id": { "type": "string" },
          "claim_id": { "type": "string" },
          "supporting_evidence_ids": {
            "type": "array",
            "items": { "type": "string" }
          },
          "contradicting_evidence_ids": {
            "type": "array",
            "items": { "type": "string" }
          },
          "resolution": {
            "type": "string",
            "enum": ["RESOLVED", "CONTESTED"]
          },
          "resolution_method": { "type": "string" },
          "winner_evidence_id": { "type": ["string", "null"] },
          "explanation": { "type": "string" }
        }
      }
    },
    "source_reputation": {
      "type": "array",
      "description": "Accumulated source reliability data (Section 6c)",
      "items": {
        "type": "object",
        "required": ["source_identifier", "times_cited", "reliability_score"],
        "properties": {
          "source_identifier": { "type": "string" },
          "times_cited": { "type": "integer" },
          "times_corroborated": { "type": "integer" },
          "times_contradicted": { "type": "integer" },
          "reliability_score": { "type": ["number", "null"] },
          "reliability_label": {
            "type": "string",
            "enum": ["HIGH_RELIABILITY", "MODERATE_RELIABILITY", "LOW_RELIABILITY", "UNRELIABLE", "INSUFFICIENT_DATA"]
          },
          "last_cited_utc": { "type": "string", "format": "date-time" }
        }
      }
    }
  }
}
```

### 7.3 SEE_METHOD_EFFECTIVENESS.json

**Purpose:** Post-run evaluation of method performance, coverage gaps, and recommendations. This artifact feeds into the self-improvement loop (Section 6).

**Path:** `.codex/research/SEE_METHOD_EFFECTIVENESS.json`

**Schema:** See Section 6a for the full schema. Additional fields for coverage gaps are defined in Section 6d.

### 7.4 SEE_IMPROVEMENT_PROPOSAL.json

**Purpose:** Formal proposals for changes to the SEE Engine specification, generated when effectiveness tracking or gap detection identifies opportunities for improvement.

**Path:** `.codex/research/SEE_IMPROVEMENT_PROPOSAL.json`

**Schema:** See Section 6e for the full schema.

**Emission rule:** This artifact is OPTIONAL. It is only emitted when at least one proposal trigger condition (Section 6e) is met. If no triggers are met, the file is not emitted and its absence is not a failure.

### 7.5 SEE_QUERY_PATTERNS.json (Accumulated)

**Purpose:** Accumulated query pattern library across runs (Section 6b). Unlike other artifacts which are per-run, this file accumulates across runs.

**Path:** `.codex/research/SEE_QUERY_PATTERNS.json`

**Behavior:** If the file exists from a prior run, SEE reads it, updates it with current run data, and writes it back. If it does not exist, SEE creates it.

---

## 8. INTEGRATION WITH MMD (Missing Middle Detector)

SEE and MMD operate in adjacent phases (Phase 1 and Phase 2 respectively). SEE produces evidence; MMD detects gaps. The integration is one-directional: SEE feeds MMD. MMD does not modify SEE artifacts.

### 8.1 Evidence Strength Signals to MMD

MMD MUST consume the `claim_evidence_map` from SOURCE_LEDGER.json and flag the following conditions:

| SEE Signal | MMD Action |
|------------|------------|
| `evidence_strength = UNSUPPORTED` | MMD flags the claim as a MISSING INPUT. The claim was made but no evidence backs it. |
| `evidence_strength = UNFALSIFIABLE` | MMD flags a HIDDEN DEPENDENCY on an unavailable capability (e.g., hash tool, web access). |
| `evidence_strength = CONTESTED` | MMD flags an UNRESOLVED CONFLICT requiring external adjudication. |
| `evidence_strength = PARTIAL` with `source_limited = true` | MMD flags a SOURCE LIMITATION. The claim might be valid but cannot be fully evaluated in current environment. |

### 8.2 Method Failure Signals to MMD

MMD MUST consume `SEE_METHOD_EFFECTIVENESS.json` and flag:

| SEE Signal | MMD Action |
|------------|------------|
| `effectiveness_ratio < 0.3` for any method | MMD flags a METHOD GAP: "Method X is ineffective for this repository; evidence pipeline is degraded." |
| `error_results > 0` for any method | MMD flags an ENVIRONMENT ISSUE: "Method X encountered errors; execution environment may be misconfigured." |
| Coverage gap with `severity = HIGH` | MMD flags a CRITICAL COVERAGE GAP and may trigger FAIL CLOSED if the gap affects INTEGRITY claims. |

### 8.3 Source Reliability Signals to MMD

MMD MUST consume the `source_reputation` section of SOURCE_LEDGER.json and flag:

| SEE Signal | MMD Action |
|------------|------------|
| Any source with `reliability_label = UNRELIABLE` that was cited in this run | MMD flags a SOURCE DEPENDENCY WARNING: "Evidence depends on a source with poor track record." |
| Any source with `reliability_label = LOW_RELIABILITY` providing the ONLY evidence for a claim | MMD flags a WEAK EVIDENCE WARNING: "Claim X relies solely on a low-reliability source." |

### 8.4 Data Flow Diagram

```
Phase 0: CLAIM_REGISTRY.json
    |
    v
Phase 1: SEE Engine
    |-- reads claims from CLAIM_REGISTRY
    |-- executes method priority tables per claim type
    |-- writes: SEE_QUERY_LOG.json
    |-- writes: SOURCE_LEDGER.json
    |-- writes: SEE_METHOD_EFFECTIVENESS.json
    |-- writes: SEE_IMPROVEMENT_PROPOSAL.json (if triggered)
    |-- updates: SEE_QUERY_PATTERNS.json (accumulated)
    |
    v
Phase 2: MMD
    |-- reads: SOURCE_LEDGER.json (claim_evidence_map, conflicts, source_reputation)
    |-- reads: SEE_METHOD_EFFECTIVENESS.json (method stats, coverage_gaps)
    |-- detects: MISSING INPUTS, HIDDEN DEPENDENCIES, UNRESOLVED CONFLICTS
    |-- detects: METHOD GAPS, ENVIRONMENT ISSUES, SOURCE DEPENDENCY WARNINGS
    |-- writes: MMD_REPORT.json
    |
    v
Phase 3+: BUILD, EVALUATE, REWRITE, SELF-VERIFY, TURN RECEIPT
```

---

## 9. OPERATIONAL CONSTRAINTS

### 9.1 Performance Bounds

SEE should not spend unbounded time gathering evidence. The following soft limits apply:

| Constraint | Limit | Action on Breach |
|------------|-------|------------------|
| Max queries per claim | 10 | Stop gathering, use what you have |
| Max total queries per run | 200 | Stop gathering, use what you have |
| Max web searches per run | 20 | Enter SOURCE-LIMITED MODE for remaining web-dependent claims |
| Max time per method invocation | 30 seconds | Record as timeout error, try next method |

These limits are soft: they may be exceeded if the agent determines it is necessary, but the overage must be documented in SEE_QUERY_LOG with a justification.

### 9.2 NON_CLAIM Passthrough

Claims classified as `NON_CLAIM` in Phase 0 (procedural instructions, trivially observable filesystem facts) pass through SEE without evidence gathering. They are recorded in the SOURCE_LEDGER with:

```json
{
  "evidence_id": "ev_passthrough_001",
  "source_type": "LOCAL_FS",
  "quality_rank": "Q1",
  "operation": "NON_CLAIM passthrough: file existence is directly observable",
  "result": "claim classified as NON_CLAIM per Phase 0",
  "evidence_strength": "CONFIRMED"
}
```

### 9.3 Forbidden Behaviors

SEE MUST NOT:

1. **Fabricate evidence.** If no evidence exists, report UNSUPPORTED. Do not invent sources or results.
2. **Upgrade evidence quality.** Three Q5 sources do not become Q4. Follow the ranking rules exactly.
3. **Skip logging.** Every query, even failed ones, must appear in SEE_QUERY_LOG.
4. **Self-admit improvements.** SEE proposes; external authority admits. SEE does not modify its own specification.
5. **Use forbidden language** (as defined in SUPER_PROMPT) in any emitted artifact.
6. **Assume web access.** Always check ENVIRONMENT_DECLARATION. If web_access is not confirmed YES, do not attempt web queries.

---

## 10. IMPLEMENTATION CHECKLIST

For an execution agent implementing SEE Engine v1.0:

- [ ] Read ENVIRONMENT_DECLARATION.json to determine available capabilities
- [ ] For each claim from CLAIM_REGISTRY.json:
  - [ ] Determine claim type (Section 2.1)
  - [ ] Execute method priority table (Section 2.2) in order
  - [ ] Record every query in SEE_QUERY_LOG (Section 7.1)
  - [ ] Record every evidence record in SOURCE_LEDGER (Section 7.2)
  - [ ] Assign quality rank to each evidence record (Section 3)
  - [ ] Resolve any conflicts (Section 5)
  - [ ] Assign evidence strength (Section 4)
- [ ] After all claims processed:
  - [ ] Compute method effectiveness metrics (Section 6a)
  - [ ] Update query patterns if applicable (Section 6b)
  - [ ] Update source reliability data (Section 6c)
  - [ ] Run coverage gap detection (Section 6d)
  - [ ] Emit SEE_IMPROVEMENT_PROPOSAL if triggers met (Section 6e)
- [ ] Write all output artifacts (Section 7)
- [ ] Hand off to MMD (Section 8)

---

## APPENDIX A: Evidence ID Format

All evidence IDs follow the pattern: `ev_<source_type_abbreviation>_<three_digit_sequence>`

| Source Type | Abbreviation |
|-------------|-------------|
| LOCAL_FS | `local_fs` |
| GIT_HISTORY | `git_hist` |
| LFS_METADATA | `lfs_meta` |
| SCHEMA_VALIDATION | `schema_val` |
| HASH_VERIFICATION | `hash_ver` |
| WEB_SEARCH | `web_search` |
| WEB_FETCH | `web_fetch` |
| PRIOR_ARTIFACTS | `prior_art` |
| CROSS_REFERENCE | `cross_ref` |
| BUNDLE_INTERNAL_EVENTS | `bndl_evt` |
| BUNDLE_AUDIT_RECEIPTS | `bndl_rcpt` |

Examples: `ev_local_fs_001`, `ev_hash_ver_012`, `ev_cross_ref_003`, `ev_bndl_evt_001`

## APPENDIX B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-06 | Initial specification. Replaces informal SEE definition in BOOT.md. |
| 1.0.1 | 2026-02-07 | Added Section 1.11 BUNDLE_AUDIT_RECEIPTS (11th source type). Fixed Appendix A abbreviations for source types 10-11. |

---

*This specification is PROPOSED. It requires external admission via DeltaGate before it becomes binding on execution agents. Until admitted, agents SHOULD follow this specification but are not in violation if they follow the prior informal SEE definition.*
