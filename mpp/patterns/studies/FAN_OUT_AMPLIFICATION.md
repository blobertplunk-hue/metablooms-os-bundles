# Pattern Study: FAN_OUT_AMPLIFICATION
**Status:** NEEDS_RESEARCH
**Assigned:** unassigned
**Protocol:** `mpp/patterns/STUDY_PROTOCOL.md`
**Target card:** `mpp/patterns/cards/FAN_OUT_AMPLIFICATION.json`

---

## Phase 1 — Pattern Identity

**Code shape:**
A single user action, API request, or event triggers writes or reads to N downstream
services or data stores, where N > 1 and the downstream calls are made in parallel
(or sequentially with no short-circuit). Each downstream has its own error rate and
latency. The overall operation succeeds only if all N calls succeed, or partially
succeeds with undefined behavior if some succeed and some fail.

**Failure hypothesis:**
Even with individually reliable services (99.9% SLO), a fan-out to N=10 services
has an overall success rate of `0.999^10 = 99.0%`. At N=50, it drops to 95.1%.
This is not a theoretical failure — it is a mathematically guaranteed degradation
of the user-facing success rate as a function of fan-out width. Most systems are
not designed with this math in mind, so the failure surprises the team when load
grows and fan-out width increases.

A secondary failure mode: one slow downstream in the fan-out delays the entire
operation (if results are gathered with `wait_all`). The latency of the overall
operation is `max(latency_1, latency_2, ..., latency_N)`, not the average.

**Likely pattern class:** `architectural`

**Working name:** `FAN_OUT_AMPLIFICATION`

**Is this covered by an existing card?**
`RETRY_AMPLIFICATION` covers retry fan-out across layers. This pattern covers
a different shape: a single layer that fans out to N parallel targets. The
failure mechanism and countermeasures are distinct. This needs its own card.

---

## Phase 2 — Targeted Research Directions

### Q1 — Activation condition
Two sub-cases with different activation paths:

1. **Error rate compounding:** As fan-out width N grows (more downstream services
   added over time), the compound error rate grows even with stable per-service SLOs.
   The system degrades without any individual service worsening.

2. **Latency tail amplification:** The `max()` latency of N parallel calls grows
   with N because the probability of hitting at least one tail-latency response
   increases with fan-out width. At N=100, even a 1% tail becomes nearly certain.

Research: is there a standard name for these two sub-cases in the distributed systems
literature? Are they typically treated as the same pattern or different ones?

### Q2 — Causal mechanism
The mechanism for error rate compounding is the independence multiplication:
if each downstream has error rate `e`, then the fan-out success rate is `(1-e)^N`.

The mechanism for latency tail is `P(max latency > T) = 1 - (1 - P(single call > T))^N`.

Research: find the original source for these formulas in the context of distributed
systems. Jeff Dean's work at Google on tail latency is the canonical starting point.
Also research: are these failures independent (required for the formula to hold)?
If downstream services share infrastructure (same DB, same network), they are not
independent, and the formula underestimates the failure rate.

### Q3 — Signal sequence
The invisible phase for error rate compounding can be long — as the team adds more
downstream integrations, each addition degrades overall reliability slightly. No
single addition triggers an alert. The degradation accumulates.

For latency tail, the invisible phase is at low load: with few requests per second,
the probability of hitting N simultaneous slow responses is low. At high load, it
becomes nearly certain.

**Find:** what does the p99 latency graph look like for a fan-out operation as
request rate increases? Is there a specific shape (transition from stable to
monotonically increasing) that identifies this pattern?

### Q4 — Why it's invisible
Each downstream service reports its own SLO as met. The upstream service's error
rate is attributed to "flakiness" or "intermittent downstream issues" rather than
to the structural math of fan-out. No dashboard shows the compound success rate
across all downstream calls as a single metric.

**Find a postmortem** where fan-out error compounding was the root cause but was
initially misdiagnosed as a specific downstream failure.

