# MBQL v1 — MetaBlooms Query Language

## Rationale (CDR Pillar 1)

**Problem:** The governance system produces structured artifacts (BUNDLE_CATALOG.json,
BUNDLE_LINEAGE.json, LEARNING_EVENTS.ndjson, MMD_REPORT.json, INVARIANT_REGISTRY.json)
but there is no standard way to query them. Every consumer writes ad-hoc jq/grep commands,
which are not auditable, not composable, and not accessible to non-technical operators.

**Chosen solution:** A minimal query language (MBQL) with a natural-language translation
layer. Operators ask questions in English; the NLQ translator converts to MBQL; the
executor runs the query; results are returned in a standard envelope.

**Rejected alternative:** Raw jq pipelines. Rejected because they are opaque, fragile
when schema changes, and inaccessible to non-technical operators.

**Rejected alternative:** Full SQL engine over JSON. Rejected because it requires a
database runtime and is over-engineered for <100 files and <1000 events.

---

## 1. CORE CONCEPTS

### 1.1 Data Sources

MBQL operates over these data sources:

| Source ID | File | Record Type |
|-----------|------|-------------|
| `bundles` | `.codex/artifacts/BUNDLE_CATALOG.json` | Bundle entry per BUNDLE_ENTRY.schema.json |
| `lineage` | `.codex/artifacts/BUNDLE_LINEAGE.json` | Chain and orphan records per BUNDLE_LINEAGE.schema.json |
| `events` | `events/LEARNING_EVENTS.ndjson` (inside bundles) | Learning event per LEARNING_EVENT.schema.json |
| `mmd` | `.codex/artifacts/MMD_REPORT.json` | MMD finding per MMD_REPORT.schema.json |
| `invariants` | `.codex/artifacts/INVARIANT_REGISTRY.json` | Invariant record per INVARIANT_REGISTRY schema |
| `receipts` | `.codex/receipts/*.json` | Receipt records |

### 1.2 Query Structure

Every MBQL query has this shape:

```
FROM <source>
WHERE <predicate>+
SELECT <field>+
[ORDER BY <field> ASC|DESC]
[LIMIT <n>]
```

- **FROM**: exactly one source ID
- **WHERE**: one or more predicates joined by AND/OR
- **SELECT**: fields to return (or `*` for all)
- **ORDER BY**: optional sort
- **LIMIT**: optional result cap

### 1.3 Predicates

| Operator | Meaning | Example |
|----------|---------|---------|
| `=` | Exact match | `category = "os_bundle"` |
| `!=` | Not equal | `lifecycle_status != "ACTIVE"` |
| `LIKE` | Substring/pattern match | `filename LIKE "PATCHED"` |
| `IN` | Set membership | `category IN ["driver", "utility"]` |
| `>`, `<`, `>=`, `<=` | Numeric/temporal comparison | `size_bytes > 100000000` |
| `IS NULL` | Field is null/missing | `superseded_by IS NULL` |
| `IS NOT NULL` | Field has a value | `date_prefix IS NOT NULL` |
| `HAS` | Array contains value | `version_qualifiers HAS "LTS"` |
| `COUNT` | Aggregate count | Used in SELECT |

### 1.4 Aggregations

| Function | Meaning |
|----------|---------|
| `COUNT(*)` | Count matching records |
| `COUNT(DISTINCT field)` | Count unique values |
| `SUM(field)` | Sum numeric field |
| `GROUP BY field` | Group results |

---

## 2. NLQ TRANSLATOR PIPELINE

The NLQ (Natural Language Query) translator converts English questions into MBQL.

### 2.1 Pipeline Stages

```
1. NLQ Input (English question)
   ↓
2. Intent Classification
   ↓  → Produces INTENT_IR (intermediate representation)
3. MBQL Generation
   ↓  → Produces executable MBQL query
4. Query Execution
   ↓  → Runs against data source
5. Result Formatting
   ↓  → Returns human-readable answer
```

### 2.2 Intent Classification

The translator classifies the user's question into one of these intent types:

