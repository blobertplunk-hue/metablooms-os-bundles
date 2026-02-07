# Learning Pipeline v1 — Evidence-Driven Structural Change

## Rationale (CDR Pillar 1)

**Problem:** AI systems claim to "learn" through memory, context, or
prompt tuning. None of these produce auditable structural change. When
something fails, there's no guarantee the failure is investigated, no
guarantee the investigation produces a fix, and no guarantee the fix
is recorded as evidence.

**Chosen solution:** A deterministic pipeline where failures force
investigation, investigation forces structural change, and structural
change emits queryable events. Learning is not memory — it is
behavioral change backed by evidence.

**Rejected alternative:** Memory-based learning (storing lessons in
prose). Rejected because prose is not queryable, not verifiable, and
degrades over time. Events are structured data that can prove what
changed, when, why, and whether it recurred.

## Core Axiom

> Learning is not remembering. Learning is structural change to system
> behavior, triggered by evidence, recorded as events, and queryable
> after the fact.

If you can't query "what did the system learn and when did behavior
change," it didn't learn.

## The Learning Loop

```
1. FAILURE occurs
   ↓
2. FAILURE EVENT emitted (EVT_FAIL_*)
   ↓
3. RCA auto-triggers (no human intervention required)
   ↓
4. ROOT CAUSE identified
   ↓
5. CORRECTIVE ACTION applied (structural fix / guard / invariant)
   ↓
6. LEARNING EVENTS emitted (EVT_LEARNING_*)
   ↓
7. Future queries can prove:
   - what failed
   - why it failed
   - how behavior changed
   - that it won't recur
```

Every step produces an artifact. No step is optional. If a step
cannot complete, the pipeline halts with a receipt explaining why.

## Event Types

### Failure Events

| Event ID                         | Trigger                              |
|----------------------------------|--------------------------------------|
| `EVT_FAIL_EXTRACTION`           | OS bundle extraction failed           |
| `EVT_FAIL_WRITE_PERMISSION`     | Write to target path denied           |
| `EVT_FAIL_HASH_MISMATCH`        | SHA-256 verification failed           |
| `EVT_FAIL_SCHEMA_VIOLATION`     | Artifact doesn't match its schema     |
| `EVT_FAIL_MISSING_DEPENDENCY`   | Required file or tool not found       |
| `EVT_FAIL_RCA_INCONCLUSIVE`     | RCA ran but could not identify cause  |
| `EVT_FAIL_GOVERNANCE_VIOLATION` | Forbidden language, missing receipt, etc. |

### Learning Events

| Event ID                              | Meaning                                    |
|---------------------------------------|--------------------------------------------|
| `EVT_LEARNING_ROOT_CAUSE_IDENTIFIED` | RCA completed, root cause is known          |
| `EVT_LEARNING_CORRECTIVE_ACTION_RATIFIED` | Structural fix has been applied        |
| `EVT_LEARNING_GUARD_INSTALLED`       | A pre-condition guard now prevents recurrence |
| `EVT_LEARNING_INVARIANT_ADDED`       | A new system invariant was established      |
| `EVT_LEARNING_METHOD_DEPRIORITIZED`  | SEE learned a method is ineffective         |
| `EVT_LEARNING_SOURCE_DEMOTED`        | SEE learned a source is unreliable          |

## Internal Bundle Architecture

OS bundles are not opaque blobs. They contain internal structure:

```
Metablooms_OS/
├── tools/
│   ├── audit/
│   │   ├── fs_root_guard.py        # Pre-extraction enforcement
│   │   └── rca_auto_trigger.py     # Auto-trigger RCA on failure
│   └── rca/
│       ├── run_rca.py              # Root cause analysis engine
│       └── emit_learning_from_rca.py # Learning event emitter
├── events/
│   └── LEARNING_EVENTS.ndjson      # Structured learning event log
├── audit/
│   └── LEARNING_PIPELINE_RECEIPT.json # Proof of pipeline execution
└── ... (OS content)
```

### Key Components

**FS Root Guard** (`tools/audit/fs_root_guard.py`)
- Blocks OS extraction unless a writable root is verified
- Emits `FS_ROOT_RECEIPT.json` before extraction proceeds
- This is a corrective action from a prior RCA — the guard exists
  because extraction once failed silently without checking write access

**RCA Auto-Trigger** (`tools/audit/rca_auto_trigger.py`)
- Monitors for `EVT_FAIL_*` events
- Automatically invokes `tools/rca/run_rca.py`
- No human intervention required — failures force investigation

**Learning Event Emitter** (`tools/rca/emit_learning_from_rca.py`)
- Reads `RCA_REPORT.json`
- Emits structured learning events to `events/LEARNING_EVENTS.ndjson`
- Events are typed, timestamped, and reference the RCA that produced them

**Learning Events Log** (`events/LEARNING_EVENTS.ndjson`)
- Newline-delimited JSON
- Each line is a single event with `event_id`, `timestamp`, `source_rca`,
  and `payload`
- Queryable: `events WHERE event_id LIKE EVT_LEARNING_%`

## Integration with Governance System

### SEE Integration
The SEE Engine must recognize learning events as an evidence source:

| Source Type              | Quality Rank          | When to Use                    |
|--------------------------|-----------------------|--------------------------------|
| `BUNDLE_INTERNAL_EVENTS` | DIRECT_OBSERVATION   | When a claim relates to bundle behavior, failure history, or structural fixes |

Learning events are among the highest-quality evidence because they
are machine-emitted, timestamped, and tied to specific RCA reports.

### MMD Integration
MMD should check for:
- Bundles that contain `tools/rca/` but no `events/LEARNING_EVENTS.ndjson`
  (RCA exists but learning events aren't being emitted)
- Learning events that reference corrective actions not reflected in
  the bundle's version qualifiers
- Failure events with no corresponding learning events (investigation
  started but never completed)

### Lineage Integration
Learning events provide evidence for lineage relationships:
- `EVT_LEARNING_CORRECTIVE_ACTION_RATIFIED` in bundle B proves it
  supersedes bundle A (the bundle where the failure occurred)
- This is stronger evidence than filename inference — it's the bundle
  itself declaring "I fixed what was wrong with my predecessor"

### CDR Integration (Pillar 6 — History-Aware Evolution)
Learning events ARE CDR Pillar 6 in machine-readable form:
- Every `EVT_LEARNING_*` event explains what was wrong before
- Every corrective action explains what it supersedes
- The event log is the attestation chain (CDR Pillar 7)

## Failure Modes (CDR Pillar 4)

| Failure Mode | Safe State | Recovery |
|---|---|---|
| RCA auto-trigger fails to fire | Failure event exists but no RCA | Manual RCA invocation; investigate trigger mechanism |
| Learning emitter crashes mid-write | Partial NDJSON line | Last line is invalid JSON — reader must handle truncation |
| RCA identifies wrong root cause | Corrective action doesn't prevent recurrence | Next failure triggers another RCA cycle — self-correcting |
| Event log grows unbounded | Performance degradation on query | Rotate logs; archive old events per retention policy |
| Bundle has no internal tools/ | Learning pipeline not present | Flag as gap in MMD; this bundle predates the learning pipeline |

## What This Is NOT

- Not a chatbot memory system
- Not a vector database
- Not a "lessons learned" document
- Not prompt engineering

It is a **deterministic, event-driven, self-correcting feedback loop**
that produces queryable evidence of behavioral change.
