# Pattern Study: RATE_LIMITER_THUNDERING_HERD
**Status:** NEEDS_RESEARCH
**Assigned:** unassigned
**Protocol:** `mpp/patterns/STUDY_PROTOCOL.md`
**Target card:** `mpp/patterns/cards/RATE_LIMITER_THUNDERING_HERD.json`

---

## Phase 1 — Pattern Identity

**Code shape:**
A rate limiter (token bucket, fixed window, sliding window) enforces a request ceiling.
When clients are rejected, they retry — either immediately or after a fixed backoff.
If many clients are rejected simultaneously (at a window boundary or after a shared
block), they retry in a synchronized wave. The downstream receives a spike exactly
at the moment the limit resets or the block expires.

**Failure hypothesis:**
Rate limiting is intended to protect a downstream resource. But if rejected clients
retry at the same moment (window reset, shared sleep duration, synchronized backoff),
the retry wave is larger than the original rate-limited load — because it combines
the clients that were rejected *plus* any new clients that arrived during the block.
The protection mechanism amplifies the peak load it was meant to prevent.

**Likely pattern class:** `architectural`

**Working name:** `RATE_LIMITER_THUNDERING_HERD`

**Is this covered by an existing card?**
`RETRY_AMPLIFICATION` covers multi-layer retry fan-out but not the specific mechanism
of synchronized retry at a rate limiter window boundary. This is a distinct failure
shape: the synchronization source is the window reset, not upstream retries.

---

## Phase 2 — Targeted Research Directions

### Q1 — Activation condition
Two specific sub-cases to research separately:

1. **Fixed-window thundering herd:** All clients are rate-limited at the same
   window boundary (e.g., all blocked from :00 to :01, all retry at :01:000).
   The window reset is the synchronization event.

2. **Retry-synchronized thundering herd:** Clients receive a 429 with a
   `Retry-After` header that gives the same timestamp to all blocked clients.
   They all retry at exactly that timestamp.

Research which sub-case is more common and whether sliding window limiters
prevent the first but not the second.

### Q2 — Causal mechanism
The mechanism involves the math of synchronized arrival. Research:
- If N clients are blocked and retry simultaneously, and the rate limit allows R
  requests per window, what fraction of the retry wave passes through?
- The remainder gets blocked again — but now they're synchronized *with* the new
  arrivals, creating a standing wave of synchronized retries.

Find the mathematical description of this in the literature. It's related to the
general thundering herd problem but has a rate-limiter-specific shape.

### Q3 — Signal sequence
The invisible phase here is the rate limit itself appearing to work. Traffic drops
to the limit. Health looks good. The spike comes at window reset — look for the
specific metric shape: a flat line followed by an instantaneous vertical spike,
repeating at window intervals.

**Find:** what does this look like in a requests-per-second graph? Can you distinguish
it from a legitimate traffic surge without knowing the window interval?

### Q4 — Why it's invisible
The rate limiter is doing its job — it's rejecting excess traffic. The problem is
what happens *after* the rejection. Monitoring shows the rate limiter is working
(429 rate is high, protected service is not overwhelmed). The spike arrives after
the monitoring confidence interval — it looks like new traffic, not deferred traffic.

**Find a postmortem** where a rate limiter caused or failed to prevent a downstream
spike. Likely candidates: API gateway thundering herd incidents, CDN edge cache
synchronized misses (related pattern but strong overlap).

### Q5 — Threshold
The threshold is a function of: number of synchronized clients × retry rate.
Research: at what client count does jitter become insufficient and coordination
(e.g., exponential backoff with full jitter) become necessary?

AWS has published specific guidance on this — the "Full Jitter" paper/blog is the
canonical source. Find the threshold numbers from their data.

### Q6 — Diagnostic
The diagnostic should detect synchronized retry waves before they hit the downstream.
Research: can you detect this from the rate limiter's 429 response timing distribution?
If 429s arrive in a burst at window boundaries and retry requests arrive in a burst
immediately after, that's the signature.

**Find:** what metric or log pattern definitively identifies synchronized retries
vs. organic traffic spikes.

### Q7 — Countermeasures
Research direction: the fix is jitter, but the details matter.
- **Full jitter** (AWS) vs. **decorrelated jitter** vs. **exponential backoff without jitter** —
  find the quantitative comparison
- **Sliding window limiters** prevent the fixed-window synchronization — research
  whether they also prevent the `Retry-After` synchronization
- **Client-side backoff with uniquely seeded randomness** — what prevents synchronized
  random seeds (e.g., all clients start at the same time, all seed from the same epoch)?

### Q8 — Trigger shapes
Draft trigger shapes:
- "Rate limiter that returns a 429 with a fixed or computed Retry-After header"
- "Client that retries on 429 with a fixed sleep (no jitter)"
- "Fixed window rate limiter with many clients sharing the same limit bucket"
- "Batch job or cron that runs on many instances simultaneously and calls a rate-limited API"
- "SDK or library with built-in rate limit handling that uses the same retry strategy across all instances"

---

## Known Incidents to Search

- AWS architecture blog — "Exponential Backoff and Jitter" (Marc Brooker, 2015) — canonical
- Cloudflare engineering blog — they have described thundering herd scenarios at the edge
- Google SRE book — Chapter 22 discusses cascading failures from synchronized retries
- Stripe engineering — they operate a rate-limited API at scale and have documented retry behavior
- Redis blog — sliding window rate limiter implementation and thundering herd avoidance

## Open Questions for Adversarial Phase

1. Does sliding window rate limiting fully prevent this pattern, or just reduce its magnitude?
2. If clients use exponential backoff with jitter but all start retrying at the same time
   (e.g., a deploy causes all instances to start simultaneously), does the jitter actually
   desynchronize them across window boundaries?
3. Is `Retry-After` actually harmful, or does it help if clients add jitter to it?
   Research both positions.

---

## Ready to Run?

When you pick this up:
1. Read `mpp/patterns/STUDY_PROTOCOL.md` — full protocol
2. Answer all 8 research questions with cited sources
3. Have a different reviewer run the adversarial check (Phase 3)
4. Write `mpp/patterns/cards/RATE_LIMITER_THUNDERING_HERD.json` using the template
5. Run the registry to validate: `python -c "from mpp.patterns import PatternRegistry; r = PatternRegistry(); print(r.render_index())"`
