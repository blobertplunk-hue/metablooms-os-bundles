# CAP-002: Mastery Engine

> **System ID**: SYS-002
> **Type**: CREATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The Mastery Engine defines what "world-class" looks like for a given task domain by synthesizing best-practitioner standards, success criteria, and knowledge gaps into a structured mastery definition. It exists to ensure every task has an explicit quality bar before execution begins.

## Source Files

- `MetaBlooms_OS/engines/mastery_engine.py`

## Entry Points

- `check_prior_mastery` — Searches state for an existing mastery definition matching the current domain
- `create_mastery_definition` — Builds a new mastery definition from task description, domain, standards, and constraints
- `validate` — Checks a mastery definition for completeness and internal consistency
- `check_readiness` — Evaluates whether the current state satisfies the mastery definition's prerequisites
- `compare_outputs` — Compares execution outputs against the mastery definition's success criteria

## Contract

### Inputs

- `task_description` (string) — Description of the task to master
- `domain` (string) — Domain context for the mastery definition
- `best_practitioners` (list[string]) — Reference practitioners or teams that define excellence
- `standards` (list[string]) — External standards or benchmarks to meet
- `world_class_standard` (string) — Narrative description of the world-class quality bar
- `success_criteria` (list[string]) — Measurable criteria for determining task success
- `knowledge_gaps` (list[string]) — Known gaps that must be addressed before execution
- `constraints` (list[string]) — Hard constraints on the solution space
- `see_queries_used` (list[string]) — SEE queries consumed during mastery creation

### Outputs

- `MASTERY_DEFINITION` artifact (`MDEF-{DOMAIN}_{DATE}.json`) — Structured mastery definition containing all inputs plus validation status and readiness assessment

### Preconditions

- A valid task description and domain must be provided
- The State Manager (SYS-008) must be available for persistence and prior-mastery lookup

### Postconditions

- A mastery definition artifact exists and has been persisted to state
- The definition has passed internal validation, or a list of validation errors has been returned
- If critical gaps exist, MPP progression is blocked until they are resolved

### Failure Mode

Returns a validation errors list; blocks MPP progression if critical gaps are detected. Does not emit a separate failure artifact — the orchestrator interprets validation failures as a phase gate block.

## Dependencies

- SYS-008 (State Manager)
- SYS-015 (LFS Gap)

## Patterns Used

- `EVIDENCE_BEFORE_EXECUTION` — Mastery definition must be established and validated before any build phase begins

## Evidence

check_prior_mastery, create_mastery_definition, validate, check_readiness, compare_outputs entry points; produces MDEF-{DOMAIN}_{DATE}.json artifacts; integrates with State Manager for persistence and lookup.

## Governance

- **MPP Phase**: 0.5
- **Gate**: Mastery validation gate — MPP cannot proceed to Phase 1 if the mastery definition has critical validation errors
- **Schema**: `MASTERY_DEFINITION.schema.json`
