# CAP-007: Assimilation Engine

> **System ID**: SYS-007
> **Type**: LEARN
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The Assimilation Engine extracts lessons from completed pipeline runs and promotes recurring observations through a structured lifecycle from observation to invariant. It exists to ensure the system learns from every execution and converts experiential knowledge into reusable constraints and invariants.

## Source Files

- `MetaBlooms_OS/engines/assimilation_engine.py`

## Entry Points

- `run` — Executes the full assimilation pipeline: compare, extract, promote
- `compare_to_mastery` — Compares execution results against the mastery definition to identify performance gaps and successes
- `extract_lessons` — Derives structured lessons from the comparison, MMD report, and RRP reports
- `promote_lesson` — Manually promotes a lesson to the next lifecycle stage
- `auto_promote_recurring` — Automatically promotes lessons that have recurred across 3 or more sessions

## Contract

### Inputs

- `mastery_definition` (object) — The mastery artifact from Phase 0.5 used as the comparison baseline
- `execution_results` (object) — Results from the execution phases (build, evaluate, rewrite outputs)
- `mmd_report` (object) — The MMD report from Phase 2
- `rrp_reports` (list[object]) — Evaluation and rewrite reports from Phases 4-5

### Outputs

- `ASSIMILATION_REPORT.json` — Structured report containing mastery comparison results, extracted lessons, and promotion actions
- `lessons` (list[object]) — Extracted lessons with lifecycle stage, recurrence count, and source phase
- `auto_promoted_ids` (list[string]) — IDs of lessons that were automatically promoted due to recurrence

### Preconditions

- At least one of the following must be available: mastery definition, MMD report, or RRP reports
- The State Manager (SYS-008) must be available for lesson persistence and recurrence tracking

### Postconditions

- All extracted lessons have been persisted to state with their current lifecycle stage
- Lessons recurring across 3 or more sessions have been promoted to the next lifecycle stage
- The assimilation report captures the full comparison, extraction, and promotion activity

### Failure Mode

DEGRADED — Still extracts lessons even if the mastery comparison fails. If the comparison step encounters an error, the engine skips comparison and proceeds directly to lesson extraction from MMD and RRP reports. The assimilation report notes the degraded mode.

## Dependencies

- SYS-008 (State Manager)

## Patterns Used

- `LESSON_PROMOTION` — Lessons follow the OBSERVATION, HYPOTHESIS, CONSTRAINT, INVARIANT lifecycle with automatic promotion at recurrence thresholds

## Evidence

OBSERVATION, HYPOTHESIS, CONSTRAINT, INVARIANT lifecycle; auto-promotes at 3+ sessions.

## Governance

- **MPP Phase**: 7.5
- **Gate**: None (assimilation is the final phase; its outputs feed future pipeline runs, not the current one)
- **Schema**: `LESSON_PROMOTION.schema.json`
