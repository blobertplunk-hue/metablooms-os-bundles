# Pattern Study: BATCH_JOB_MEMORY_PRESSURE
**Status:** NEEDS_RESEARCH
**Assigned:** unassigned
**Protocol:** `mpp/patterns/STUDY_PROTOCOL.md`
**Target card:** `mpp/patterns/cards/BATCH_JOB_MEMORY_PRESSURE.json`

---

## Phase 1 — Pattern Identity

**Code shape:**
A batch job, ETL pipeline, or report generator that reads a dataset into memory
(or materializes intermediate results in memory) and processes it. The job is
designed and tested against a dataset of known size. Over time, the dataset grows,
or the data characteristics change (more columns, larger field values, lower
selectivity of filters), and the job's memory footprint crosses the container or
process memory limit.

**Failure hypothesis:**
The job is killed by OOM. The failure is often silent (no alert for OOM kills in
many environments), or the alert fires but the job restarts automatically —
restarting into the same OOM condition. If the job has no checkpointing, it restarts
from scratch, consuming the same memory, and is killed again. The job enters an
OOM restart loop, consuming compute resources and making no progress, while the
data it was supposed to process falls further behind.

**Likely pattern class:** `operational`

**Working name:** `BATCH_JOB_MEMORY_PRESSURE`

**Is this covered by an existing card?**
`QUEUE_LAG_SILENT` covers consumer lag but is specific to message queues and
consumer throughput. Batch job OOM is structurally different: the job processes
a bounded dataset in a single run, the failure is a resource constraint rather
than a throughput constraint, and the invisible phase is the restart loop rather
than queue accumulation.

---

## Phase 2 — Targeted Research Directions

### Q1 — Activation condition
The activation is not the OOM itself — it is the dataset crossing a threshold where
the job's memory footprint exceeds available memory. Research: what specific
data characteristics most commonly cause this transition?
- Row count growth (linear with data volume)
- Column proliferation (schema change adds columns to a wide table)
- Filter selectivity change (a WHERE clause that filtered 90% of rows now filters 10%)
- Join cardinality explosion (two tables both grow; the join result grows quadratically)

**Research which cause is most common in real incidents.**

### Q2 — Causal mechanism
Two paths worth distinguishing:

1. **Gradual growth path:** The dataset grows by a small amount every day. Memory
   usage grows with it. At some threshold, the job crosses the memory limit. The
   crossing appears sudden but is the result of months of gradual growth.

2. **Schema change path:** A schema migration adds a large column or changes a filter.
   The next job run immediately uses significantly more memory. The crossing is
   sudden and causally tied to a specific deploy.

Research which path is harder to detect (probably the gradual one) and what
monitoring would catch each.

### Q3 — Signal sequence
The invisible phase for this pattern can be very long — months. Memory usage grows
slowly, the job completes each run, and no alert fires because the job always finishes.
The threshold is crossed on a specific run, which is the first observable signal.

**Find:** what metric would show the gradual memory growth before the OOM? Is job
memory usage typically tracked per run? Is there a way to set an alert on memory
usage trajectory (not just on OOM)?

The restart loop phase is particularly dangerous: in Kubernetes or similar environments,
a crash-looping job may not produce an obvious alert — it may just show
`CrashLoopBackOff` in pod events, which requires checking pod status rather than
receiving a push alert.

### Q4 — Why it's invisible
Batch job memory usage is typically not instrumented at the run level. Monitoring
covers: did the job finish (exit code 0)? Did it take too long (timeout)? But
not: how much memory did it use, and is that increasing over time?

OOM kills in containerized environments produce a kernel-level event that may not
flow to application-level alerting. The job restarts automatically, and if the
restart eventually succeeds (with a smaller intermediate dataset), the failure
never reaches an on-call engineer.

**Find a postmortem** where a batch job OOM loop went undetected for hours or days.

### Q5 — Threshold
Research the typical ratio between dataset size and in-memory working set for common
data processing patterns. Specific patterns to investigate:
- Pandas DataFrame: what is the memory multiplier over raw CSV size?
- SQL query materialization: what is the working set for a GROUP BY on N rows?
- Python list vs. generator: when does the difference matter?

**The threshold should be expressible as a rule:** "if the input dataset size
exceeds X% of available container memory, OOM risk is high."

### Q6 — Diagnostic
Two diagnostics needed:
1. **Runtime:** how do you detect that a job is in an OOM restart loop?
   (kubectl describe pod, CloudWatch metrics, Prometheus container memory metrics)
2. **Proactive:** how do you measure memory usage growth per run over time to
   predict when the threshold will be crossed?

**Find:** what specific metric query surfaces the restart loop in Kubernetes,
ECS, and a raw VM environment (the three most common batch job environments).

### Q7 — Countermeasures
Research direction: streaming vs. batching is the fundamental countermeasure —
don't load the full dataset into memory. But this requires code changes. Research
the cheaper countermeasures that can be applied without rewriting the job:
- Pagination / chunking: process N rows at a time, commit state between chunks
- Checkpointing: record progress so a restart resumes rather than restarts
- Memory limits with headroom: set container memory limit at 2x measured peak,
  alert when usage exceeds 70% of limit

Also research: how do tools like Spark, Dask, and Polars handle datasets larger
than memory? Are these viable drop-in replacements for Pandas in OOM scenarios?

### Q8 — Trigger shapes
Draft trigger shapes:
- "Batch job that reads an entire table or file into a Pandas DataFrame"
- "ETL job with no checkpointing that restarts from the beginning on failure"
- "Report generator with a memory limit set to exactly what it needed on the day it was written"
- "Data pipeline that materializes a JOIN result before filtering it (filter-after-join)"
- "Celery or cron job that runs against a database table with no row limit"

---

## Known Incidents to Search

- Airflow OOM incidents are widely discussed in the Airflow community (search GitHub issues)
- Kubernetes CrashLoopBackOff from OOM — there are several postmortems in the
  community that describe the invisible restart loop
- Spotify engineering — they have written about Hadoop/Spark memory pressure in batch pipelines
- AWS Lambda OOM behavior (similar pattern but different environment) — documented in Lambda docs
- dbt (data build tool) community — OOM in model runs is a recurring topic

## Open Questions for Adversarial Phase

1. Is chunking always safe? If the job has side effects per chunk (e.g., writes to
   an external system per chunk), and a chunk fails halfway, does checkpointing
   prevent duplicate writes or enable them?
2. Does setting a memory limit lower than the current peak usage cause the job to
   fail — and is that failure visible enough to trigger an investigation?
3. If the job runs on a shared host (not a container), OOM may kill a different
   process on the same host. How does this change the signal and the countermeasure?

---

## Ready to Run?

When you pick this up:
1. Read `mpp/patterns/STUDY_PROTOCOL.md` — full protocol
2. Answer all 8 research questions with cited sources
3. Have a different reviewer run the adversarial check (Phase 3)
4. Write `mpp/patterns/cards/BATCH_JOB_MEMORY_PRESSURE.json` using the template
5. Run the registry to validate: `python -c "from mpp.patterns import PatternRegistry; r = PatternRegistry(); print(r.render_index())"`
