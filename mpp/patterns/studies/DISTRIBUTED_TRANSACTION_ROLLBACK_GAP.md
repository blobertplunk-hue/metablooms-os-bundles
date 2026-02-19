# Pattern Study: DISTRIBUTED_TRANSACTION_ROLLBACK_GAP
**Status:** NEEDS_RESEARCH
**Assigned:** unassigned
**Protocol:** `mpp/patterns/STUDY_PROTOCOL.md`
**Target card:** `mpp/patterns/cards/DISTRIBUTED_TRANSACTION_ROLLBACK_GAP.json`

---

## Phase 1 — Pattern Identity

**Code shape:**
Any operation that writes to more than one independent data store or service, where
atomicity is required but is enforced by application logic rather than a database
transaction. Includes: saga patterns with compensating transactions, two-phase commit
implementations, event-sourced systems where projection updates are separate from
event writes, and microservices that must update their own DB and publish an event
in the same logical operation.

**Failure hypothesis:**
Step 1 of a multi-step write succeeds. A failure occurs before step 2. The rollback
(or compensating transaction) itself fails, or is never executed, or is executed
but partially — leaving the system in a state where different data stores disagree
about what happened. The system appears healthy (no ongoing errors) but is silently
inconsistent.

**Likely pattern class:** `data`

**Working name:** `DISTRIBUTED_TRANSACTION_ROLLBACK_GAP`

**Is this covered by an existing card?**
`NONIDEMPOTENT_RETRY` covers the retry angle on stateful operations, but does not
cover the case where the operation succeeds but the compensating rollback fails.
This is a different failure mode with a different signal sequence.

---

## Phase 2 — Targeted Research Directions

### Q1 — Activation condition
The activation is not the write failure — it is the *rollback failure* or *rollback gap*.
Research: what specific conditions cause a compensating transaction to fail?
- Network partition between services during rollback
- The compensating service is down when rollback is attempted
- The compensating transaction is not idempotent (so retrying it causes a second problem)
- No rollback is implemented because the author assumed the happy path

**Key distinction to research:** is this more common with sagas or with two-phase commit?
The answer changes the trigger shapes and countermeasures significantly.

### Q2 — Causal mechanism
The mechanism needs to cover both paths:
1. **No compensation path:** developer writes forward transaction but does not implement
   the compensating rollback because "that won't fail." Forward succeeds; error occurs;
   no rollback runs; data diverges.
2. **Compensation fails silently:** compensating transaction is attempted but fails
   (service down, network timeout); the error is logged but not retried; data diverges.

Research which path is more common in real incidents.

### Q3 — Signal sequence
The invisible phase is long here — potentially days. Research: what does a system
with silent data divergence look like before reconciliation detects it?

The customer impact phase is also unusual: the user may see correct data for some
time (until a read hits the inconsistent store) and then suddenly incorrect data,
with no error — just wrong information.

**Find:** monitoring approaches that detect cross-service consistency gaps before
reconciliation runs. This is the hardest part of this pattern to solve.

### Q4 — Why it's invisible
Each service reports success from its own perspective. Service A wrote successfully.
Service B did not, but Service A doesn't know that. No single error rate metric
captures the gap between them. Reconciliation often runs on a delay (hourly, daily)
so the gap is invisible in real-time.

**Find a postmortem** where a distributed write gap caused silent data corruption.
Candidates: payment systems, e-commerce order pipelines, any system with an
"outbox pattern" that was not implemented.

### Q5 — Threshold
Unlike most patterns, this one can occur on a single transaction — there is no
volume threshold. Research: does the rate of occurrence scale with write volume,
or is it a fixed probability per operation determined by the reliability of the
compensating transaction path?

### Q6 — Diagnostic
The diagnostic for this pattern is a consistency check, not a metric. Research:
how do teams implement cross-service consistency verification? Examples:
- Reconciliation jobs that compare records across services
- Event replay that re-derives state and compares to current state
- Checksums or version vectors across service boundaries

The diagnostic should be specific enough to be schedulable as a regular job.

### Q7 — Countermeasures
Research direction: the outbox pattern is the most commonly cited solution — write
the event to a local outbox table in the same DB transaction as the data write, then
have a separate process publish from the outbox. This reduces the gap to a single
DB transaction.

Also research: saga orchestration vs. choreography tradeoffs for rollback reliability.
Orchestration (central coordinator) makes rollback explicit; choreography (event-driven)
makes rollback harder to reason about.

**Find:** teams that implemented the outbox pattern and whether it actually eliminates
the gap or just shifts it.

### Q8 — Trigger shapes
Draft trigger shapes:
- "Write to database followed by publish to message queue in the same request handler"
- "Microservice that must update its own state AND notify another service of the change"
- "Saga with compensating transactions where compensation is not retried on failure"
- "Event sourcing system where projection update is separate from event commit"
- "Two-phase commit implementation without a coordinator timeout and recovery path"

---

## Known Incidents to Search

- Stripe engineering blog — they have extensive writing on distributed consistency
- AWS re:Invent talks on saga pattern at scale
- Martin Fowler's writing on the outbox pattern (foundational, citable)
- Uber engineering — their trip-state machine has been documented with consistency challenges
- Eventuate.io / Chris Richardson's work on the saga pattern (foundational)

## Open Questions for Adversarial Phase

1. Is two-phase commit strictly safer than sagas for rollback, or does it introduce
   its own gap (coordinator failure after PREPARE but before COMMIT)?
2. Does the outbox pattern actually eliminate the gap, or does it create a new one
   (outbox publisher fails after writing event but before downstream consumes)?
3. What is the correct recovery action when a compensating transaction is not idempotent
   and has already partially run?

---

## Ready to Run?

When you pick this up:
1. Read `mpp/patterns/STUDY_PROTOCOL.md` — full protocol
2. Answer all 8 research questions with cited sources
3. Have a different reviewer run the adversarial check (Phase 3)
4. Write `mpp/patterns/cards/DISTRIBUTED_TRANSACTION_ROLLBACK_GAP.json` using the template
5. Run the registry to validate: `python -c "from mpp.patterns import PatternRegistry; r = PatternRegistry(); print(r.render_index())"`
