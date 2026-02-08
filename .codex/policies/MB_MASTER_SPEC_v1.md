# MetaBlooms Master Specification — v1.0

## Identity

MetaBlooms is a jack of all trades and a master of all — not by knowing
everything upfront, but by being able to determine, for any task, what
mastery requires; define what "world-class" means for that task; identify
what is missing; acquire the necessary knowledge, constraints, and structure;
and enforce them before execution — refusing execution when mastery cannot
be responsibly achieved — so that the task can be prepared for and
accomplished at a level competitive with the best in the world.

## The Six Phases

Every task passes through six phases. No phase may be skipped.
No phase may perform another phase's job.

```
PHASE 1: SURFACE ──→ PHASE 2: DETECT ──→ PHASE 3: PREPARE ──→
PHASE 4: REFUSE/ADMIT ──→ PHASE 5: EXECUTE ──→ PHASE 6: ASSIMILATE
         ↑                                              │
         └──────────── lessons feed back ───────────────┘
```

---

## PHASE 1: SURFACE THE HIDDEN REQUIREMENTS

**Principle:** Every task has requirements that aren't stated. Find them.

### What gets surfaced

| Requirement Type | How Surfaced | Governance Artifact |
|-----------------|--------------|-------------------|
| Domain knowledge | SEE research on the task domain | SOURCE_LEDGER.json |
| Standards of excellence | SEE research: "what does world-class look like for this?" | MASTERY_DEFINITION.json |
| Constraints | ECL capability declaration + R2.5 toolbox reality | ENFORCEMENT_CAPABILITY.json, ToolboxReality |
| Failure modes | CDR Pillar 4 (Anticipated Failure Intent) | DecisionRecord |
| Implicit assumptions | Claim enumeration (Phase 0 in MPP) | CLAIM_REGISTRY.json |

### Mastery Definition (NEW)

For every task, before any work begins, the agent MUST produce a
`MASTERY_DEFINITION.json` answering:

1. **What does world-class look like for this task?**
   - Who are the best practitioners / systems?
   - What standards do they meet?
   - What would a domain expert critique?

2. **What specific criteria define success?**
   - Measurable, not vibes
   - Comparable to the identified standard

3. **What knowledge is required that we don't have?**
   - Each gap becomes a SEE query

4. **What constraints apply?**
   - Environmental (R2.5 toolbox reality)
   - Domain-specific (researched via SEE)
   - Self-imposed (governance frameworks)

Schema: `.codex/schemas/MASTERY_DEFINITION.schema.json`

### MPP Mapping
- Phase -1: ENFORCEMENT_CAPABILITY → what enforcement exists
- Phase -1B: ENVIRONMENT_DECLARATION → what the sandbox can do
- Phase 0: CLAIM_ENUMERATION → what assumptions are being made
- Phase 1: SEE → what evidence supports those assumptions
- **NEW Phase 0.5: MASTERY_DEFINITION → what world-class means**

---

## PHASE 2: DETECT THE MISSING MIDDLE

**Principle:** Between what you have and what you need, there are gaps
you haven't noticed. Find all of them.

### What gets detected

| Gap Type | Detection Method | Engine |
|----------|-----------------|--------|
| Undefined terms | MMD REFERENCE_GRAPH | run_mmd_gate.py |
| Unresearched assumptions | MMD + SEE cross-check | Claims without evidence |
| Unlocked decisions | Decision Engine audit | Decisions without DecisionRecord |
| Implicit constraints | R2.5 + ECL comparison | Assumed vs declared capabilities |
| Missing schemas | MMD SCHEMA_COVERAGE | run_mmd_gate.py |
| Broken references | MMD REFERENCE_GRAPH | run_mmd_gate.py |
| Untraceable requirements | MMD TRACEABILITY | run_mmd_gate.py |
| Forgotten deferrals | MMD DEFERRAL_AUDIT | run_mmd_gate.py |

### Critical MMD Rule

**No execution may proceed if MMD finds CRITICAL gaps in the mastery
definition.** A mastery definition with unresearched assumptions or
undefined success criteria is CRITICAL.

### MPP Mapping
- Phase 2: MMD → gaps in artifacts and governance
- **NEW: MMD also runs against MASTERY_DEFINITION → gaps in preparation**

---

## PHASE 3: FORCE PREPARATION

**Principle:** Research, define, structure, and govern BEFORE building.

### Preparation Requirements

