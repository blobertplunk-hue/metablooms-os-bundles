# G0 — Context Brief
**Feature:** Monitoring Alert Generation from Pattern Cards
**Turn:** turns/001_monitoring_alert_gen
**Date:** 2026-02-19
**Context Owner:** MetaBlooms engineering

---

## 1. The Real User Story

An engineer is deploying a service that has a retry loop around an external payment API.
They declare `code_shapes: ["retry loop around external API call"]` in their research
dossier. MMD flags `RETRY_AMPLIFICATION` and `NONIDEMPOTENT_RETRY`. They address both
in their MMD report and the pipeline passes.

Three weeks later, the service has a retry storm. Post-incident review reveals there
was no alert on retry count or downstream error rate — the engineer knew the pattern
existed, documented it, but still had to configure monitoring manually from scratch.
They didn't know what metric to use, what threshold to set, or what the alert body
should say.

The frustration: **the pattern card told them exactly what to monitor
(`signal_sequence[first_anomaly]`) and they had to re-derive that information by
hand, at 2am, during an incident.**

The specific person: any engineer who passes a pattern check at MMD. They have
already proven they know which patterns apply to their code. They should receive
the monitoring configuration as an output of the pipeline, not as homework.

---

## 2. Definition of Done

Done means: given a pattern ID and a target monitoring platform, the system
produces a ready-to-apply alert configuration file that:

1. Uses the `signal_sequence[first_anomaly].signal` field as the alert description
2. Sets the alert threshold from `threshold_estimated`
3. Names the alert after the pattern ID (stable, searchable)
4. Includes the `diagnostic` field as the runbook link or annotation
5. Is syntactically valid for the target platform

**Testable right now:**
```
python -m mpp.patterns.alert_gen RETRY_AMPLIFICATION --platform prometheus
```
Produces a `.yaml` file. Load it into a Prometheus rules validator. It passes.
The alert name contains `RETRY_AMPLIFICATION`. The `for:` duration corresponds
to the pattern's `lag` field. The `annotations.runbook` contains the `diagnostic`.

A second test: the same command for all 5 ACTIVE patterns produces 5 valid files
with no manual editing required.

---

## 3. Hidden Constraints

- **The signal_sequence fields were written as prose, not as metric queries.** The
  `first_anomaly` signal for `RETRY_AMPLIFICATION` says "Retry count metrics rise
  in logs." That's not a Prometheus `expr`. The generator cannot fully automate
  metric query construction without per-platform knowledge. The output must be
  honest about what it can and cannot fill in — partial templates with clear
  `# FILL_IN:` markers are better than silently wrong configs.

- **Platform diversity.** Prometheus, CloudWatch, Datadog, and PagerDuty all have
  different alert schema. The generator must be platform-pluggable, not hardcoded.
  Starting with Prometheus (most common, open standard) but the architecture must
  accommodate others without rewriting the core.

- **The pattern cards are the source of truth.** The generator must read cards
  from the live registry at generation time — not from a snapshot. If a card is
  updated (threshold changed, new signal added), the generated alert should change
  on the next run. No caching.

- **DRAFT cards must not produce ACTIVE alert configs.** A DRAFT card has
  unreviewed fields. Its threshold and signal may be wrong. Output from DRAFT
  cards must be clearly marked `# DRAFT — DO NOT APPLY WITHOUT REVIEW`.

---

## 4. Failure Cost

If the generator produces incorrect alert configs:
- Engineers apply them without reading them (that's the whole point of automation)
- Alerts fire on wrong conditions, or never fire on real ones
- The pattern library's credibility is destroyed — if the cards can't be trusted
  to generate valid monitoring, why trust them for anything?

The cost of a wrong alert config is higher than no alert config. The generator
must be conservative: when in doubt, emit a `# FILL_IN:` marker rather than
a plausible-but-wrong value.

---

## 5. Prior Attempts

None in this codebase. Externally:
- Datadog has "recommended monitors" for integrations, but they are hardcoded
  per-integration, not derived from a structured pattern library
- AWS Trusted Advisor has pattern-based recommendations but no alert generation
- No tool derives alert configs from a structured failure pattern schema

This is new. The risk is that the signal_sequence fields are not structured
enough to be machine-readable. We will find out in SEE.
