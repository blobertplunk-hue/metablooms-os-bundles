# ECL:
#   id: MPP.PATTERNS.PLATFORMS.PROMETHEUS
#   role: adapter
#   owns: [rendering a PatternCard into a valid Prometheus alert rule YAML string]
#   does_not: [write files, load the registry, validate card schema beyond alert_metadata]
#   inputs: [card: PatternCard]
#   outputs: [str — Prometheus alert rules YAML, ready to write to a .yaml file]
#   side_effects: [none]
#   failure_modes: [METRIC_HINT_INJECTION, NONPOSITIVE_THRESHOLD, FILL_IN_SENTINEL_EMITTED]
#   invariants: [output is always syntactically valid YAML,
#                FILL_IN sentinel strings cause promtool check rules to fail loudly,
#                DRAFT cards always carry a prominent header warning]
#   evidence: [tests/test_alert_gen.py]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
Prometheus Alert Adapter

Renders a PatternCard into a Prometheus alert rule YAML string.

For cards with alert_metadata.metric_category == 'data_consistency':
  Emits a comment-only block explaining that no time-series alert is possible
  and what type of check is required instead.

For all other cards with alert_metadata.prometheus present:
  Renders a complete Prometheus alert rule with validated fields.

For cards with no alert_metadata:
  Renders a fully FILL_IN template — syntactically valid YAML, but every
  metric field contains a sentinel string that promtool check rules rejects.