| Intent | Description | Example NLQ |
|--------|-------------|-------------|
| `INVENTORY` | Count or list bundles | "How many OS bundles are there?" |
| `LOOKUP` | Find specific bundle(s) | "Show me all PATCHED bundles" |
| `LINEAGE` | Trace evolution chain | "What did this bundle replace?" |
| `STATUS` | Check lifecycle state | "Which bundles are superseded?" |
| `INTEGRITY` | Verify hash/LFS/schema | "Are all files LFS tracked?" |
| `TEMPORAL` | Time-based query | "What was added after Jan 28?" |
| `AGGREGATE` | Statistical summary | "Total size by category?" |
| `GAP` | Find missing/broken things | "Any bundles without lineage?" |
| `INVARIANT` | Check system invariant | "Does invariant X hold?" |

### 2.3 INTENT_IR (Intermediate Representation)

Between NLQ and MBQL, the translator produces a structured INTENT_IR:

```json
{
  "nlq": "How many OS bundles have the PATCHED qualifier?",
  "intent": "AGGREGATE",
  "source": "bundles",
  "filters": [
    {"field": "category", "op": "=", "value": "os_bundle"},
    {"field": "version_qualifiers", "op": "HAS", "value": "PATCHED"}
  ],
  "projection": ["COUNT(*)"],
  "confidence": 0.95
}
```

The INTENT_IR is an auditable intermediate step. If the translator misclassifies,
the INTENT_IR shows exactly where interpretation diverged from intent.

Schema: `.codex/schemas/INTENT_IR.schema.json`

### 2.4 Translation Rules

| NLQ Pattern | Intent | MBQL Template |
|-------------|--------|---------------|
| "how many" / "count" | AGGREGATE | `SELECT COUNT(*) FROM <source> WHERE ...` |
| "list" / "show" / "which" | LOOKUP | `SELECT * FROM <source> WHERE ...` |
| "what replaced" / "what came after" | LINEAGE | `FROM lineage WHERE ...` |
| "is X tracked" / "are all" | INTEGRITY | `FROM bundles WHERE ... SELECT lfs_tracked` |
| "total size" / "sum" | AGGREGATE | `SELECT SUM(size_bytes) FROM ...` |
| "superseded" / "deprecated" / "frozen" | STATUS | `FROM bundles WHERE lifecycle_status = ...` |
| "missing" / "gap" / "orphan" | GAP | Source-dependent |
| "does invariant" / "check invariant" | INVARIANT | Dispatch to invariant evaluator |

### 2.5 Confidence Scoring

The translator assigns a confidence score (0.0–1.0) to each INTENT_IR:

| Score Range | Action |
|-------------|--------|
| 0.85–1.0 | Execute automatically |
| 0.60–0.84 | Execute with disclaimer: "I interpreted this as..." |
| 0.0–0.59 | Do not execute. Ask for clarification. |

---

## 3. QUERY EXECUTION

### 3.1 Executor Behavior

The executor reads the target data source, applies WHERE predicates, projects
SELECT fields, applies ORDER BY and LIMIT, and returns a result envelope.

### 3.2 Result Envelope

```json
{
  "query": "<original MBQL>",
  "source": "<source ID>",
  "intent_ir": { ... },
  "results": [ ... ],
  "count": 7,
  "executed_utc": "2026-02-07T00:00:00Z",
  "notes": "Optional executor notes"
}
```

### 3.3 Error Handling

| Error | Behavior |
|-------|----------|
| Source file not found | Return error envelope with `"error": "SOURCE_NOT_FOUND"` |
| Invalid MBQL syntax | Return error with `"error": "SYNTAX_ERROR"` and the offending clause |
| Field not in schema | Return error with `"error": "UNKNOWN_FIELD"` |
| Empty result set | Return empty results array (not an error) |

---

## 4. EXAMPLE QUERIES

### 4.1 Inventory

**NLQ:** "How many files are in each category?"

**MBQL:**
```
FROM bundles
SELECT category, COUNT(*)
GROUP BY category
```

### 4.2 Lookup with Filter

**NLQ:** "Show me all bundles with the LTS qualifier"

**MBQL:**
```
FROM bundles
WHERE version_qualifiers HAS "LTS"
SELECT filename, lifecycle_status, version_qualifiers
```

### 4.3 Lineage Trace

**NLQ:** "What is the evolution chain for the PASS3 bundles?"

**MBQL:**
```
FROM lineage
WHERE chain_id LIKE "PASS3"
SELECT *
```

