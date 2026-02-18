# MetaBlooms — Claude Standing Instructions

This repo contains the MPP (Mandatory Process Pipeline) and GVN (Governance Layer).
Specs live in `mpp/MPP_SPEC.md` and `mpp/governance/GOV_SPEC.md`.
Entry point: `mpp/governance/gov_pipeline.py`.

---

## How to Work Here

Every change goes through G0 → PRVE → SEE → G1 → MMD → CDR → ECL → G2 → TEST → G3.
Do not skip stages. Do not soft-fail gates. If a stage blocks, loop back to the earliest
failing stage — not just the last one.

When writing or reviewing code in this repo, apply the failure patterns and quality gates
below as active checks, not background reading.

---

## Quality Gates — Apply These During Every Coding Task

### G0 — Context Brief (before starting)
Before writing anything, confirm:
- Who specifically needs this, and what frustration does it remove?
- What does done look like — specifically enough to test right now?
- What constraint would I never infer from the code alone?

If any answer is vague, stop and get it before proceeding. Gate artifact: `gov/CONTEXT_BRIEF.md`.

### G1 — Adversarial MMD (before CDR locks the plan)
A different person than the researcher answers all six:
1. What malicious or careless input breaks this?
2. What breaks at 10x load, data size, or concurrency?
3. What does a distracted junior engineer do wrong on first use?
4. Which research claim is most likely false? What happens if it is?
5. What existing system will this touch that isn't mentioned?
6. What is so obvious the author forgot to state it?

Same reviewer as research = blocked. Gate artifact: `gov/ADVERSARIAL_MMD.md`.

### G2 — Behavior Review (before tests run)
A third perspective checks:
1. Point to the test that catches the most expensive production failure. Does it exist?
2. Which test would still pass if the core logic were completely wrong?
3. What user-facing behavior has no coverage?

INSUFFICIENT verdict stops the TEST gate. Gate artifact: `gov/BEHAVIOR_REVIEW.md`.

### G3 — Governor (after every run)
Checks cross-run health:
- Adversarial reviewer finding zero gaps every time → gaming signal
- Research dossiers getting shorter over time → drift signal
- Coverage always landing at threshold ± 1% → gaming signal

CRITICAL signals block the next run. Artifact: `gov/GOVERNOR_LOG.md` (append-only).

---

## Failure Patterns — The Pattern Library

Patterns live in `mpp/patterns/`. Every pattern is a structured JSON card.

**When you see one of these code shapes, check the pattern library before writing:**

| Code shape | Pattern to check |
|---|---|
| Retry around an external call | `RETRY_AMPLIFICATION`, `NONIDEMPOTENT_RETRY` |
| Message queue consumer | `QUEUE_LAG_SILENT`, `DLQ_ACCUMULATION` |
| Cache read/write/invalidate | `CACHE_INVALIDATION_RACE` |
| Any shape with no card | Run `mpp/patterns/STUDY_PROTOCOL.md` |

**Look up a pattern:**
```python
from mpp.patterns import PatternRegistry
registry = PatternRegistry()

# by id
card = registry.get("RETRY_AMPLIFICATION")
print(registry.render_card(card))

# by code shape
matches = registry.find_by_trigger("retry loop around an API call")

# full index
print(registry.render_index())
```

**Adding a new pattern:** Follow `mpp/patterns/STUDY_PROTOCOL.md`.
New cards start as `DRAFT` and only become `ACTIVE` after G2 passes.

**Active patterns as of 2026-02-18:**

- `RETRY_AMPLIFICATION` — Retry amplification in call chains `[architectural]`
- `NONIDEMPOTENT_RETRY` — Non-idempotent retry on stateful operations `[operational]`
- `QUEUE_LAG_SILENT` — Sustained queue lag without a traffic spike `[architectural]`
- `DLQ_ACCUMULATION` — Dead letter queue accumulation from persistent errors `[operational]`
- `CACHE_INVALIDATION_RACE` — Cache invalidation race without versioning `[data]`

**Patterns with no card yet (study triggers):**
Connection pool exhaustion, distributed transaction rollback gaps, rate limiter thundering herd,
leader election split-brain, batch job memory pressure, fan-out amplification.