### Q5 — Threshold
Research the mathematical threshold for each sub-case:
- Error compounding: at what fan-out width and per-service error rate does the
  compound error rate exceed typical user-facing SLOs (99.9%, 99.5%, 99%)?
- Latency tail: at what fan-out width does p99 latency of the fan-out exceed 3×
  the p99 latency of a single call (the point where the fan-out latency dominates)?

**Find:** the Jeff Dean / Google paper that first quantified tail latency amplification
and the specific numbers they found at Google's scale.

### Q6 — Diagnostic
The diagnostic needs to surface the compound success rate, not the per-service
success rate. Research: how do you instrument a fan-out operation so that:
1. You can see the success rate of the entire fan-out as a single metric
2. You can see which downstream is failing most often (to prioritize fixes)
3. You can see the latency distribution at the fan-out level, not just per-service

**Find:** how do distributed tracing tools (Jaeger, Zipkin, AWS X-Ray) represent
fan-out operations, and whether their built-in views surface the tail latency
amplification.

### Q7 — Countermeasures
Research direction: the fundamental countermeasure is to redesign the fan-out to
not require all N services to succeed for the user to receive a response. Specific
approaches:

- **Partial success semantics:** define what the operation returns when K of N
  downstream calls succeed. Return the result, note the failures. (Requires a
  product decision about what partial success means to the user.)
- **Hedged requests:** send the same request to multiple instances of the same
  service; use the first response; cancel the rest. (Reduces tail latency but
  increases load.)
- **Scatter-gather with timeout:** send all N calls simultaneously; collect results
  until a deadline; return whatever arrived. (Requires defining behavior for
  missing responses.)
- **Write fan-out to a queue:** instead of writing to N services synchronously,
  write one event; let N services consume it asynchronously. (Decouples the
  user-facing latency from the fan-out, but creates eventual consistency.)

Research which approach is most commonly used at companies with wide fan-outs
(social networks, notification systems, recommendation engines).

### Q8 — Trigger shapes
Draft trigger shapes:
- "Parallel calls to N downstream services where all must succeed before returning"
- "`asyncio.gather`, `Promise.all`, or `CompletableFuture.allOf` with more than 3 targets"
- "Notification service that delivers to N channels (email, SMS, push, in-app) per user action"
- "Write-through to N data stores (primary DB + search index + cache + analytics) in a single request handler"
- "GraphQL resolver that fans out to N data sources per query"

---

## Known Incidents to Search

- Jeff Dean & Luiz André Barroso — "The Tail at Scale" (2013, Communications of the ACM) —
  the canonical source for tail latency amplification math
- Facebook/Meta engineering — their social graph fan-out is the most studied example
  at scale; search their engineering blog for fan-out architecture discussions
- Twitter engineering — "Handling Five Billion Sessions a Day – In Real Time" and related
  fan-out architecture posts
- Discord engineering — "How Discord Stores Trillions of Messages" discusses fan-out
  to read replicas and the latency implications
- Netflix engineering blog — their API gateway fan-out to microservices is well-documented

## Open Questions for Adversarial Phase

1. If downstream services are not independent (shared infrastructure), the compound
   error rate formula breaks. Is the correlated failure case better or worse than
   the independent case? (Worse: if one fails, all might fail simultaneously.)
2. Hedged requests reduce latency but increase load. At what fan-out width and load
   level does hedging cause the downstream services to exceed their capacity,
   creating a worse failure than the tail latency it was trying to prevent?
3. Is "write fan-out to a queue" actually a countermeasure for this pattern, or does
   it just move the fan-out to the consumer side and introduce `DLQ_ACCUMULATION`?

---

## Ready to Run?

When you pick this up:
1. Read `mpp/patterns/STUDY_PROTOCOL.md` — full protocol
2. Answer all 8 research questions with cited sources
3. Have a different reviewer run the adversarial check (Phase 3)
4. Write `mpp/patterns/cards/FAN_OUT_AMPLIFICATION.json` using the template
5. Run the registry to validate: `python -c "from mpp.patterns import PatternRegistry; r = PatternRegistry(); print(r.render_index())"`
