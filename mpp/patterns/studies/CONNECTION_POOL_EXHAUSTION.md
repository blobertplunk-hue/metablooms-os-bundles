# Pattern Study: CONNECTION_POOL_EXHAUSTION
**Status:** NEEDS_RESEARCH
**Assigned:** unassigned
**Protocol:** `mpp/patterns/STUDY_PROTOCOL.md`
**Target card:** `mpp/patterns/cards/CONNECTION_POOL_EXHAUSTION.json`

---

## Phase 1 — Pattern Identity

**Code shape:**
Any code that acquires a connection from a bounded pool (database connection pool,
HTTP client pool, thread pool) to serve a request, then returns it on completion.
Specifically dangerous when: pool size is fixed, request latency is variable, and
no backpressure prevents new requests from arriving while the pool is drained.

**Failure hypothesis:**
Pool is fully checked out. New requests queue waiting for a connection. If queue
length is unbounded, memory grows. If queue has a timeout, requests start failing
with "connection timeout" errors that look like a database problem — not a pool
problem. Health checks pass because the pool exists; they don't check wait time.

**Likely pattern class:** `operational`

**Working name:** `CONNECTION_POOL_EXHAUSTION`

**Is this covered by an existing card?**
No. `RETRY_AMPLIFICATION` touches adjacent territory (retries worsen exhaustion)
but does not describe pool exhaustion as the root cause.

---

## Phase 2 — Targeted Research Directions

### Q1 — Activation condition
Look for: what is the specific state that tips the pool from "busy" to "exhausted"?
Is it always 100% checkout rate, or does it happen before that (due to slow connection
acquisition under contention)?

**Recommended sources:**
- HikariCP (Java) docs on pool sizing and deadlock detection — HikariCP has the most
  rigorous public writing on why pool sizing is counterintuitive
- PgBouncer documentation on pool modes (session vs. transaction vs. statement)
- Shopify engineering blog — they have written about Rails DB pool exhaustion at scale

### Q2 — Causal mechanism
The mechanism has two failure paths worth distinguishing:
1. **Slow query path:** queries slow down (e.g., missing index, lock contention),
   connections stay checked out longer, pool drains, new requests queue/fail
2. **Traffic spike path:** request rate rises, each request needs a connection,
   pool drains before queries complete, new requests queue/fail

Both lead to the same observable state. The distinction matters for the fix.

### Q3 — Signal sequence
The invisible phase is the hardest one here. The key question: what does a
pool that is 95% checked out look like vs. a pool that is 100% checked out?
Look for the specific metric that appears *before* the first timeout fires.

**Look for:** connection wait time histograms, active vs. idle connection ratios,
queue depth metrics in HikariCP/c3p0/pgbouncer. These exist but are rarely alarmed on.

### Q4 — Why it's invisible
The standard health check for database connectivity acquires one connection and
releases it. This passes even when 99 of 100 connections are checked out.
Application-level metrics show "database errors" which are misattributed to
the database rather than the pool.

**Find a postmortem** where the DB was blamed but the root cause was pool exhaustion.
Likely candidates: Rails app postmortems, Django DB pool issues, Node.js pg pool.

### Q5 — Threshold
Pool exhaustion is a function of: `(average_query_time_ms x requests_per_second) / 1000`.
If this exceeds `pool_size`, you will exhaust. Research the formula and find the
real-world numbers where teams discovered they were running too small.

Look for: GitHub engineering, Heroku Postgres documentation on pool sizing recommendations.

### Q6 — Diagnostic
The diagnostic should be executable by an on-call engineer in under 5 minutes.
Look for: how do you query the current pool state in HikariCP, PgBouncer, SQLAlchemy?
What is the specific command that shows active vs. idle vs. waiting connections?

`SELECT * FROM pg_stat_activity` is the starting point — but the diagnostic
should be specific to the pool layer, not just the database.

### Q7 — Countermeasures
Research direction: the counterintuitive result from HikariCP is that *smaller pools
are often better* because larger pools increase DB-side lock contention. The fix is
not always "increase pool size."

Also research: connection multiplexers (PgBouncer in transaction mode), circuit
breakers that open when wait time exceeds threshold, and async/non-blocking
connection patterns that don't hold connections during I/O waits.

### Q8 — Trigger shapes
Draft trigger shapes to validate during research:
- "ORM or database client initialized with a max_connections or pool_size parameter"
- "Request handler that queries a database without explicit connection timeout"
- "Async task queue (Celery, Sidekiq) with a worker count that exceeds DB pool size"
- "Service behind a load balancer where each instance has its own pool (pool fragmentation)"

---

## Known Incidents to Search

- Basecamp / HEY — Ruby on Rails DB pool issues are well-documented
- Heroku Postgres documentation has explicit pool sizing postmortems
- GitHub engineering blog has discussed connection pool exhaustion under deploy load
- Discord engineering — "How Discord Stores Trillions of Messages" mentions connection handling

## Open Questions for Adversarial Phase

1. Is connection pool exhaustion always caused by slow queries, or can connection
   *acquisition* itself be slow under contention (acquiring a connection from the pool
   becomes serialized)?
2. What is the interaction with ORMs that open connections lazily vs. eagerly?
3. Does PgBouncer in session mode make this worse (by holding the server connection
   for the whole client session) or better (by abstracting the pool)?

---

## Ready to Run?

When you pick this up:
1. Read `mpp/patterns/STUDY_PROTOCOL.md` — full protocol
2. Answer all 8 research questions with cited sources
3. Have a different reviewer run the adversarial check (Phase 3)
4. Write `mpp/patterns/cards/CONNECTION_POOL_EXHAUSTION.json` using the template
5. Run the registry to validate: `python -c "from mpp.patterns import PatternRegistry; r = PatternRegistry(); print(r.render_index())"`
