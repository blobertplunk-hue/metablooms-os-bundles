# CAP-017: Invariant Evaluation Gate

> **System ID**: SYS-017
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Evaluates all ACTIVE invariants registered in the Invariant Registry by running their mechanical checkers, ensuring that foundational system properties are upheld across every commit and preventing regression of critical governance constraints.

## Source Files

- `.codex/validators/run_invariant_gate.py`

## Entry Points

- `main` — CLI entry point; loads the invariant registry and runs all ACTIVE invariant checkers
- `check_mb_inv_nlq_required_v1` — verifies that the NLQ (No Loose Queries) invariant holds: all factual claims cite evidence
- `check_mb_inv_bundle_internals_v1` — verifies that bundle internal structure constraints are satisfied
- `check_mb_inv_maturity_pipeline_v1` — verifies that the maturity pipeline progression rules are respected
- `check_mb_inv_claim_strength_v1` — verifies that claim strength qualifiers are appropriately scoped
- `check_mb_inv_toolbox_reality_v1` — verifies that toolbox references point to real, existing tools
- `check_mb_inv_wikipedia_prohibition_v1` — verifies that Wikipedia is not cited as a primary evidence source

## Contract

### Inputs

- `.codex/artifacts/INVARIANT_REGISTRY.json` — registry of all declared invariants and their status
- Various policy documents under `.codex/policies/`
- JSON schemas under `.codex/schemas/`
- Validator scripts under `.codex/validators/`

### Outputs

- `EXIT 0` — all ACTIVE invariants pass their mechanical checks
- `EXIT 14` — at least one ACTIVE invariant failed its check

### Preconditions

- `INVARIANT_REGISTRY.json` must exist and be valid JSON
- All referenced policy documents, schemas, and validators must be present
- Each ACTIVE invariant must have a corresponding mechanical checker function

### Postconditions

- If EXIT 0: all 6 ACTIVE invariants (NLQ, bundle internals, maturity pipeline, claim strength, toolbox reality, Wikipedia prohibition) have been mechanically verified
- If EXIT 14: at least one invariant check failed; the failing invariant ID and reason are reported

### Failure Mode

FAIL_CLOSED — any invariant failure causes the gate to fail, blocking the commit via SYS-012.

## Dependencies

- None (standalone validation gate)

## Patterns Used

- `FAIL_CLOSED` — any invariant violation blocks the commit

## Evidence

6 ACTIVE invariants with mechanical checkers: MB_INV_NLQ_REQUIRED_v1 (evidence citation), MB_INV_BUNDLE_INTERNALS_v1 (bundle structure), MB_INV_MATURITY_PIPELINE_v1 (maturity progression), MB_INV_CLAIM_STRENGTH_v1 (qualifier scoping), MB_INV_TOOLBOX_REALITY_v1 (tool existence), MB_INV_WIKIPEDIA_PROHIBITION_v1 (source exclusion). Each checker runs independently and reports pass/fail with detail.

## Governance

- **MPP Phase**: N/A (registered as gate in SYS-012)
- **Gate**: Registered as a sub-gate in the Master Governance Gate (SYS-012)
- **Schema**: `.codex/schemas/INVARIANT_REGISTRY.schema.json` (constrains the input registry)
