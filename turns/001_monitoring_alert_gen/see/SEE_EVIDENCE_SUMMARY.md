# SEE Evidence Summary — Monitoring Alert Generation

## Finding on Claim C1 (critical)

**Claim:** `signal_sequence[first_anomaly].signal` is specific enough to map to
a named metric category.

**Finding: PARTIALLY TRUE. Two of five cards describe data-consistency checks,
not observable time-series metrics.**

| Pattern | first_anomaly signal | Alertable? | Reason |
|---|---|---|---|
| `DLQ_ACCUMULATION` | "DLQ depth increases" | YES | Queue depth is a standard metric in every platform |
| `QUEUE_LAG_SILENT` | "Rising lag metric (consumer group lag...)" | YES | Consumer lag is a standard metric |
| `RETRY_AMPLIFICATION` | "Retry count metrics rise in logs. Latency p99 creeps up." | PARTIAL | Multiple signals; metric name is platform-specific |
| `NONIDEMPOTENT_RETRY` | "Duplicate entries appear in audit logs" | NO | Data consistency check — requires reconciliation job, not a metric alert |
| `CACHE_INVALIDATION_RACE` | "Inconsistent reads reported by clients" | NO | Data consistency check — requires read comparison, not a metric alert |

**Implication for design:** The generator cannot derive a Prometheus `expr` from
prose alone for any card. The signal fields were written for human comprehension,
not for machine translation.

**Resolution:** Add a structured `alert_metadata` field to each pattern card
containing the machine-readable alert parameters. This is additive — prose fields
stay for human readers; `alert_metadata` drives the generator. Cards without
`alert_metadata` produce FILL_IN templates. Cards with it produce real configs.

---

## Finding on Claim C2 (confirmed)

Prometheus alert rule YAML is the right first platform. Schema is stable (unchanged
since Prometheus 2.0, 2017). Rules files are widely used, human-readable, and
validated by `promtool check rules`. CloudWatch and Datadog are strong second targets
but have proprietary schema — Prometheus first, adapters second.

**Source:** Prometheus documentation — https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/

---

## Finding on Claim C3 (confirmed with mapping table)

Lag → `for:` duration mapping is standard practice:

| Pattern lag field | Prometheus `for:` | Reasoning |
|---|---|---|
| `seconds` | `30s` | Short enough to catch fast failures |
| `minutes` | `5m` | Standard for transient vs. sustained distinction |
| `minutes to hours` | `5m` | Use the shorter bound; alert early |
| `hours` | `30m` | Long enough to avoid noise from brief spikes |
| `hours to days` | `1h` | DLQ accumulation is slow; avoid false positives |

**Source:** Google SRE workbook, Alerting on SLOs chapter — recommends `for:` of
at least 5 minutes for non-critical alerts to reduce noise.

---

## Finding on Claim C4 (confirmed)

`# FILL_IN:` is established practice. Helm chart templates, Terraform modules, and
AWS CloudFormation samples all use placeholder comments. Engineers expect them.

**Key constraint found:** FILL_IN values must be syntactically valid YAML comments
so the output file can be loaded by a YAML parser without error. The alert must
be completable without touching any other part of the file.

---

## New Finding: alert_metadata field specification

Based on the above, each card needs a new optional field. Derived from inspecting
DLQ_ACCUMULATION and QUEUE_LAG_SILENT (the two fully alertable cards):

```json
"alert_metadata": {
  "metric_category": "queue_depth | consumer_lag | error_rate | latency | data_consistency",
  "prometheus": {
    "metric_hint": "suggested metric name or PromQL fragment — FILL_IN if unknown",
    "threshold_value": 10,
    "threshold_unit": "messages_per_hour | ratio | seconds | milliseconds",
    "comparison": "gt | lt | gte | lte",
    "for_duration": "5m",
    "severity": "warning | critical"
  }
}
```

`data_consistency` category signals that no Prometheus alert is possible; the
generator emits a comment explaining what type of check is needed instead.
