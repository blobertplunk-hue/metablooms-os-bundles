# ECL:
#   id: GVN.PATTERN_CONTEXT
#   role: library
#   owns: [PatternContext — the single oracle of detected architectural risks for a pipeline run]
#   does_not: [run the pipeline, validate governance receipts, make pass/fail decisions]
#   inputs: [description: str (architecture text) OR turn_dir: str (for load/save)]
#   outputs: [PatternContext dataclass, gov/G0_LINT_REPORT.json, gov/G0_LINT_REPORT.md]
#   side_effects: [filesystem — write-only on save(), read-only on load()]
#   failure_modes: [PATTERN_LIBRARY_UNAVAILABLE (graceful — returns empty context),
#                   LINT_REPORT_CORRUPT (load returns None)]
#   invariants: [PatternContext is immutable after creation,
#                G0 lint report is the only authoritative source of pattern truth for a run,
#                downstream stages must load from file — never re-run architectural_lint()]
#   evidence: [gov/G0_LINT_REPORT.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
PatternContext — G0 Lint Oracle

Creates, persists, and loads the pattern context for a pipeline run.

The context is built once at G0 by running architectural_lint() on the
Context Brief description. It is saved to gov/G0_LINT_REPORT.json and
gov/G0_LINT_REPORT.md. All downstream stages (G1, G2, G3, PRVE, MMD)
load from that file — they never re-run the lint. This ensures a single
source of truth: if the brief changes mid-run, the risk assessment
doesn't silently shift.

Finding codes (FINDING_*) are stable string constants embedded in
GovIssue.description fields so G3 can detect repeated findings without
parsing free-form text.

Usage:
    ctx = create_pattern_context(brief_text)
    save_pattern_context(turn_dir, ctx)

    # In downstream stages:
    ctx = load_pattern_context(turn_dir)
    if ctx and ctx.block_patterns:
        # enforce cascade coverage ...
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---- Stable finding codes ---------------------------------------------------
# These appear as prefixes in GovIssue.description so G3 can track repeats.

FINDING_MISSING_PATTERN_IN_BRIEF    = "FINDING_MISSING_PATTERN_IN_BRIEF"
FINDING_MISSING_CASCADE_IN_BRIEF    = "FINDING_MISSING_CASCADE_IN_BRIEF"
FINDING_MISSING_DERIVED_CONSTRAINT  = "FINDING_MISSING_DERIVED_CONSTRAINT"
FINDING_MISSING_MISDIAGNOSIS_REVIEW = "FINDING_MISSING_MISDIAGNOSIS_REVIEW"
FINDING_MISSING_CASCADE_NODE_IN_G1  = "FINDING_MISSING_CASCADE_NODE_IN_G1"
FINDING_MISSING_FAILURE_MODE_PATTERN = "FINDING_MISSING_FAILURE_MODE_PATTERN"
FINDING_MISSING_CASCADE_TEST        = "FINDING_MISSING_CASCADE_TEST"

# Risks at these levels require a pattern to be explicitly addressed.
BLOCK_RISK_LEVELS: frozenset[str] = frozenset({"high", "critical"})


# ---- Core data classes -------------------------------------------------------