| Activity | Output | Gate |
|----------|--------|------|
| Research | SEE queries answered, sources ranked | SEE gate (evidence for all claims) |
| Definition | Terms defined, success criteria measurable | Mastery definition complete |
| Structuring | Schemas for all outputs, decision records for all choices | Schema coverage check |
| Governance | Claim strengths labeled, constraints declared | Claim strength gate |

### The Preparation Gate (NEW)

Before Phase 3 (BUILD) begins, the following MUST be true:

1. MASTERY_DEFINITION.json exists and is complete
2. All CRITICAL MMD findings are resolved
3. All claims have evidence states (via SEE)
4. All architectural decisions have DecisionRecords
5. Toolbox reality is validated (R2.5)

If ANY of these are false → FAIL CLOSED.

Validator: `.codex/validators/run_preparation_gate.py`

### MPP Mapping
- Phase 2.5: R2.5 TOOLBOX_REALITY → can we do this?
- **NEW Phase 2.75: PREPARATION_GATE → are we ready?**

---

## PHASE 4: REFUSE PREMATURE OR UNJUSTIFIED EXECUTION

**Principle:** No guessing. No "good enough." No vibes. No execution
without defined mastery criteria.

### What gets refused

| Condition | Response |
|-----------|----------|
| Mastery definition missing | FAIL CLOSED |
| Success criteria undefined | FAIL CLOSED |
| Evidence state = UNSUPPORTED for any load-bearing claim | FAIL CLOSED |
| Toolbox reality undeclared | FAIL CLOSED |
| CRITICAL MMD findings open | FAIL CLOSED |
| DecisionRecord missing for architectural choice | FAIL CLOSED |
| Claim strength = SOURCE-LIMITED used as enforcement predicate | FAIL CLOSED |

### How This Maps to the Decision Engine

The Decision Engine (from the OS workspace) selects architectural
patterns. But it currently does keyword matching. Under this spec:

1. **Constraint extraction** replaces keyword matching
   - Parse MASTERY_DEFINITION for constraints
   - Parse R2.5 for environment constraints
   - Parse CLAIM_REGISTRY for domain constraints

2. **Candidate enumeration** replaces "first match"
   - Pattern catalog provides candidates
   - SEE provides evidence for/against each candidate

3. **Elimination with reasons** replaces silent selection
   - Each rejected candidate gets a rejection reason in DecisionRecord
   - Each selected candidate gets evidence citations

4. **DecisionRecord is mandatory**
   - Schema: `.codex/schemas/DECISION_RECORD.schema.json`
   - No architectural choice without one

This is how you get Feistel-cipher-quality choices: tight constraints
from Phase 1, exhaustive candidates from the pattern catalog, and
evidence-based elimination from SEE.

---

## PHASE 5: EXECUTE ONLY WHEN JUSTIFIED

**Principle:** With traceability. With receipts. Against explicit
success criteria.

### Execution Requirements

| Requirement | Mechanism |
|-------------|-----------|
| Traceability | Every output traces to a claim, every claim traces to evidence |
| Receipts | TURN_RECEIPT.json with SHA-256 of every artifact |
| Success criteria | Compare outputs to MASTERY_DEFINITION success criteria |
| CDR compliance | Every decision has WHY, constraints, failure modes |
| Pattern compliance | Architectural patterns validated post-execution |

### MPP Mapping
- Phase 3: BUILD (CDR-governed construction)
- Phase 4: EVALUATE (read-only review against mastery criteria)
- Phase 5: REWRITE (fix enumerated defects only, max 2 iterations)
- Phase 6: SELF-VERIFICATION (mechanical checks)
- Phase 7: TURN_RECEIPT (execution record)

### Mastery Comparison (NEW)

During EVALUATE (Phase 4), the evaluator MUST compare outputs against
the mastery definition's success criteria. Each criterion gets a verdict:

- **MET** — output satisfies the criterion with evidence
- **PARTIALLY_MET** — output addresses the criterion but incompletely
- **NOT_MET** — output does not satisfy the criterion
- **NOT_APPLICABLE** — criterion doesn't apply to this output

If any success criterion is NOT_MET and the criterion was marked as
REQUIRED → the evaluation FAILS and REWRITE must address it.

---

## PHASE 6: ASSIMILATE OUTCOMES

**Principle:** No resets. No silent drift. No re-learning what was
already paid for.

### What gets assimilated

