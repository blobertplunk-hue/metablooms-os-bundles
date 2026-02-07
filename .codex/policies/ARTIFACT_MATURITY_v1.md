# Artifact Maturity Pipeline v1

## Rationale (CDR Pillar 1)

**Problem:** Governance artifacts are created at different levels of rigor. Some have
schemas, some have validators, some have neither. There is no rule that forces an
artifact through a progression from "exists" to "validated" to "mechanically enforced."
This means specifications accumulate without enforcement, and the gap between what is
claimed and what is checked grows silently.

**Chosen solution:** A mandatory three-stage pipeline that every governance artifact
must progress through. Each stage has mechanical proof requirements. Nothing advances
without evidence. Nothing claims enforcement without a validator that returns an exit code.

**Core invariant:** `MB_INV_MATURITY_PIPELINE_V1` — every artifact in the governance
system must be registered in the maturity tracker, and its claimed maturity stage must
be mechanically verifiable.

---

## 1. PIPELINE STAGES

Every governance artifact progresses through exactly three stages:

```
DRAFT ──→ VALIDATED ──→ ENFORCED
```

### Stage 1: DRAFT

**What it means:** The artifact exists. It has been written and committed.

**Proof required:**
- File exists at its declared path
- File is valid (JSON parses, Markdown renders)

**What it does NOT mean:** The artifact is correct, complete, or checked by anything.

**DRAFT is temporary for governed artifacts.** If `enforcement_required` is true and
`governance_class` is not `NON_GOVERNED`, DRAFT blocks commits. The only way forward
is to write a validator and advance to VALIDATED. This prevents specifications from
accumulating without enforcement.

### Governance Classification

Every artifact has a `governance_class`:

| Class | Meaning | DRAFT Allowed? |
|---|---|---|
| `SYSTEM` | Core infrastructure (schemas, artifacts, receipts, standards) | NO |
| `PIPELINE` | Defines a process (MPP, SEE, RRP, learning loop) | NO |
| `INVARIANT` | Defines system invariants | NO |
| `VALIDATOR` | Is the enforcement mechanism itself | N/A (always ENFORCED) |
| `NON_GOVERNED` | Superseded, reference-only, explicitly exempt | YES |

### Stage 2: VALIDATED

**What it means:** The artifact has been checked against a schema or structural
specification and passes.

**Proof required:**
- A JSON Schema exists for the artifact (in `.codex/schemas/`), OR
- A structural validator exists that checks the artifact's internal consistency
- The artifact currently passes its validation check

**Advancement rule:** An artifact advances from DRAFT to VALIDATED when:
1. A schema or structural check exists for it
2. The artifact passes that check
3. The maturity tracker is updated to reflect VALIDATED status

### Stage 3: ENFORCED

**What it means:** A mechanical gate exists that will **block commits** if the
artifact's invariants are violated.

**Proof required:**
- A validator script exists in `.codex/validators/` that checks this artifact
- That validator is registered in `run_governance_gate.py`
- The validator returns a non-zero exit code on failure
- The pre-commit hook runs the governance gate

**Advancement rule:** An artifact advances from VALIDATED to ENFORCED when:
1. A validator exists in `.codex/validators/`
2. The validator is wired into the master gate
3. The pre-commit hook calls the master gate
4. The maturity tracker is updated to reflect ENFORCED status

---

## 2. MATURITY TRACKER

All maturity states are recorded in `.codex/artifacts/ARTIFACT_MATURITY.json`.

Each entry contains:
- `artifact_path`: path relative to repo root
- `artifact_type`: `policy`, `schema`, `artifact`, `receipt`, `validator`
- `maturity`: `DRAFT`, `VALIDATED`, or `ENFORCED`
- `schema_path`: path to validating schema (null if none)
- `validator_path`: path to enforcement validator (null if none)
- `gate_name`: name of gate in master runner (null if not wired)
- `advanced_utc`: timestamp of last stage advancement

### Maturity Verification Rules

The maturity gate enforces these rules:

| Claimed Stage | Required Proof |
|---|---|
| DRAFT | File exists at artifact_path |
| VALIDATED | File exists + schema_path exists + artifact passes schema |
| ENFORCED | All VALIDATED rules + validator_path exists + gate_name is registered |

If any proof fails, the claimed maturity is a **lie** and the gate blocks the commit.

---

## 3. DEMOTION

Maturity can decrease. If a schema changes and an artifact no longer passes, it
demotes from VALIDATED to DRAFT. If a validator is removed, the artifact demotes
from ENFORCED to VALIDATED.

Demotion is not a failure state — it is a signal that work is needed. The gate
catches the mismatch between claimed maturity and actual proof.

---

## 4. PIPELINE FOR NEW ARTIFACTS

When creating any new governance artifact, the pipeline is:

```
1. Write the artifact                          → DRAFT
2. Write or identify a schema for it           → still DRAFT
3. Validate artifact against schema, passes    → VALIDATED
4. Write a validator in .codex/validators/     → still VALIDATED
5. Wire validator into master gate             → still VALIDATED
6. Validator runs and passes in pre-commit     → ENFORCED
```

No step may be skipped. You cannot claim ENFORCED without steps 1-6.

---

## 5. FAILURE MODES (CDR Pillar 4)

| Failure Mode | Safe State | Recovery |
|---|---|---|
| Artifact deleted but still in tracker | Gate detects file missing, blocks commit | Remove entry or restore file |
| Schema changes, artifact now invalid | Demotion from VALIDATED to DRAFT | Fix artifact or fix schema |
| Validator removed or broken | Demotion from ENFORCED to VALIDATED | Restore or rewrite validator |
| New artifact created without tracker entry | Gate detects untracked artifact, blocks commit | Add entry to tracker |
| Tracker claims ENFORCED but no gate registered | Gate detects false claim, blocks commit | Register gate or demote |

---

## 6. CONSTRAINTS (CDR Pillar 2)

1. The maturity pipeline is one-directional by intent. Demotion only occurs mechanically when proof is lost.
2. There is no DEPRECATED stage — use BUNDLE_LIFECYCLE for artifact retirement.
3. The maturity gate itself must be ENFORCED (self-referential: it checks itself).
4. Human-authored documents (BOOT.md, CDR_v2.md) are DRAFT by default unless they have schemas.
5. Validators are ENFORCED by definition (they are the enforcement mechanism).

---

## APPENDIX A: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-07 | Initial specification. Three-stage pipeline with mechanical proof. |

---

*CDR Attestation: Pillar 1 (rationale) in header. Pillar 2 (constraints) in Section 6.
Pillar 4 (failure modes) in Section 5. Pillar 7 (attestation) is this paragraph.*
