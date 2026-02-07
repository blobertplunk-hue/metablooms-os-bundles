# DeltaGate v1 — Change Admission Policy

## Purpose

DeltaGate governs how changes to governed artifacts are proposed,
evaluated, and admitted. The execution agent may PROPOSE deltas.
Only an external admission authority may ACCEPT or REJECT them.

## Definitions

| Term            | Meaning                                                |
|-----------------|--------------------------------------------------------|
| **Delta**       | Any modification to an existing governed artifact       |
| **New Artifact**| A file that did not previously exist — not a delta     |
| **Admission**   | External decision to accept or reject a proposed delta |
| **Authority**   | Human operator or CI system with admission rights      |

## What Constitutes a Delta

A delta is any change to:
- An existing file in `os_bundles/`
- `.gitattributes` LFS configuration
- Any file under `.codex/` that was previously committed
- `CLAUDE.md`

The following are NOT deltas (they are new artifacts):
- New receipt files emitted during a governed session
- New research logs (SEE_QUERY_LOG, SOURCE_LEDGER)
- First-time creation of artifacts that don't yet exist

## Admission Process

### 1. Proposal
The agent emits a delta proposal:
```json
{
  "delta_id": "DELTA-<NNN>",
  "proposed_utc": "<timestamp>",
  "affected_files": ["<path>", ...],
  "change_type": "MODIFY | DELETE | RENAME | RESTRUCTURE",
  "description": "<what and why>",
  "mmd_findings_addressed": ["MMD-<NNN>", ...],
  "reversible": true | false
}
```

### 2. Evaluation
The agent may evaluate the delta's impact but MUST NOT apply it.

### 3. Admission Decision
External authority records:
```json
{
  "delta_id": "DELTA-<NNN>",
  "decision": "ACCEPTED | REJECTED | DEFERRED",
  "decided_by": "<authority identifier>",
  "decided_utc": "<timestamp>",
  "conditions": "<any conditions on acceptance>"
}
```

### 4. Application
Only after ACCEPTED status may the agent apply the delta.

## Admission Authority

The admission authority is declared in Phase -1:
- If `human_admission_authority_present` = YES → human decides
- If `ci_pipeline_present` = YES → CI decides
- If neither → agent operates in EVIDENCE-ONLY MODE and
  all deltas remain proposals until an authority is available

## Scope Exceptions

The following changes do NOT require DeltaGate admission:
- Emitting new receipts during a governed session
- Emitting new research artifacts (query logs, source ledgers)
- Fixing governance artifacts that fail self-verification
  (these are self-healing, not deltas)

## Delta Log

All proposed deltas are recorded in:
`.codex/receipts/DELTA_LOG.json`

Schema:
```json
{
  "deltas": [
    {
      "delta_id": "DELTA-001",
      "proposed_utc": "",
      "status": "PROPOSED | ACCEPTED | REJECTED | DEFERRED | APPLIED",
      "affected_files": [],
      "description": ""
    }
  ]
}
```
