# CAP-004: MMD Engine

> **System ID**: SYS-004
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The Missing Middle Detection Engine scans for gaps across schemas, policies, mastery definitions, decisions, evidence, and state integrity. It exists to catch structural and logical defects that individual engines cannot detect in isolation, serving as the pipeline's primary quality gate.

## Source Files

- `MetaBlooms_OS/engines/mmd_engine.py`

## Entry Points

- `run` — Executes all six detection methods and aggregates findings into a single report
- `emit_report` — Writes the MMD report to disk as structured JSON
- `method_schema_coverage` — Detects schemas that are referenced but missing, or present but unused
- `method_policy_coverage` — Detects policies that are referenced but missing, or present but unused
- `method_mastery_readiness` — Checks whether the mastery definition is complete and ready for execution
- `method_decision_completeness` — Validates that all required decisions have been recorded
- `method_evidence_gaps` — Identifies claims that lack sufficient evidence from the SEE phase
- `method_state_integrity` — Checks MB_STATE.json for corruption, staleness, or internal inconsistencies

## Contract

### Inputs

- `mastery_definition` (object, optional) — The mastery definition from Phase 0.5, if available
- `see_results` (object, optional) — Evidence results from Phase 1, if available

### Outputs

- `MMD_REPORT.json` — Structured report with status `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`, containing all findings organized by detection method and severity

### Preconditions

- The `.codex/` directory structure must exist so that schema and policy coverage methods can scan for files
- At least one detection method must have inputs available (mastery definition or SEE results)

### Postconditions

- An MMD report exists with a definitive status of PASS, PASS_WITH_WARNINGS, or FAIL
- Every finding has a severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO) and a source detection method
- If status is FAIL, at least one CRITICAL finding exists

### Failure Mode

FAIL_CLOSED — When any CRITICAL finding is detected, the report status is FAIL and the MPP orchestrator blocks progression to execution phases. No partial execution is permitted past a FAIL status.

## Dependencies

- SYS-008 (State Manager)

## Patterns Used

- `FAIL_CLOSED` — CRITICAL findings halt pipeline progression unconditionally

## Evidence

6 detection methods, severity CRITICAL/HIGH/MEDIUM/LOW/INFO.

## Governance

- **MPP Phase**: 2
- **Gate**: MMD gate — a FAIL status blocks all execution phases (3+); PASS_WITH_WARNINGS allows progression with logged warnings
- **Schema**: `MMD_REPORT.schema.json`
