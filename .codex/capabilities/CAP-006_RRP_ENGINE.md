# CAP-006: RRP Engine

> **System ID**: SYS-006
> **Type**: TRANSFORM
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The Recursive Refinement Protocol Engine iterates artifacts through BUILD, EVALUATE, and REWRITE cycles until defects converge toward zero or the iteration cap is reached. It exists to systematically improve output quality through structured self-correction rather than one-shot generation.

## Source Files

- `MetaBlooms_OS/engines/rrp_engine.py`

## Entry Points

- `evaluate` — Assesses a set of artifacts for defects, producing an evaluation report with categorized findings
- `should_rewrite` — Determines whether the current defect count and trajectory justify another rewrite cycle
- `plan_rewrite` — Generates a rewrite plan specifying which defects to address and how
- `record_rewrite` — Records the rewrite action and its outcomes for the current iteration
- `get_known_defects` — Returns the current defect inventory from the most recent evaluation
- `emit_reports` — Writes evaluation and rewrite reports to disk as structured JSON

## Contract

### Inputs

- `artifacts` (list[object]) — The artifacts to evaluate and potentially rewrite
- `mastery_definition` (object, optional) — Mastery artifact used as the quality bar for evaluation, if available

### Outputs

- `EVALUATION_REPORT_{N}.json` — Defect report for iteration N, listing all found defects with severity and category
- `REWRITE_REPORT_{N}.json` — Rewrite action report for iteration N, documenting what was changed and why

### Preconditions

- At least one artifact must be provided for evaluation
- Artifacts must be in a format the engine can inspect (structured text or JSON)

### Postconditions

- At least one evaluation report exists
- If rewrites occurred, each rewrite has a corresponding rewrite report
- The defect count in the final evaluation is less than or equal to the defect count in the first evaluation (monotonic convergence)

### Failure Mode

Converges after MAX_ITERATIONS=2 even if defects remain. The engine does not block the pipeline on residual defects; it reports them and allows the orchestrator to decide whether to proceed. Remaining defects are carried forward as known technical debt.

## Dependencies

None — The RRP Engine operates independently on provided artifacts without requiring other system services.

## Patterns Used

- `RECURSIVE_REFINEMENT` — The BUILD, EVALUATE, REWRITE cycle with convergence testing (defects must decrease each iteration)

## Evidence

BUILD, EVALUATE, REWRITE cycle; convergence test (defects must decrease); MAX_ITERATIONS=2 cap.

## Governance

- **MPP Phase**: 4-5
- **Gate**: RRP convergence gate — the orchestrator checks that defect count is non-increasing across iterations
- **Schema**: None (evaluation and rewrite reports follow internal conventions)
