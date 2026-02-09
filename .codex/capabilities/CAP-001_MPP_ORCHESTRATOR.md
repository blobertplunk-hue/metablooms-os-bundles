# CAP-001: MPP Orchestrator

> **System ID**: SYS-001
> **Type**: ORCHESTRATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The MPP Orchestrator drives the Mandatory Process Pipeline end-to-end, sequencing all phases from preparation through execution and ensuring that every phase gate is satisfied before advancing. It exists to guarantee that no governed task bypasses the required pipeline stages.

## Source Files

- `MetaBlooms_OS/mpp.py`

## Entry Points

- `MPPOrchestrator.__init__` — Initializes the orchestrator, wires all engine dependencies, and loads prior state
- `run_preparation_phases` — Executes phases -1 through 2 (boot, mastery, SEE, MMD) in sequence
- `run_execution_phases` — Executes phases 3 through 7.5 (decision, build, evaluate, rewrite, emit, assimilate)

## Contract

### Inputs

- `task_type` (string) — Classification of the task being orchestrated
- `task_description` (string) — Human-readable description of the task objective
- `domain` (string) — Domain context for mastery and evidence gathering
- `claims` (list[string]) — Factual claims requiring SEE verification
- `mastery_definition` (object) — Mastery artifact produced by Phase 0.5
- `build_artifacts` (list[object]) — Artifacts produced during the build phase
- `execution_results` (object) — Results from the execution phases for assimilation

### Outputs

- `TURN_RECEIPT.json` — Structured receipt summarizing the completed pipeline run
- `FAIL_RECEIPT.json` — Emitted when the pipeline halts due to a gate failure
- All phase artifacts — Every intermediate artifact produced by phases -1 through 7.5

### Preconditions

- All 6 engines (Mastery, SEE, MMD, Decision, RRP, Assimilation) and the State Manager must be importable and initialized
- A valid task description and task type must be provided
- The `.codex/` directory structure must exist for artifact output

### Postconditions

- Either a `TURN_RECEIPT.json` exists confirming successful completion of all phases, or a `FAIL_RECEIPT.json` exists identifying the failing phase and reason
- All intermediate phase artifacts have been persisted to their respective locations
- State has been saved via the State Manager

### Failure Mode

FAIL_CLOSED — Emits a `FAIL_RECEIPT.json` identifying the failing phase and halts the pipeline. No partial results are promoted as complete.

## Dependencies

- SYS-002 (Mastery Engine)
- SYS-003 (SEE Engine)
- SYS-004 (MMD Engine)
- SYS-005 (Decision Engine)
- SYS-006 (RRP Engine)
- SYS-007 (Assimilation Engine)
- SYS-008 (State Manager)

## Patterns Used

- `FAIL_CLOSED` — Pipeline halts on any gate failure rather than continuing in a degraded state
- `MONOTONIC` — Pipeline phases execute in strictly increasing order; no phase is skipped or re-ordered

## Evidence

14 pipeline phases, imports all 6 engines + StateManager.

## Governance

- **MPP Phase**: ALL (orchestrates all phases -1 through 7.5)
- **Gate**: Every inter-phase transition acts as a gate; the orchestrator enforces all of them
- **Schema**: `TURN_RECEIPT.schema.json`, `FAIL_RECEIPT` structure