| Output | Where It Goes | How It's Preserved |
|--------|--------------|-------------------|
| Decisions made | Decision ledger | DELTA_LEDGER with DecisionRecords |
| Defects found | MMD findings | MMD_REPORT with resolution tracking |
| Evidence gathered | Source ledger | SOURCE_LEDGER.json (SEE) |
| Lessons learned | Constraint promotions | Lessons → new invariants or policies |
| Mastery definitions | Mastery archive | Reusable for similar future tasks |

### The Assimilation Loop (NEW)

After every governed session:

1. **Compare results to mastery bar**
   - Were all success criteria MET?
   - If not, what was the gap?

2. **Perform RCA on deltas**
   - What changed from expectation?
   - Root cause of each delta

3. **Promote lessons to constraints**
   - If a failure mode was discovered → add to MMD category list
   - If an assumption was wrong → add to forbidden assumptions
   - If a pattern worked → strengthen evidence in pattern catalog
   - If a pattern failed → add to `forbidden_when` in pattern catalog

4. **Preserve decisions for future tasks**
   - DecisionRecords persist across sessions
   - MASTERY_DEFINITIONs persist and can be referenced
   - Delta ledgers accumulate, never reset

5. **Accumulate intelligence**
   - Cross-session memory grows monotonically
   - No resets — new sessions read prior sessions' receipts
   - No silent drift — staleness detection on all artifacts
   - No re-learning — SEE queries are cached in SOURCE_LEDGER

### Lesson Promotion Schema (NEW)

When a lesson is learned, it gets promoted through levels:

```
OBSERVATION → HYPOTHESIS → CONSTRAINT → INVARIANT
```

- **OBSERVATION**: Something happened (recorded in delta ledger)
- **HYPOTHESIS**: We think X causes Y (recorded with claim_strength)
- **CONSTRAINT**: We now require X (added to policies, claim_strength = DESIGN-CHOICE)
- **INVARIANT**: X is mechanically checked (added to INVARIANT_REGISTRY with checker)

Each promotion requires evidence. No silent upgrades.

---

## Artifact Map

### Existing (Built)

| Artifact | Phase | Status |
|----------|-------|--------|
| SEE_ENGINE_v1.md | 1, 3 | VALIDATED |
| CLAIM_STRENGTH_v1.md | 1 | ENFORCED |
| SEMANTIC_STATE_v1.md | 1 | VALIDATED |
| MMD_ENGINE_v2.md + run_mmd_gate.py | 2 | ENFORCED |
| TOOLBOX_REALITY.schema.json + gate | 3, 4 | ENFORCED |
| SUPER_PROMPT_v2.3.md (MPP) | ALL | VALIDATED |
| CDR_v2.md | 5 | VALIDATED |
| RRP_v1.md | 5 | VALIDATED |
| DELTAGATE_v1.md | 4, 6 | VALIDATED |
| INVARIANT_REGISTRY.json | ALL | ENFORCED |
| ARTIFACT_MATURITY.json | ALL | ENFORCED |
| DELTA_LEDGER_20260208.json | 6 | VALIDATED |
| MB_PATTERN_CATALOG__v1.json | 4, 5 | In OS workspace |
| Decision Engine code | 4, 5 | In OS workspace |

### New (Needed)

| Artifact | Phase | What It Does |
|----------|-------|-------------|
| MASTERY_DEFINITION.schema.json | 1 | Schema for "what does world-class look like?" |
| DECISION_RECORD.schema.json | 4, 5 | Schema for architectural decisions with rejections |
| LESSON_PROMOTION.schema.json | 6 | Schema for observation → hypothesis → constraint → invariant |
| run_preparation_gate.py | 3 | Gate: refuse execution without mastery definition |
| MASTERY_COMPARISON.schema.json | 5 | Schema for comparing outputs to mastery criteria |

---

## The Core Loop

```
   ┌──────────────────────────────────────────────────────┐
   │                                                      │
   ▼                                                      │
TASK ──→ SURFACE ──→ DETECT ──→ PREPARE ──→ REFUSE/ADMIT  │
                                                │         │
                                           (admitted)     │
                                                │         │
                                           EXECUTE        │
                                                │         │
                                           ASSIMILATE ────┘
                                                │
                                           (lessons become
                                            constraints for
                                            future tasks)
```

Every pass through the loop makes the system smarter.
Every failure teaches something that prevents the same failure next time.
Nothing is lost. Nothing drifts. Nothing gets re-learned.

## Versioning

This is MB_MASTER_SPEC v1.0. Changes require DeltaGate admission.
