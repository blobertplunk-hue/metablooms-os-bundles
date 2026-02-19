# G1 — Adversarial MMD
**Feature:** Monitoring Alert Generation
**Adversarial Reviewer:** MetaBlooms adversarial reviewer (different from research operator)

---

## adversarial_input
**What does a malicious or careless actor send to break this?**

A card author writes `alert_metadata.prometheus.metric_hint: "1 == 1"` — valid PromQL
that always fires. The generator produces a valid YAML file that immediately alerts on
every system it's applied to, causing alert fatigue and masking real incidents.

**Gap found:** The generator must validate that `metric_hint` looks like a metric
selector, not arbitrary PromQL. It should reject expressions containing `==`, `!=`,
or boolean literals. This goes into MMD as a gap.

A careless actor sets `threshold_value: -1`. Generator produces `> -1` which always
fires. Validator must reject non-positive thresholds.

---

## scale_failure
**What breaks at 10x load, data size, or concurrency?**

At 10x patterns (50 cards), generating alerts for all matched patterns on every
pipeline run is still fast (file I/O, no network). This is not a scale concern.

What does break: if `find_by_trigger()` is called with a very long code_shapes list
(50 entries), the keyword match runs 50 × 50 = 2500 comparisons. Still O(milliseconds).
Not a concern at any realistic scale for a pattern library.

**No gap found at this scale.**

---

## api_misuse
**What does a distracted junior engineer do wrong on first use?**

They run `alert_gen RETRY_AMPLIFICATION --platform prometheus` and get a file with
three `# FILL_IN:` markers. They apply the file to Prometheus without filling in the
markers. Prometheus fails to load the rules file — YAML comments are valid YAML, but
the rule `expr` field will be empty or missing.

**Gap found:** FILL_IN markers must be in positions that cause Prometheus rule loading
to fail loudly, not silently apply a broken alert. The `expr` field must be present
and non-empty in Prometheus rules. If `metric_hint` is unknown, emit a syntactically
invalid expression (e.g., `# FILL_IN: replace with PromQL expression`) that fails
`promtool check rules` immediately.

Also: they pipe the output directly to `kubectl apply` without reading it. Same fix —
fail loudly if FILL_IN markers are present.

---

## false_assumption
**Which research claim is most likely false?**

**Claim C3: lag → `for:` duration mapping is reasonable.**

Counterargument: the lag field describes time from *activation* to *customer impact*,
not time from *alert condition true* to *alert firing*. These are different. The Prometheus
`for:` field is "how long must the condition be true before alerting." Setting `for: 5m`
for a pattern with lag=minutes means the alert fires 5 minutes *after* the condition is
met — which is appropriate for sustained conditions but may be too slow for spike-based
failures.

**Gap found:** The lag-to-for mapping needs a second field in `alert_metadata`:
`condition_type: sustained | spike`. Sustained conditions use the lag-to-for mapping.
Spike conditions use `for: 0s` (alert immediately) because the condition may clear before
5 minutes pass.

---

## missing_integration
**What existing system will this touch that isn't mentioned?**

The Prometheus adapter produces YAML. Someone has to apply it. In Kubernetes, Prometheus
rules are loaded via ConfigMaps or PrometheusRule CRDs (if using the Prometheus Operator).
The generator produces plain YAML — it's compatible with both, but the filename and labels
differ. A PrometheusRule CRD requires specific `labels` for the Prometheus Operator to
discover it.

**Gap found:** The Prometheus adapter must document (in comments in the output file) how
to apply it in both standalone Prometheus and Prometheus Operator environments. It should
not silently produce output that only works in one.

---

## obvious_unstated
**What is so obvious the author forgot to state it?**

The generated alert files need to be committed to the repo or applied to infrastructure.
Where do they go? The pipeline produces them in the turn directory. But turn directories
are ephemeral — they're not shipped to production.

**Gap found:** The CDR must specify the output path for generated alert files. Are they
written to `mpp/patterns/alerts/<PATTERN_ID>_alerts.yaml` (committed to the library)?
Or to `turn_dir/alerts/` (per-turn, applied manually)? This is unanswered. Committing
them to the library means they're shared across all users of the pattern — which is the
right behavior, but requires the library to be on the path of the monitoring pipeline.