@dataclass(frozen=True)
class DetectedPattern:
    """A single pattern that architectural_lint() identified in the Context Brief."""
    pattern_id:          str
    name:                str
    pattern_class:       str
    cascade_chain:       List[str]  # ordered IDs of downstream patterns
    data_integrity_risk: str        # none | low | medium | high | critical
    financial_risk:      str        # none | low | medium | high | critical

    @property
    def is_blocking_risk(self) -> bool:
        """True when any risk dimension is high or critical."""
        return (
            self.data_integrity_risk in BLOCK_RISK_LEVELS
            or self.financial_risk in BLOCK_RISK_LEVELS
        )

    @property
    def cascade_depth(self) -> int:
        return len(self.cascade_chain)

    @property
    def severity_label(self) -> str:
        """Human-readable worst-case risk label for this pattern."""
        levels = [self.data_integrity_risk, self.financial_risk]
        for level in ("critical", "high", "medium", "low"):
            if level in levels:
                return level
        return "low"

    def as_dict(self) -> Dict:
        return {
            "pattern_id":          self.pattern_id,
            "name":                self.name,
            "pattern_class":       self.pattern_class,
            "cascade_chain":       self.cascade_chain,
            "data_integrity_risk": self.data_integrity_risk,
            "financial_risk":      self.financial_risk,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> DetectedPattern:
        return cls(
            pattern_id          = d["pattern_id"],
            name                = d["name"],
            pattern_class       = d["pattern_class"],
            cascade_chain       = d.get("cascade_chain", []),
            data_integrity_risk = d.get("data_integrity_risk", "low"),
            financial_risk      = d.get("financial_risk", "low"),
        )


@dataclass
class PatternContext:
    """
    The single oracle of architectural risk for a pipeline run.

    Created once at G0. Persisted to gov/G0_LINT_REPORT.json.
    All downstream stages load from file — they do not re-run the lint.
    """
    generated_at:       str
    source_description: str             # first 500 chars of the linted text
    detected:           List[DetectedPattern] = field(default_factory=list)

    @property
    def has_patterns(self) -> bool:
        return bool(self.detected)

    @property
    def block_patterns(self) -> List[DetectedPattern]:
        """Patterns with data_integrity_risk or financial_risk in {high, critical}."""
        return [p for p in self.detected if p.is_blocking_risk]

    @property
    def deep_cascade_patterns(self) -> List[DetectedPattern]:
        """Patterns with cascade_depth >= 3 OR blocking risk — require cascade mitigation."""
        return [
            p for p in self.detected
            if p.cascade_depth >= 3 or p.is_blocking_risk
        ]

    def all_required_ids(self) -> List[str]:
        """
        Every pattern ID that must be addressed in downstream artifacts.
        Includes both direct patterns and their cascade nodes for block/deep patterns.
        """
        ids: list[str] = []
        for p in self.detected:
            ids.append(p.pattern_id)
        for p in self.deep_cascade_patterns:
            for node_id in p.cascade_chain:
                if node_id not in ids:
                    ids.append(node_id)
        return ids

    def as_dict(self) -> Dict:
        return {
            "generated_at":       self.generated_at,
            "source_description": self.source_description,
            "detected":           [p.as_dict() for p in self.detected],
        }

    @classmethod
    def from_dict(cls, d: Dict) -> PatternContext:
        return cls(
            generated_at       = d.get("generated_at", ""),
            source_description = d.get("source_description", ""),
            detected           = [
                DetectedPattern.from_dict(p)
                for p in d.get("detected", [])
            ],
        )


# ---- Factory -----------------------------------------------------------------

def create_pattern_context(description: str) -> PatternContext:
    """
    Run architectural_lint() on description and return a PatternContext.

    If the pattern library is unavailable (sklearn missing, import error),
    returns an empty context so the pipeline degrades gracefully.
    """
    try:
        from mpp.patterns import PatternRegistry
        from mpp.patterns.pattern_graph import PatternGraph
    except ImportError:
        return PatternContext(
            generated_at       = _now(),
            source_description = description[:500],
            detected           = [],
        )

    try:
        registry = PatternRegistry()
        graph    = PatternGraph(registry)
        report   = graph.architectural_lint(description)
    except Exception:
        return PatternContext(
            generated_at       = _now(),
            source_description = description[:500],
            detected           = [],
        )

    detected: List[DetectedPattern] = []
    for card in report.direct:
        cascade_ids = [c.id for c in report.cascades.get(card.id, [])]
        rc = card.recovery_cost or {}
        detected.append(DetectedPattern(
            pattern_id          = card.id,
            name                = card.name,
            pattern_class       = card.pattern_class,
            cascade_chain       = cascade_ids,
            data_integrity_risk = rc.get("data_integrity_risk", "low"),
            financial_risk      = rc.get("financial_risk", "low"),
        ))

    return PatternContext(
        generated_at       = _now(),
        source_description = description[:500],
        detected           = detected,
    )


# ---- Persistence -------------------------------------------------------------

def save_pattern_context(turn_dir: str, ctx: PatternContext) -> None:
    """Write G0_LINT_REPORT.json and G0_LINT_REPORT.md into turn_dir/gov/."""
    gov_dir = Path(turn_dir) / "gov"
    gov_dir.mkdir(parents=True, exist_ok=True)

    (gov_dir / "G0_LINT_REPORT.json").write_text(
        json.dumps(ctx.as_dict(), indent=2), encoding="utf-8"
    )
    (gov_dir / "G0_LINT_REPORT.md").write_text(
        _render_markdown(ctx), encoding="utf-8"
    )


def load_pattern_context(turn_dir: str) -> Optional[PatternContext]:
    """
    Load PatternContext from gov/G0_LINT_REPORT.json.
    Returns None if the file doesn't exist or is malformed.
    """
    path = Path(turn_dir) / "gov" / "G0_LINT_REPORT.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PatternContext.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# ---- Rendering ---------------------------------------------------------------

def _render_markdown(ctx: PatternContext) -> str:
    lines = [
        "# G0 Architectural Risk Lint Report",
        "",
        f"*Generated: {ctx.generated_at}*",
        "",
    ]

    if not ctx.detected:
        lines += [
            "No architectural risk patterns detected in the Context Brief description.",
            "",
            "This means either:",
            "- The design does not match any known failure pattern trigger shapes, or",
            "- The Context Brief description is too brief for pattern matching.",
            "",
            "If the design involves retries, queues, caches, connection pools, or",
            "distributed writes, verify that the brief describes these components explicitly.",
        ]
        return "\n".join(lines)

    lines += [
        f"**{len(ctx.detected)} direct risk(s) detected.**",
        "",
        "## Detected Patterns",
        "",
    ]

    for p in ctx.detected:
        risk_flags = []
        if p.data_integrity_risk in BLOCK_RISK_LEVELS:
            risk_flags.append(f"data integrity: **{p.data_integrity_risk}**")
        if p.financial_risk in BLOCK_RISK_LEVELS:
            risk_flags.append(f"financial: **{p.financial_risk}**")
        risk_str = " | ".join(risk_flags) if risk_flags else "no high/critical flags"

        lines.append(f"### {p.pattern_id}")
        lines.append(f"**{p.name}** `[{p.pattern_class}]`")
        lines.append(f"Risk: {risk_str}")
        if p.cascade_chain:
            chain = " → ".join([p.pattern_id] + p.cascade_chain)
            lines.append(f"Cascade (depth {p.cascade_depth}): `{chain}`")
        lines.append("")

    block = ctx.block_patterns
    if block:
        lines += [
            "## Required Actions (blocking)",
            "",
            "These patterns have HIGH or CRITICAL risk. The `Failure Cost / Critical Risks`",
            "section of `CONTEXT_BRIEF.md` must explicitly name each one, or G0 will block.",
            "",
        ]
        for p in block:
            lines.append(f"- **{p.pattern_id}**: {p.name}")
            if p.cascade_chain:
                lines.append(f"  - Cascade nodes that must also be addressed: "
                              + ", ".join(p.cascade_chain))
        lines.append("")

    return "\n".join(lines)


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"