Application instructions are embedded in the file header comment.
"""

from __future__ import annotations

import re
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mpp.patterns.pattern_registry import PatternCard

# Sentinel used in place of unknown metric expressions.
# This string is not valid PromQL — promtool check rules will reject it,
# preventing engineers from accidentally applying an incomplete alert.
FILL_IN_SENTINEL = "FILL_IN_REPLACE_WITH_PROMQL_EXPRESSION"

# Reject metric_hint strings that contain PromQL comparison operators
# as standalone binary operators (spaces required) — these indicate that
# the author wrote a full expression rather than a metric selector.
# Valid label matchers like {code=~"5.."} or {status!="ok"} are allowed.
_BANNED_METRIC_HINT_PATTERNS = re.compile(
    r"(\s==\s|\s!=\s|\s>=\s|\s<=\s|\s>\s|\s<\s|^\s*[01]\s*$|^\s*true\s*$|^\s*false\s*$)",
    re.IGNORECASE,
)

_LAG_TO_FOR = {
    "seconds":        "30s",
    "minutes":        "5m",
    "minutes to hours": "5m",
    "hours":          "30m",
    "hours to days":  "1h",
    "days":           "6h",
}

_COMPARISON_TO_PROMQL = {
    "gt":  ">",
    "lt":  "<",
    "gte": ">=",
    "lte": "<=",
}


class MetricHintValidationError(ValueError):
    """Raised when metric_hint contains disallowed content."""


def render(card: "PatternCard") -> str:
    """Render card to a Prometheus alert rules YAML string."""
    header    = _render_header(card)
    alert     = _render_alert_block(card)
    footer    = _render_application_instructions(card)
    return header + alert + footer


# ---- Section renderers ------------------------------------------------------

def _render_header(card: "PatternCard") -> str:
    draft_warning = (
        "# ╔══════════════════════════════════════════════════════════════╗\n"
        "# ║  WARNING: DRAFT CARD                                        ║\n"
        "# ║  Fields have not passed G2 behavior review.                 ║\n"
        "# ║  DO NOT APPLY without manual verification of all values.    ║\n"
        "# ╚══════════════════════════════════════════════════════════════╝\n"
        "#\n"
    ) if card.is_draft else ""

    return (
        f"# MetaBlooms Pattern Alert — {card.id}\n"
        f"# {card.name}\n"
        f"# Class: {card.pattern_class} | Status: {card.status} | Lag: {card.lag}\n"
        f"#\n"
        f"{draft_warning}"
        f"# Generated from mpp/patterns/cards/{card.id}.json\n"
        f"# Last card review: {card.last_reviewed}\n"
        f"#\n"
    )


def _render_alert_block(card: "PatternCard") -> str:
    meta = getattr(card, "alert_metadata", None)
    if not isinstance(meta, dict):
        return _render_fill_in_block(card)

    category = meta.get("metric_category", "")
    if category == "data_consistency":
        return _render_data_consistency_block(card, meta)

    prom = meta.get("prometheus")
    if not isinstance(prom, dict):
        return _render_fill_in_block(card)

    return _render_metric_alert_block(card, meta, prom)


def _render_metric_alert_block(card: "PatternCard", meta: dict, prom: dict) -> str:
    metric_hint      = str(prom.get("metric_hint", ""))
    threshold_value  = prom.get("threshold_value")
    threshold_unit   = prom.get("threshold_unit", "")
    comparison       = prom.get("comparison", "gt")
    for_duration     = prom.get("for_duration", "5m")
    severity         = prom.get("severity", "warning")
    condition_type   = meta.get("condition_type", "sustained")

    _validate_metric_hint(metric_hint, card.id)

    if threshold_value is None or threshold_value <= 0:
        raise ValueError(
            f"[{card.id}] alert_metadata.prometheus.threshold_value must be positive, "
            f"got: {threshold_value}"
        )

    promql_op   = _COMPARISON_TO_PROMQL.get(comparison, ">")
    effective_for = "0s" if condition_type == "spike" else for_duration
    alert_name  = f"MetaBlooms{card.id.replace('_', '').title()}"

    first_anomaly = next(
        (s["signal"] for s in card.signal_sequence if s["phase"] == "first_anomaly"),
        "See pattern card for signal description."
    )

    return (
        f"groups:\n"
        f"  - name: metablooms.{card.id.lower()}\n"
        f"    rules:\n"
        f"      - alert: {alert_name}\n"
        f"        expr: {metric_hint} {promql_op} {threshold_value}\n"
        f"        for: {effective_for}\n"
        f"        labels:\n"
        f"          severity: {severity}\n"
        f"          pattern_id: {card.id}\n"
        f"          pattern_class: {card.pattern_class}\n"
        f"        annotations:\n"
        f"          summary: \"{card.name} detected\"\n"
        f"          description: >\n"
        + textwrap.indent(
            f"First signal: {first_anomaly}\n"
            f"Threshold: {threshold_value} {threshold_unit} ({comparison}).\n"
            f"Condition type: {condition_type}. Lag to customer impact: {card.lag}.",
            "            "
        ) + "\n"
        f"          runbook: |\n"
        f"            {card.diagnostic}\n"
        f"          pattern_card: mpp/patterns/cards/{card.id}.json\n"
        f"\n"
    )


def _render_data_consistency_block(card: "PatternCard", meta: dict) -> str:
    first_anomaly = next(
        (s["signal"] for s in card.signal_sequence if s["phase"] == "first_anomaly"),
        ""
    )
    return (
        f"# ── DATA CONSISTENCY PATTERN — NO PROMETHEUS ALERT POSSIBLE ──\n"
        f"#\n"
        f"# Pattern '{card.id}' ({card.name}) cannot be detected by a\n"
        f"# time-series metric alert. Its first observable signal is:\n"
        f"#\n"
        f"#   {first_anomaly}\n"
        f"#\n"
        f"# Required check type: reconciliation job\n"
        f"# A scheduled job must compare state across system boundaries and\n"
        f"# alert when values diverge. This cannot be expressed as PromQL.\n"
        f"#\n"
        f"# Diagnostic:\n"
        + "".join(f"#   {line}\n" for line in card.diagnostic.splitlines())
        + f"#\n"
        f"# See card for countermeasures: mpp/patterns/cards/{card.id}.json\n"
        f"\n"
    )


def _render_fill_in_block(card: "PatternCard") -> str:
    alert_name = f"MetaBlooms{card.id.replace('_', '').title()}"
    return (
        f"# ── FILL_IN TEMPLATE — alert_metadata not present in card ──\n"
        f"# Complete all FILL_IN values before applying.\n"
        f"# This file will fail promtool check rules until completed.\n"
        f"#\n"
        f"groups:\n"
        f"  - name: metablooms.{card.id.lower()}\n"
        f"    rules:\n"
        f"      - alert: {alert_name}\n"
        f"        expr: {FILL_IN_SENTINEL}\n"
        f"        for: FILL_IN_FOR_DURATION  # e.g. 5m\n"
        f"        labels:\n"
        f"          severity: FILL_IN_SEVERITY  # warning | critical\n"
        f"          pattern_id: {card.id}\n"
        f"        annotations:\n"
        f"          summary: \"{card.name} detected\"\n"
        f"          description: FILL_IN_DESCRIPTION\n"
        f"          runbook: |\n"
        f"            {card.diagnostic}\n"
        f"\n"
    )


def _render_application_instructions(card: "PatternCard") -> str:
    return (
        f"# ── HOW TO APPLY ─────────────────────────────────────────────\n"
        f"#\n"
        f"# Standalone Prometheus:\n"
        f"#   1. Copy this file to your Prometheus rules directory\n"
        f"#   2. Run: promtool check rules {card.id}_prometheus_alerts.yaml\n"
        f"#   3. Reload Prometheus: curl -X POST http://localhost:9090/-/reload\n"
        f"#\n"
        f"# Prometheus Operator (Kubernetes):\n"
        f"#   Wrap in a PrometheusRule CRD with these required labels:\n"
        f"#     labels:\n"
        f"#       release: <your-prometheus-release-name>\n"
        f"#   kubectl apply -f {card.id}_prometheus_rule.yaml\n"
        f"#\n"
        f"# Customize metric_hint for your environment:\n"
        f"#   The metric name in expr is a hint — replace with the exact\n"
        f"#   metric your instrumentation exposes.\n"
    )


# ---- Validation -------------------------------------------------------------

def _validate_metric_hint(hint: str, pattern_id: str) -> None:
    """Reject metric_hint strings that look like PromQL injection attempts."""
    if not hint or hint == FILL_IN_SENTINEL:
        return
    if _BANNED_METRIC_HINT_PATTERNS.search(hint):
        raise MetricHintValidationError(
            f"[{pattern_id}] alert_metadata.prometheus.metric_hint contains disallowed "
            f"content: '{hint}'. Provide a metric selector only, not a full PromQL "
            f"expression with comparisons or boolean literals."
        )
