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

## Failure Patterns — Check These When Reviewing Architecture or Code

When you see retry logic, queues, caches, or stateful operations, check the relevant pattern.

---

**PATTERN: Retry amplification in call chains**
CLASS: architectural
ACTIVATION: Transient failure in downstream service triggers retries at multiple upstream layers without coordination.
MECHANISM: Downstream service fails (e.g., timeout); immediate caller retries 3x; each retry may trigger further upstream retries if not idempotent; load multiplies (1 failure x 3 retries x layers); resource exhaustion cascades to healthy services.
SIGNAL SEQUENCE:
  - [invisible] Overall request rate appears normal or slightly elevated; success metrics mask underlying failures.
  - [first anomaly] Increased retry counts in logs or metrics.
  - [escalation] Latency spikes across services.
  - [customer impact] Widespread timeouts or errors.
LAG: minutes
THRESHOLD (estimated): 50% error rate over 10 seconds in downstream service; based on common circuit breaker defaults in SDKs like AWS boto3.
INVISIBLE BECAUSE: Retries configured per-service seem reasonable; no end-to-end simulation tests amplification; assumes failures are isolated.
DIAGNOSTIC: Does tracing show retry fan-out multipliers >1 across >2 layers in failure scenarios?
SOURCES: Temporal.io blog on error handling; AWS US-EAST-1 outage postmortem (retry storms at 3 retries without jitter).

---

**PATTERN: Non-idempotent retry on stateful operations**
CLASS: operational
ACTIVATION: Retry triggered on non-idempotent activity (e.g., payment) without key check.
MECHANISM: Transient failure (e.g., network); retry re-executes full operation; duplicates side effects (e.g., double charge); no rollback as state committed partially.
SIGNAL SEQUENCE:
  - [invisible] Retry metrics show "successes" on re-execution.
  - [first anomaly] Duplicate entries in audit logs or DB.
  - [escalation] Inconsistent state detected in reconciliation.
  - [customer impact] Overcharges or data corruption reported.
LAG: minutes to hours
THRESHOLD (estimated): >3 retries per operation without idempotency; reasoned as default max_attempts in policies.
INVISIBLE BECAUSE: Operation looks retry-safe in isolation; non-retryable errors not explicitly listed; works for transient-free paths.
DIAGNOSTIC: Are non-retryable error types (e.g., ValueError) defined in retry policies? Are idempotency keys required for state changes?
SOURCES: Temporal.io on golden rule of retries; iamraghuveer.com on idempotent consumers; Yandex incident story on retry budgets.

---

**PATTERN: Sustained queue lag without traffic spike**
CLASS: architectural
ACTIVATION: Consumer processing rate drops below inflow due to dependency latency or code inefficiency.
MECHANISM: Messages enqueue normally; consumers slow (e.g., dependency adds 100ms); lag accumulates as backlog; no backpressure; downstream derives stale state.
SIGNAL SEQUENCE:
  - [invisible] Queue accept rate and broker health green.
  - [first anomaly] Rising lag metric (backlog time > threshold).
  - [escalation] Increased retry rates if enabled.
  - [customer impact] Stale data or delayed actions.
LAG: hours
THRESHOLD (estimated): Lag >5 minutes sustained; based on typical monitoring for workflow delays.
INVISIBLE BECAUSE: No explicit errors; assumes constant processing time; partitioning hides skew in aggregate metrics.
DIAGNOSTIC: Does queue monitoring track per-partition lag and consumer throughput vs. inflow?
SOURCES: dev.to on queue growth and asynchronous failures; AWS Health Dashboard on increased queue processing time.

---

**PATTERN: DLQ accumulation from persistent errors**
CLASS: operational
ACTIVATION: Messages exceed retry limit due to unhandled cases (e.g., schema drift).
MECHANISM: Message fails processing; retries N times; moves to DLQ after max; DLQ grows as similar messages follow; main queue clears but errors persist.
SIGNAL SEQUENCE:
  - [invisible] Main queue depth and throughput normal.
  - [first anomaly] DLQ depth increase.
  - [escalation] Alert on DLQ growth if configured.
  - [customer impact] Lost or unprocessed events leading to inconsistencies.
LAG: hours to days
THRESHOLD (estimated): DLQ growth >10 messages/hour; based on signal-to-noise threshold for distinguishing isolated failures from systemic schema or contract issues.
INVISIBLE BECAUSE: DLQ seen as safety net, not signal; monitoring focuses on main queue; assumes all messages processable.
DIAGNOSTIC: Is DLQ depth alerted on >10 messages/hour, with sampling to classify error types?
SOURCES: dev.to on dead-letter queues; Temporal.io on error rates; Substack on Dead Letter Queues for Failed Log Processing.

---

**PATTERN: Cache invalidation race without versioning**
CLASS: data
ACTIVATION: Concurrent updates/invalidations without fences; high write rate.
MECHANISM: Thread 1 reads DB and gets V1; Thread 2 writes V2 to DB and invalidates cache; Thread 1 writes V1 (stale) to cache; cache serves V1 while DB has V2; no further invalidation resolves it.
SIGNAL SEQUENCE:
  - [invisible] Cache hit rate stable.
  - [first anomaly] Inconsistent reads reported in logs.
  - [escalation] Data anomalies in downstream.
  - [customer impact] Wrong decisions based on stale data.
LAG: minutes
THRESHOLD (estimated): Write rate >10/sec per key without order preservation.
INVISIBLE BECAUSE: Invalidation seems atomic; no concurrent write tests; works for low-contention keys.
DIAGNOSTIC: Do invalidation events include version checks to prevent applying to newer data?
SOURCES: gitconnected.com on cache invalidation queue; Meta engineering on cache consistency races; DEV Community on race conditions in event-based invalidation.
