# CAP-009: Pattern Catalog

> **System ID**: SYS-009
> **Type**: PERSIST
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

Static catalog of 8 architectural patterns used by the Decision Engine for constraint-driven elimination.

## Source Files

- MetaBlooms_OS/patterns/MB_PATTERN_CATALOG.json

## Entry Points

- Loaded by DecisionEngine._load_pattern_catalog (JSON data, not executable)

## Contract

### Inputs

- None (static data file)

### Outputs

- 8 patterns: BIJECTION, IDEMPOTENT, MONOTONIC, FAIL_CLOSED, CONSTRAINT_ELIMINATION, RECURSIVE_REFINEMENT, EVIDENCE_BEFORE_EXECUTION, LESSON_PROMOTION

### Preconditions

File exists at patterns/MB_PATTERN_CATALOG.json

### Postconditions

Pattern data available for constraint matching

### Failure Mode

DEGRADED — DecisionEngine falls back to empty catalog if file missing

## Dependencies

None (foundational)

## Patterns Used

N/A (IS the pattern catalog)

## Evidence

v2.0, each pattern has when_to_use, strengths, weaknesses, required_capabilities, forbidden_when, exemplar, claim_strength

## Governance

- **MPP Phase**: N/A (referenced by Phase 3)
- **Gate**: N/A
- **Schema**: N/A
