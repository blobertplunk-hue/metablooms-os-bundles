# SEE Anti-Patterns — Monitoring Alert Generation

## AP1 — Generating alerts from prose fields directly

**What it looks like:** Parsing `signal_sequence[first_anomaly].signal` with regex
or string matching to extract metric names.

**Why it fails:** The prose was written for humans, not parsers. "Retry count metrics
rise in logs" does not tell you whether the metric is `http_requests_retried_total`,
`retry_count`, or something custom. Regex on prose produces brittle, wrong configs.

**Instead:** `alert_metadata.prometheus.metric_hint` is a curated, human-authored
hint that the generator uses directly. The card author writes it once; the generator
uses it forever.

---

## AP2 — Making alert generation block the pipeline

**What it looks like:** Adding alert generation as a required gate in gov_pipeline.py
such that a missing `alert_metadata` field blocks certification.

**Why it fails:** Alert generation is valuable but not safety-critical. A certified
pattern card with no `alert_metadata` is still a valid, reviewed pattern card. Making
it blocking would require retrofitting all 5 existing cards before shipping any new
feature.

**Instead:** Alert generation is a post-certification tool, not a gate. Cards without
`alert_metadata` produce FILL_IN templates. The FILL_IN output is still useful — it
tells the engineer exactly what to configure, even if it can't configure it automatically.

---

## AP3 — One monolithic alert file for all patterns

**What it looks like:** Generating a single `all_patterns_alerts.yaml` containing
rules for every matched pattern.

**Why it fails:** Engineers need to apply alerts per-service, not globally. A service
with a retry loop needs RETRY_AMPLIFICATION alerts; it does not need DLQ_ACCUMULATION
alerts. A monolithic file forces engineers to manually delete irrelevant rules —
exactly the kind of friction that causes alerts to be skipped.

**Instead:** One file per pattern, named `<PATTERN_ID>_alerts.yaml`. Engineers apply
only the files matching their `pattern_checks`. The pipeline can emit a manifest
listing which files to apply for a given run.
