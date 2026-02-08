# MMD Engine Specification — v2.0

## Purpose

The Missing Middle Detector (MMD) is a **mechanical gap detection engine**
that finds everything missing, broken, or inconsistent in the governance
system. It is NOT a report generator — it is a validator that runs 6
detection methods and fails if critical gaps are found.

## Design Principles

### From DO-178C / Aerospace Traceability
- **Bidirectional traceability**: every requirement must trace forward to
  an implementation, and every implementation must trace back to a
  requirement. Applied here: every policy traces to a validator, every
  validator traces to a registered gate.
- **Coverage analysis**: prove that testing covers requirements. Applied
  here: prove that schemas cover artifacts.

### From Graph Theory
- **Orphan detection**: nodes in a dependency graph with no incoming edges
  are unreferenced; nodes with no outgoing edges are dead ends.
- **Broken edge detection**: references between artifacts that point to
  non-existent targets.

### From Requirements Engineering
- **Completeness checking**: the set of requirements should be "closed" —
  no requirement references an undefined concept.
- **Intentional vs accidental absence**: distinguish "we decided not to
  do X" (DEFERRED with reason) from "we forgot X" (gap).

## Detection Methods

### METHOD 1: REFERENCE_GRAPH
**Source**: Graph-based dependency analysis
**What it does**: Parses all JSON artifacts and markdown policies for
file path references. Verifies each referenced path exists on disk.
**Catches**: Broken references, renamed files, deleted artifacts that
are still referenced.
**Exclusions**: MMD_REPORT.json is excluded (contains recommendations,
not live references). Paths with spaces are excluded (prose fragments).

### METHOD 2: SCHEMA_COVERAGE
**Source**: DO-178C requirements traceability
**What it does**: For every JSON artifact under `.codex/artifacts/`,
checks that a corresponding schema exists (via ARTIFACT_MATURITY tracker)
or that a structural_check is documented.
**Catches**: Artifacts with no schema validation, untracked artifacts.

### METHOD 3: TRACEABILITY
**Source**: ISO 26262 / IEC 62304 traceability matrices
**What it does**: Checks bidirectional tracing:
- Validators → must be registered in master governance gate
- Active invariants → must have mechanical checkers
- Schemas → must be referenced by at least one artifact
**Catches**: Unregistered validators, invariants without checkers,
orphaned schemas.

### METHOD 4: DEFERRAL_AUDIT
**Source**: Requirements management (avoid "lost" requirements)
**What it does**: Scans delta ledgers for DEFERRED items. Verifies
each has a `not_done_reason`. Flags deferrals without explanations.
**Catches**: Silent requirement drops, unexplained deferrals.

### METHOD 5: SELF_CHECK
**Source**: Self-referential integrity (Gödel-style)
**What it does**: Validates MMD_REPORT.json against its own schema.
Verifies summary counts match findings array. Checks finding IDs
are unique.
**Catches**: Stale summary counts, duplicate IDs, schema violations.

### METHOD 6: CATEGORY_COMPLETENESS
**Source**: Open-world vs closed-world assumption (knowledge representation)
**What it does**: Compares gap categories discovered by the engine against
the categories the MMD schema allows. If the engine discovers a gap type
the schema can't represent, that's a schema limitation.
**Catches**: Closed enum problems where new gap types are rejected.

## Severity Derivation

| Severity | Mechanical Rule |
|----------|----------------|
| CRITICAL | Blocks pipeline execution, produces incorrect output, or destroys data integrity |
| HIGH | Missing traceability, broken references to governed artifacts, unregistered validators |
| MEDIUM | Schema coverage gaps, stale counts, policy references to non-existent paths |
| LOW | Unreferenced schemas, cosmetic issues |
| INFO | Observations, no action needed |

## Exit Codes

- **0**: PASS (no issues) or PASS_WITH_WARNINGS (issues found, none CRITICAL)
- **18**: FAIL (CRITICAL issues found)

## Gate Registration

The MMD gate is registered in the master governance runner as:
```
("MMD", "run_mmd_gate.py", 18)
```

## Future Methods (identified but not yet implemented)

These detection methods were identified through SEE research but are not
yet implemented:

### METHOD 7: CIRCULAR_DEPENDENCY (planned)
Detect cycles in the artifact reference graph. A depends on B depends on
A = circular dependency that can cause bootstrap failures.

### METHOD 8: STALENESS_PROPAGATION (planned)
When artifact A changes, find all artifacts that reference A and check
if they need updating. Currently done ad-hoc; should be systematic.

### METHOD 9: SEMANTIC_CONSISTENCY (planned)
Check that claims made in one artifact don't contradict claims in another.
Requires natural language analysis or structured claim comparison.

### METHOD 10: COVERAGE_METRICS (planned)
Compute and report:
- % of artifacts with schemas
- % of policies with validators
- % of invariants with mechanical checkers
- % of delta ledger items with resolution tracking

This would provide a completeness bound (answering "how complete is our
governance system?").

## Self-Improvement Protocol

When the MMD gate discovers a new category of gap that the schema cannot
represent:
1. The CATEGORY_COMPLETENESS method reports it
2. The new category is added to `MMD_REPORT.schema.json`
3. A new detection method is written for that category (if mechanical)
4. The gate is re-run to verify it now catches the gap

This creates a recursive improvement loop: **MMD detecting its own
limitations and expanding to cover them**.

## Staleness

This document becomes stale if:
- New detection methods are added without documenting them here
- The exit code convention changes
- The gate registration changes
