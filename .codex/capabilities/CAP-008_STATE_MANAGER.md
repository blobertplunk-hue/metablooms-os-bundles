# CAP-008: State Manager

> **System ID**: SYS-008
> **Type**: PERSIST
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The State Manager provides persistent, cross-session storage for mastery definitions, decision records, lessons, source reputations, and query patterns. It exists as the foundational persistence layer that all other engines depend on for continuity between pipeline runs.

## Source Files

- `MetaBlooms_OS/state/state_manager.py`

## Entry Points

- `save` — Serializes the full state to MB_STATE.json
- `store_mastery_definition` — Persists a mastery definition artifact to state
- `get_mastery_definition` — Retrieves a mastery definition by domain or ID
- `find_similar_mastery` — Searches for prior mastery definitions similar to a given domain or description
- `store_decision_record` — Persists a decision record artifact to state
- `find_decisions_by_type` — Retrieves decision records filtered by decision type
- `store_lesson` — Persists a lesson with its lifecycle stage and recurrence metadata
- `get_lessons_at_level` — Retrieves lessons filtered by lifecycle stage (observation, hypothesis, constraint, invariant)
- `promote_lesson` — Advances a lesson to the next lifecycle stage
- `update_source_reputation` — Updates the reputation score for an evidence source
- `update_query_pattern` — Records a query pattern and its effectiveness for future SEE optimization
- `get_intelligence_summary` — Computes and returns the system's accumulated intelligence score

## Contract

### Inputs

- `os_root` (string, path) — Root path of the MetaBlooms OS directory, used to locate MB_STATE.json
- `prior_state` (object, optional) — An existing state object to initialize from, instead of loading from disk

### Outputs

- `MB_STATE.json` — The persisted state file containing all mastery definitions, decision records, lessons, source reputations, and query patterns
- `intelligence_summary` (object) — Computed intelligence score and breakdown by category

### Preconditions

- The `os_root` path must be a valid, writable directory
- No other process should hold a write lock on MB_STATE.json during save operations

### Postconditions

- MB_STATE.json reflects all mutations made since the last save
- The intelligence summary accurately reflects the current state contents
- All stored artifacts are retrievable by their respective getter methods

### Failure Mode

Creates fresh state if MB_STATE.json is missing or corrupt. The State Manager never halts the pipeline due to state loading failures; it falls back to an empty state and logs a warning. This ensures the system can always bootstrap from scratch.

## Dependencies

None — The State Manager is foundational and has no dependencies on other systems.

## Patterns Used

- `IDEMPOTENT` — Repeated saves with the same state produce identical MB_STATE.json content
- `MONOTONIC` — State accumulates over time; entries are never deleted, only added or promoted

## Evidence

Intelligence formula: mastery_defs*3 + decision_records*2 + lessons*1 + constraints*5 + invariants*10.

## Governance

- **MPP Phase**: N/A (used by all phases as the shared persistence layer)
- **Gate**: None (the State Manager is a service, not a gate; other systems gate based on state contents)
- **Schema**: None (MB_STATE.json follows internal conventions; individual artifacts within state conform to their respective schemas)
