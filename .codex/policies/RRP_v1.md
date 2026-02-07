# RRP v1 — Recursive Refinement Protocol

## Purpose

RRP ensures outputs improve through iteration without unbounded loops
or scope creep. Every deliverable goes through BUILD → EVALUATE → REWRITE
with strict convergence controls.

## Pipeline

```
BUILD (Phase 3) → EVALUATE (Phase 4) → REWRITE (Phase 5)
                         ↑                       |
                         └───── if defects ───────┘
                              (max 2 re-entries)
```

## Phase Rules

### BUILD (Phase 3)
- Produce all requested deliverables
- Follow CDR requirements (WHY, constraints, failure modes)
- Emit artifacts to canonical paths

### EVALUATE (Phase 4)
- READ-ONLY inspection of BUILD outputs
- Identify defects, each with a stable `defect_id`
- Categorize defects:
  - `SCHEMA_VIOLATION` — output doesn't match schema
  - `MISSING_FIELD` — required field absent
  - `LOGIC_ERROR` — incorrect classification or computation
  - `STALE_REFERENCE` — references outdated information
  - `SCOPE_VIOLATION` — output exceeds task scope
  - `CDR_VIOLATION` — decision without justification
- NO fixes, NO new ideas, NO scope expansion
- Emit EVALUATION_REPORT.json

### REWRITE (Phase 5)
- Apply ONLY defects enumerated in EVALUATION_REPORT
- Each fix must reference its `defect_id`
- NO new concepts
- NO scope expansion
- If a fix cannot be applied without introducing new scope → flag it
  and leave the defect open
- Emit REWRITE_REPORT.json

## Convergence Controls

### Maximum Iterations
- The EVALUATE → REWRITE cycle may execute at most **2 times**
- Total pipeline: BUILD → EVALUATE → REWRITE → EVALUATE₂ → REWRITE₂
- After 2 rewrites, if defects remain → emit them as KNOWN_DEFECTS
  in the TURN_RECEIPT and proceed to self-verification

### Convergence Test
After each REWRITE, compare:
- `defects_before` = count from EVALUATION_REPORT
- `defects_after` = count from re-evaluation

If `defects_after >= defects_before`:
→ Refinement is NOT converging
→ STOP rewriting
→ Emit remaining defects as KNOWN_DEFECTS
→ Proceed to self-verification

### Loop Detection
If a REWRITE re-introduces a previously fixed defect (same `defect_id`):
→ Flag as OSCILLATING_DEFECT
→ Do NOT attempt to fix again
→ Record in REWRITE_REPORT

### Scope Creep Detection
If EVALUATE identifies something that was NOT a defect in the original
BUILD but is a "nice to have" or "improvement":
→ Classify as SCOPE_CREEP
→ Do NOT fix in REWRITE
→ Optionally record as a future task

## Artifact Schemas

### EVALUATION_REPORT.json
```json
{
  "phase": "EVALUATE",
  "iteration": 1,
  "artifacts_evaluated": ["<path>", ...],
  "defects": [
    {
      "defect_id": "DEF-001",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "<defect category>",
      "artifact": "<path>",
      "description": "<what's wrong>",
      "location": "<field or line reference>"
    }
  ],
  "total_defects": 0,
  "scope_creep_items": []
}
```

### REWRITE_REPORT.json
```json
{
  "phase": "REWRITE",
  "iteration": 1,
  "fixes_applied": [
    {
      "defect_id": "DEF-001",
      "fix_description": "<what was changed>",
      "artifacts_modified": ["<path>"]
    }
  ],
  "defects_deferred": [],
  "oscillating_defects": [],
  "known_defects_remaining": []
}
```
