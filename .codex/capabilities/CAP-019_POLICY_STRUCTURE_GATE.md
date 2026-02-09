# CAP-019: Policy Structure Gate

> **System ID**: SYS-019
> **Type**: VALIDATE
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Validates that all 9 governance policy documents contain their required structural sections, ensuring that no policy is missing critical components that downstream systems depend on.

## Source Files

- `.codex/validators/run_policy_structure_gate.py`

## Entry Points

- `main` — orchestrates validation of all 9 policy documents and emits final pass/fail exit code
- `validate_super_prompt` — checks SUPER_PROMPT for MPP phases, forbidden language list, and BOOT.md reference
- `validate_cdr` — checks CDR policy for all 7 pillars
- `validate_see` — checks SEE policy for evidence sources, quality ranks, and BUNDLE_INTERNAL_EVENTS
- `validate_rrp` — checks RRP policy for BUILD/EVALUATE/REWRITE cycle and convergence bounds
- `validate_deltagate` — checks DELTAGATE policy for PROPOSE/ADMIT/REJECT workflow
- `validate_lifecycle` — checks LIFECYCLE policy for all 6 statuses
- `validate_learning_pipeline` — checks LEARNING_PIPELINE policy for RCA/EVT_FAIL/EVT_LEARNING
- `validate_mbql` — checks MBQL policy for NLQ/FROM/WHERE/SELECT/INTENT_IR/INVARIANT
- `validate_maturity` — checks MATURITY policy for DRAFT/VALIDATED/ENFORCED levels and demotion rules

## Contract

### Inputs

- 9 policy documents in `.codex/policies/*.md`:
  - SUPER_PROMPT
  - CDR
  - SEE
  - RRP
  - DELTAGATE
  - LIFECYCLE
  - LEARNING_PIPELINE
  - MBQL
  - MATURITY

### Outputs

- `EXIT 0` — all 9 policies pass structural validation
- `EXIT 16` — one or more policies are missing required sections

### Preconditions

- All 9 policy documents must exist in `.codex/policies/`
- Policy documents must be valid markdown

### Postconditions

- SUPER_PROMPT contains MPP phase definitions, forbidden language list, and a reference to BOOT.md
- CDR contains all 7 pillars
- SEE contains evidence sources, quality ranks, and BUNDLE_INTERNAL_EVENTS
- RRP contains BUILD/EVALUATE/REWRITE cycle definition and convergence bounds
- DELTAGATE contains PROPOSE/ADMIT/REJECT workflow
- LIFECYCLE contains all 6 statuses
- LEARNING_PIPELINE contains RCA/EVT_FAIL/EVT_LEARNING
- MBQL contains NLQ/FROM/WHERE/SELECT/INTENT_IR/INVARIANT
- MATURITY contains DRAFT/VALIDATED/ENFORCED levels and demotion rules

### Failure Mode

FAIL_CLOSED — any missing required section causes the gate to reject with EXIT 16.

## Dependencies

None

## Patterns Used

- **BIJECTION** — each policy structure bijects to its required sections; every required section must appear and every section present must be required

## Evidence

Validates 9 policies: SUPER_PROMPT (MPP phases, forbidden language, BOOT ref), CDR (7 pillars), SEE (evidence sources, quality ranks, BUNDLE_INTERNAL_EVENTS), RRP (BUILD/EVALUATE/REWRITE, convergence), DELTAGATE (PROPOSE/ADMIT/REJECT), LIFECYCLE (6 statuses), LEARNING_PIPELINE (RCA/EVT_FAIL/EVT_LEARNING), MBQL (NLQ/FROM/WHERE/SELECT/INTENT_IR/INVARIANT), MATURITY (DRAFT/VALIDATED/ENFORCED, demotion).

## Governance

- **MPP Phase**: Phase 5 (VALIDATE)
- **Gate**: Policy Structure Gate (EXIT 16)
- **Schema**: N/A (validates markdown structure, not JSON)
