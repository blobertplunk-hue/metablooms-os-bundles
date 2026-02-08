# Claim Strength Enforcement Policy — v1.0

## Purpose

Mandatory claim-strength labeling for all normative statements in the
governance system. Prevents silent upgrades from SOURCE-LIMITED to
enforceable requirements.

## Claim Strength Levels

| Level | Meaning | Enforcement |
|-------|---------|-------------|
| **SUPPORTED** | Evidence from primary sources confirms this claim | May be used as enforcement predicate |
| **SUPPORTED-INTENT** | Primary sources support the intent but not the exact form | May inform design, NOT enforce |
| **SOURCE-LIMITED** | Insufficient evidence; claim is plausible but unverified | MUST NOT be used as enforcement predicate |
| **DESIGN-CHOICE** | Deliberate design decision without external evidence requirement | May be enforced if CDR-justified |

## Enforcement Invariant (P0)

> Normative claims without SUPPORTED or DESIGN-CHOICE strength MUST NOT
> be used as enforcement predicates (gate conditions, invariant checks,
> or admission criteria).

This is fail-closed: if a claim lacks a strength label, it is treated
as SOURCE-LIMITED by default.

## Evidence Source Rules

### Prohibited Load-Bearing Sources

The following sources may NEVER serve as the sole evidence basis for
SUPPORTED claims:

1. **Wikipedia** — may be used for discovery/orientation only, never
   as load-bearing evidence for requirements, invariants, or formal
   definitions
2. **Unattributed AI outputs** — generated text without traceable
   source citations
3. **Stack Overflow answers** — unless linking to primary documentation

### Acceptable Sources for SUPPORTED Claims

- Primary academic papers (peer-reviewed)
- Official tool/framework documentation
- First-party specifications (RFCs, standards bodies)
- Direct filesystem observation (LOCAL_FS evidence)
- Bundle internal events (BUNDLE_INTERNAL_EVENTS)

## Application

Every governance artifact that makes normative claims MUST include
a `claim_strength` field. The field uses the enum defined above.

Schemas that reference DMDU/RDM concepts MUST tag each requirement
with its claim strength per SEMANTIC_STATE_v1.md.

## Staleness

This policy becomes stale if new claim strength levels are needed
or if the prohibited sources list requires updates.
