# Pattern Study Protocol
**Version:** 1.0.0
**Owner:** MetaBlooms MPP Pattern Library
**When to run:** Any time you encounter a code shape that has no matching pattern card, or a known pattern that needs a new countermeasure or source.

---

## When Does This Trigger?

Run this protocol when you encounter any of the following code shapes and no existing pattern card fully covers it:

| Shape | Check first |
|---|---|
| Retry logic around an external call | `RETRY_AMPLIFICATION`, `NONIDEMPOTENT_RETRY` |
| Message queue consumer | `QUEUE_LAG_SILENT`, `DLQ_ACCUMULATION` |
| Cache read/write/invalidate | `CACHE_INVALIDATION_RACE` |
| Connection pool to a DB or service | (no card yet — study trigger) |
| Distributed transaction across services | (no card yet — study trigger) |
| Rate limiter or token bucket | (no card yet — study trigger) |
| Leader election or distributed lock | (no card yet — study trigger) |
| Batch job reading from a large dataset | (no card yet — study trigger) |
| Fan-out to multiple downstream services | (no card yet — study trigger) |

If no card exists for the shape you're looking at: **run this protocol before writing the code.**

---

## Phase 1 — Name the Pattern

Answer these before researching anything:

1. **What is the code shape?** (one sentence — describe what the code does structurally, not what it's for)
2. **What is the failure mode you're worried about?** (one sentence — what goes wrong)
3. **Is this a new pattern or a variant of an existing one?** Check `pattern_registry.py` first: `registry.find_by_trigger("<your code description>")`. If an existing card covers it, stop here and reference the card.

If this is new, give it a working name and continue.

---

## Phase 2 — Research (SEE-Style)

For each of these 8 questions, find at least one external source (postmortem, engineering blog, documentation, or published research). **Do not answer from memory alone.**

### Q1 — Activation condition
What is the specific precipitating event? Not "it fails" but what specific change in input, load, or system state crosses from safe to failing?

*Required: cite one source that describes this activation condition in a real system.*

### Q2 — Causal mechanism
Write the failure as a numbered step sequence. Each step must cause the next. If you can't connect two steps causally, you have a gap — research it.

*Required: the mechanism must be specific enough that an engineer could reproduce it in a test.*

### Q3 — Signal sequence
What does monitoring see at each phase: invisible, first anomaly, escalation, customer impact? Be specific: which metric, which log line, which alert threshold?

*Required: at least one phase must be invisible to standard monitoring — if everything is visible, it's not a pattern worth documenting.*

### Q4 — Why it's invisible
What specific assumption or monitoring gap causes this to look healthy when it isn't?

*Required: cite one real example (postmortem or engineering blog) where this invisibility caused a production incident.*

### Q5 — Threshold
At what approximate load, rate, or concurrency does the pattern activate? Include the reasoning — don't just guess.

*Required: must be quantified enough to set an alert threshold from.*

### Q6 — Diagnostic
What is the specific question an on-call engineer asks, or the specific query they run, to confirm or rule out this pattern?

*Required: specific enough to execute. "Check the logs" is not a diagnostic.*

### Q7 — Countermeasures
List at least 3 concrete actions that prevent or mitigate this pattern. Each must be:
- Specific (names a technology, a policy, or a test)
- Actionable (an engineer can implement it this sprint)
- Ordered by implementation cost (cheapest first)

*Required: at least one countermeasure must be a test that would catch the failure.*

### Q8 — Trigger shapes
List 3–5 code shapes that should trigger checking this pattern. Plain English. Specific enough that a code reviewer reading a PR would recognize the shape.

---

## Phase 3 — Adversarial Check (before writing the card)

A different reviewer (not the researcher) answers these before the card is drafted:

1. **Is the mechanism actually causal?** Could the same symptoms arise from a different cause not described in the card?
2. **Is the threshold realistic?** Is the number based on evidence or intuition?
3. **Are the countermeasures sufficient?** Could a system implement all of them and still hit the failure?
4. **Is there an existing card this should merge with** rather than creating a new one?
5. **Is the diagnostic actually executable?** Test it: can you write a test that would pass if the diagnostic succeeds?

Any "no" answer means the card goes back to Phase 2 for that question.

---

## Phase 4 — Write the Card

Use the template at `mpp/patterns/cards/TEMPLATE.json`. All fields are required.

```
mpp/patterns/cards/<PATTERN_ID>.json
```

Validate against the schema before submitting:
```
python -c "from mpp.patterns.pattern_registry import PatternRegistry; r = PatternRegistry(); print(r.render_card(r.get('<PATTERN_ID>')))"
```

If the registry loads without error and renders the card correctly, proceed.

---

## Phase 5 — MPP Review

A new pattern card is a code change. It goes through MPP:

1. **G0** — Context brief: who needs this pattern and what production failure does it prevent?
2. **PRVE** — Research dossier: list all 8 research questions and their sources.
3. **SEE** — Citation map: every claim in the card must cite a source.
4. **G1** — Adversarial MMD: the Phase 3 adversarial check, formalized.
5. **CDR** — Delta proposal: the new card file + any updates to the index.
6. **ECL** — Not applicable to JSON cards. Skip for cards only. Required if `pattern_registry.py` is modified.
7. **G2** — Behavior review: does a test exist that validates the diagnostic is executable?
8. **TEST** — `tests/test_pattern_registry.py` must pass with the new card loaded.

**Status starts as DRAFT. Changes to ACTIVE only after G2 passes.**

---

## Evidence Standards

A source is valid if it is:
- A production postmortem with a named incident date and owner
- An engineering blog from a named company describing a real system
- Official documentation from a technology (e.g., AWS, Kafka, Redis)
- Published research with an abstract and methodology

A source is **not** valid if it is:
- An anonymous blog post with no named author or company
- A Stack Overflow answer without a cited primary source
- Personal memory or "everyone knows this"

---

## Card Template Reference

See `mpp/patterns/cards/TEMPLATE.json` for the full template.
See `mpp/patterns/PATTERN_SCHEMA.json` for the schema.
See `mpp/patterns/pattern_registry.py` for field validation logic.

---

## Growing the Library

The pattern library is a living artifact. After every production incident:

1. Check if an existing card predicted it. If yes, update `last_reviewed` and add any new countermeasures found.
2. If no card predicted it, run this protocol to document the new pattern.
3. If a card predicted it but the diagnostic or countermeasures failed — that is a HIGH-severity gap. Update the card and run G3 Governor with a note.

The goal is that no production failure surprises us twice.