### 4.4 Gap Detection

**NLQ:** "Which OS bundles have no lineage chain?"

**MBQL:**
```
FROM lineage
WHERE orphans HAS filename
  AND category = "os_bundle"
SELECT filename
```

### 4.5 Invariant Check

**NLQ:** "Does the NLQ-required invariant hold?"

Dispatches to invariant evaluator for `MB_INV_NLQ_REQUIRED_V1`.

### 4.6 Learning Events

**NLQ:** "What corrective actions have been ratified?"

**MBQL:**
```
FROM events
WHERE event_type = "EVT_LEARNING_CORRECTIVE_ACTION_RATIFIED"
SELECT event_id, payload.corrective_action, timestamp_utc
ORDER BY timestamp_utc DESC
```

---

## 5. INVARIANT EVALUATION

MBQL supports invariant checking as a first-class operation. Invariants are
registered in `.codex/artifacts/INVARIANT_REGISTRY.json` and evaluated on demand.

### 5.1 Invariant Query Syntax

```
CHECK INVARIANT <invariant_id>
```

This is syntactic sugar that dispatches to the invariant evaluator, which:
1. Loads the invariant definition from the registry
2. Translates the invariant's `mbql_check` into an executable query
3. Evaluates the query against the specified data source
4. Compares the result against the invariant's `expected_result`
5. Returns PASS or FAIL with evidence

### 5.2 Invariant Result

```json
{
  "invariant_id": "MB_INV_NLQ_REQUIRED_V1",
  "status": "PASS",
  "evidence": { ... },
  "checked_utc": "2026-02-07T00:00:00Z"
}
```

---

## 6. INTEGRATION WITH GOVERNANCE SYSTEM

### 6.1 SEE Integration

MBQL query results are valid SEE evidence. When a claim can be resolved by
querying structured artifacts, SEE should use MBQL rather than ad-hoc inspection.

Evidence source type: `PRIOR_ARTIFACTS` (for catalog/lineage queries) or
`BUNDLE_INTERNAL_EVENTS` (for learning event queries).

### 6.2 MMD Integration

MMD should use MBQL queries to detect gaps systematically rather than
one-off inspection. Example MMD checks expressible as MBQL:

- `FROM bundles WHERE lfs_tracked = false SELECT filename` → LFS gap detection
- `FROM bundles WHERE lifecycle_status = "ORPHANED" SELECT filename` → Orphan detection
- `FROM lineage WHERE orphans.category = "os_bundle" SELECT filename` → Lineage gap

### 6.3 Invariant Integration

Invariants registered in the INVARIANT_REGISTRY can reference MBQL queries
as their verification method. This creates a closed loop:

```
Invariant defined → MBQL check specified → Query runs → Result proves compliance
```

---

## 7. FAILURE MODES (CDR Pillar 4)

| Failure Mode | Safe State | Recovery |
|---|---|---|
| NLQ translator misclassifies intent | Wrong query executed, wrong results | INTENT_IR is auditable — review classification |
| Data source schema changes | MBQL field references break | UNKNOWN_FIELD error returned; update query |
| Data source file missing | Query cannot execute | SOURCE_NOT_FOUND error; regenerate artifact |
| Invariant registry corrupted | Invariant checks return errors | Re-validate registry against schema |
| Confidence score too low | Query not executed | Ask operator for clarification |

---

## 8. CONSTRAINTS (CDR Pillar 2)

1. MBQL is read-only. It cannot modify any data source.
2. MBQL queries execute against local files only — no network access.
3. NLQ translation is best-effort. Confidence below 0.60 halts execution.
4. MBQL does not support JOINs across data sources in v1.
5. Aggregations operate on in-memory data — no streaming for v1.
6. All queries are synchronous and single-threaded.

---

## APPENDIX A: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-07 | Initial specification. NLQ translator, INTENT_IR, invariant evaluation. |

---

*CDR Attestation: This document was constructed justification-first per CDR v2.0.
Pillar 1 (rationale) in Section 0. Pillar 2 (constraints) in Section 8.
Pillar 4 (failure modes) in Section 7. Pillar 5 (integration) in Section 6.
Pillar 6 (history) in Appendix A. Pillar 7 (attestation) is this paragraph.*
