# CAP-003: SEE Engine

> **System ID**: SYS-003
> **Type**: SEARCH
> **Status**: CODIFIED
> **Codified**: 2026-02-09

## Purpose

The Search for Evidence Engine gathers and ranks evidence for factual claims using multiple search methods and quality tiers. It exists to ensure that no claim passes into downstream phases without a traceable evidence basis, enforcing the EVIDENCE_BEFORE_EXECUTION principle.

## Source Files

- `MetaBlooms_OS/engines/see_engine.py`

## Entry Points

- `run` — Executes the full evidence-gathering pipeline across all provided claims
- `gather_evidence_for_claim` — Searches for evidence supporting or refuting a single claim using method priority based on claim type
- `emit_artifacts` — Writes the query log and source ledger to disk as structured JSON

## Contract

### Inputs

- `claims` (list[string]) — Factual claims requiring evidence verification
- `environment` (object) — Environment descriptor, notably `web_access` (YES/NO)

### Outputs

- `claim_evidence_map` (dict) — Mapping of each claim to its gathered evidence records
- `evidence_records` (list[object]) — All evidence items with source, method, quality rank, and relevance
- `query_log` (list[object]) — Record of every query attempted, including method and result status
- `SEE_QUERY_LOG.json` — Persisted query log artifact
- `SOURCE_LEDGER.json` — Persisted source reputation and ranking artifact

### Preconditions

- At least one claim must be provided
- The State Manager (SYS-008) must be available for source reputation persistence
- Environment descriptor must indicate whether web access is available

### Postconditions

- Every input claim has at least one evidence record (even if the record is "no evidence found")
- The query log captures all attempted methods and their outcomes
- The source ledger reflects updated reputation scores for all consulted sources

### Failure Mode

DEGRADED — Enters SOURCE-LIMITED mode when no web access is available. Still produces evidence records from available local/cached sources, but marks all outputs with a SOURCE-LIMITED quality ceiling. Does not halt the pipeline.

## Dependencies

- SYS-008 (State Manager)

## Patterns Used

- `EVIDENCE_BEFORE_EXECUTION` — Evidence must be gathered and recorded before any build or decision phase consumes the claims

## Evidence

6 methods, Q1-Q6 quality ranks, claim-type-specific method priority.

## Governance

- **MPP Phase**: 1
- **Gate**: Evidence sufficiency gate — claims with no evidence are flagged for MMD review in Phase 2
- **Schema**: None (outputs are structured but not yet schema-constrained; SEE_QUERY_LOG and SOURCE_LEDGER follow internal conventions)
