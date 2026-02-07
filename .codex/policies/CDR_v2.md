# CDR v2.0 — Coding Done Right (Justification-First Edition)

## What CDR Is

CDR is a software construction standard in which code is the secondary
artifact and documented, justified intent is the primary artifact.

> An unexplained line of code is a defect, regardless of whether it works.

Execution correctness alone is insufficient. Code is only admissible
when every structural and logical choice is:

- **explicit**
- **justified**
- **attested**

## Core Axiom

> Code exists first to be understood by future humans, and only second
> to be executed by machines.

Misunderstanding is the dominant failure mode; CDR optimizes against it.

## The Seven Pillars

### 1. Proactive Rationale

Every non-trivial module/function must include a **Rationale Header**
explaining:

- The problem being solved
- The chosen solution
- Why alternatives were rejected

A rationale header is NOT a docstring. A docstring says what the code
does. A rationale header says WHY the code exists and WHY it takes
this form rather than another.

### 2. Explicit Constraint Mapping

Code must state which constraints it optimizes for and what it
sacrifices, with justification.

Example: "This function trades memory for speed because the input
set is bounded at 90 files and latency matters more than RAM here."

Without constraint mapping, future maintainers cannot distinguish
between a deliberate tradeoff and an accidental limitation.

### 3. Semantic Domain Authority

No generic "utils/helpers."

All logic lives in named, law-bearing domain constructs. Examples:

| Instead of           | Use                          |
|----------------------|------------------------------|
| `utils.classify()`   | `BundleClassifier.classify()` |
| `helpers.validate()` | `SchemaValidator.validate()`  |
| `misc.parse_name()`  | `BundleNameParser.parse()`    |

Every construct declares its domain of authority — what it governs,
what it does NOT govern, and where its boundaries are.

### 4. Anticipated Failure Intent

Failure paths are deliberate design decisions, not afterthoughts.

Every function/module must declare:

- **Expected failure modes** — what can go wrong
- **Safe state** — where the system lands on failure
- **Recovery path** — how to get back to a working state (or why
  recovery is not possible and what happens instead)

Silent swallowing of errors is a CDR violation. "Catch all, log nothing"
is a CDR violation.

### 5. Integration Reciprocity

Modules declare their integration contract:

| Declaration         | Meaning                                      |
|---------------------|----------------------------------------------|
| **Assumptions**     | What must be true for this to work            |
| **Inputs**          | What it consumes (type, range, source)        |
| **Outputs**         | What it produces (type, guarantees)           |
| **Side effects**    | What it changes beyond its return value       |
| **Promises**        | What integrators can rely on                  |

If a module changes its promises, that is a breaking change regardless
of whether the API signature changed.

### 6. History-Aware Evolution

Every delta (change) explains:

- What it replaces or supersedes
- Why the prior logic became invalid
- What evidence triggered the change

Code that silently overwrites prior logic without explanation is a
CDR violation. "I rewrote this because it was bad" is insufficient.
"I rewrote this because the prior implementation assumed X, but
MMD-017 showed X was false" is sufficient.

### 7. Mandatory Attestation

The generator (human or LLM) must be able to reconstruct and attest
to the reasoning chain behind any piece of code.

- If asked "why does this line exist?", the answer must be available
  without reading the rest of the codebase.
- Unattested code is invalid and must be deleted or attested.
- "The model generated it" is not attestation.
- "This line exists because [specific reason]" is attestation.

## What CDR Explicitly Rejects

| Anti-pattern                        | Why it's rejected                           |
|-------------------------------------|---------------------------------------------|
| Cleverness without justification    | Optimizes for author ego, not comprehension |
| Implicit trust ("the model knows")  | Unattested; violates Pillar 7               |
| Silent success                      | Hides failure modes; violates Pillar 4      |
| Oral-tradition code                 | Knowledge that exists only in someone's head is not engineering |
| Premature optimization without argument | Violates Pillar 2 (no constraint mapping) |

**Clarity wins unless performance tradeoffs are explicitly argued.**

## What CDR Is NOT

- **Not a style guide** — CDR does not prescribe tabs vs spaces,
  naming conventions, or formatting rules
- **Not a framework** — CDR does not provide libraries, base classes,
  or runtime components
- **Not a linter** — CDR cannot be fully automated (though some
  pillars can be partially checked)

CDR is a **quality bar**, an **admission filter**, and a
**decision standard**.

## CDR Violation Classes

| Class | Pillar | Description | Severity |
|-------|--------|-------------|----------|
| `CDR-NORATIONALE` | 1 | Non-trivial logic with no rationale header | HIGH |
| `CDR-NOCONSTRAINT` | 2 | Tradeoff made without stating what was sacrificed | MEDIUM |
| `CDR-GENERICDOMAIN` | 3 | Logic in utils/helpers instead of named domain construct | MEDIUM |
| `CDR-SILENTFAIL` | 4 | Error swallowed or failure path undocumented | HIGH |
| `CDR-NOCONTRACT` | 5 | Module has no integration declarations | MEDIUM |
| `CDR-GHOSTDELTA` | 6 | Change made without explaining what it supersedes | HIGH |
| `CDR-UNATTESTED` | 7 | Code exists with no reconstructable reasoning | CRITICAL |

## How CDR Fits the Governance System

| Layer | Role |
|-------|------|
| **ECL / Governance** | Declares WHEN heightened rules apply |
| **CDR** | Declares HOW code must be written when they apply |
| **DeltaGate** | May reject deltas that contain CDR violations |
| **RRP** | EVALUATE phase checks for CDR violations as defects |
| **SEE** | Evidence for Pillar 6 (history-aware evolution) |

CDR is about craft and legibility. Governance systems (MetaBlooms,
DeltaGate, SEE) may reference it, but CDR stands independently as
a construction standard.

## Applying CDR to Non-Code Artifacts

CDR applies to governance artifacts (JSON schemas, policy documents,
configuration) as well as code:

| Artifact Type | CDR Application |
|---------------|-----------------|
| JSON Schema   | Every field must have a description explaining WHY it exists |
| Policy Doc    | Every rule must state its rationale and what it prevents |
| Config File   | Non-obvious settings must have inline comments with rationale |
| Receipt       | Every field must be traceable to a pipeline requirement |
