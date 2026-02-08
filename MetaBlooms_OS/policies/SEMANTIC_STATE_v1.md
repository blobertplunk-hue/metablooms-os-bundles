# Semantic State Lock — v1.0

## Purpose

Formalizes the boundary between SEALED (evidence-supported, enforceable)
and SOURCE-LIMITED (not enforceable without further evidence) governance
requirements. Prevents governance drift and silent elevation of unsupported
claims.

## Origin

Adversarial review of DMDU/RDM literature claims in chat session
(2026-02-08). All categories were stress-tested against primary sources.

---

## SEALED (SUPPORTED)

These requirements have evidence backing and are enforceable:

| Requirement | Evidence Basis |
|-------------|---------------|
| Scenario ensembles required in DMDU/RDM | Primary DMDU literature (Lempert et al.) |
| Scenario space must be explicit and documented | RDM methodology requirement |
| Robustness is comparative across scenarios | Core RDM/DMDU definition |
| Multiple robustness metric families exist | Literature survey (regret, reliability, worst-case, domain-specific) |
| No single canonical robustness equation is mandated | Absence proof across DMDU/RDM corpus |

## SOURCE-LIMITED (NOT ENFORCEABLE)

These requirements lack sufficient evidence to enforce. They remain
gated until a formal SEE investigation upgrades them:

| Requirement | Why Source-Limited |
|-------------|-------------------|
| Enumeration-only scenario requirements | DMDU allows generative definitions |
| Fixed scenario cardinality | No source mandates a specific count |
| Mandated scenario generation techniques | Multiple valid approaches exist |
| Canonical robustness equations | No single formula is authoritative |

## Enforcement Rule

Any normative claim in the governance system that references DMDU/RDM
concepts MUST be tagged with its claim strength (see CLAIM_STRENGTH_v1.md).
SOURCE-LIMITED claims may NOT be used as enforcement predicates.

## Staleness

This document becomes stale if:
- New DMDU/RDM evidence is gathered via SEE that contradicts a SEALED entry
- A SOURCE-LIMITED entry is upgraded via formal evidence review
