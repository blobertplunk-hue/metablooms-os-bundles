# CAP-005: Decision Engine

> **System ID**: SYS-005
> **Type**: DECIDE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The Decision Engine replaces ad-hoc keyword matching with a structured constraint-driven elimination pipeline for selecting among candidate approaches. It exists to make every architectural and design decision traceable, reproducible, and auditable through formal decision records.

## Source Files

- `MetaBlooms_OS/engines/decision_engine.py`

## Entry Points

- `make_decision` — Runs the full 5-step pipeline: extract constraints, enumerate candidates, eliminate, score, select
- `extract_constraints` — Derives hard and soft constraints from the mastery definition, toolbox reality, and additional inputs
- `enumerate_candidates` — Generates the initial candidate set from context, patterns, and additional candidates
- `eliminate` — Removes candidates that violate hard constraints
- `score_candidates` — Scores surviving candidates against soft constraints and pattern fit

## Contract

### Inputs

- `decision_type` (string) — Category of decision (e.g., architecture, tool selection, pattern choice)
- `context` (string) — Situational context for the decision
- `mastery_definition` (object) — Mastery artifact providing quality constraints
- `toolbox_reality` (object) — Available tools, libraries, and runtime capabilities
- `additional_constraints` (list[string]) — Extra hard or soft constraints beyond those derived from mastery
- `additional_candidates` (list[string]) — Extra candidates to include beyond auto-enumerated ones
- `evidence` (object) — SEE evidence relevant to the decision

### Outputs

- `DECISION_RECORD` artifact (`DR-{TYPE}_{TIMESTAMP}.json`) — Structured record containing all candidates, constraints, elimination rationale, scores, and the selected candidate with justification

### Preconditions

- At least 2 candidates must be available after enumeration (from auto-enumeration, additional_candidates, or both)
- The Pattern Catalog (SYS-009) must be loadable for pattern-based candidate generation and scoring

### Postconditions

- Exactly one candidate has been selected and recorded
- Every eliminated candidate has a documented elimination reason
- The decision record has been persisted to state via the State Manager

### Failure Mode

Raises an error if fewer than 2 candidates survive enumeration. The orchestrator treats this as a phase gate failure, blocking progression until the candidate pool is expanded.

## Dependencies

- SYS-008 (State Manager)
- SYS-009 (Pattern Catalog)

## Patterns Used

- `CONSTRAINT_ELIMINATION` — Candidates are eliminated by constraint violation before scoring, ensuring only viable options are compared

## Evidence

5-step pipeline replacing keyword matching with constraint-driven elimination.

## Governance

- **MPP Phase**: 3
- **Gate**: Decision completeness gate — all required decisions for the task must have records before build begins
- **Schema**: `DECISION_RECORD.schema.json`
