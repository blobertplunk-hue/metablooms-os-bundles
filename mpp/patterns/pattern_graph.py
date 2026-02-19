"""
Pattern Graph — Failure Dependency Map and Architectural Lint Engine.

The graph is built from the `cascades_to` field on each pattern card.
An edge A → B means: when pattern A manifests, it frequently activates
the conditions for pattern B.

The three capabilities this provides:

1. chain(start_id) — Given a detected pattern, what follows?
   Use during incident response to anticipate the next failure before it hits.

2. architectural_lint(description) — Given an architecture description,
   find direct risks AND the full downstream cascade. Use this at design time
   to block architectures before a line of code is written.

3. render_mermaid() — Full cascade graph as a Mermaid flowchart.
   Paste into any markdown file or architecture doc.

Usage:
    from mpp.patterns import PatternRegistry
    from mpp.patterns.pattern_graph import PatternGraph

    registry = PatternRegistry()
    graph = PatternGraph(registry)

    # Design-time: what does this architecture risk?
    report = graph.architectural_lint(
        "API gateway with 3 retries calling order service with 3 retries "
        "calling payment service with 2 retries and a Redis cache"
    )
    print(report.render_markdown())

    # Incident-time: what comes next?
    chain = graph.chain("RETRY_AMPLIFICATION")
    for card in chain:
        print(f"  → {card.id}: {card.name}")

    # Architecture doc:
    print(graph.render_mermaid())
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from mpp.patterns.pattern_registry import PatternCard, PatternHypothesis, PatternRegistry


@dataclass
class LintReport:
    """
    Result of architectural_lint().

    direct:   cards whose trigger_shapes matched the architecture description.
    cascades: for each direct card, the downstream chain it can activate.
    """
    description: str
    direct:      List[PatternCard]
    cascades:    Dict[str, List[PatternCard]] = field(default_factory=dict)

    def render_markdown(self) -> str:
        if not self.direct:
            return (
                "## Architectural Risk Assessment\n\n"
                "> No pattern signals detected for this description.\n"
            )

        all_downstream: set[str] = set()
        for chain in self.cascades.values():
            all_downstream.update(c.id for c in chain)

        lines = [
            "## Architectural Risk Assessment",
            "",
            f"> Input: *{self.description[:120]}{'...' if len(self.description) > 120 else ''}*",
            "",
            f"**{len(self.direct)} direct risk(s)** detected."
            + (f" **{len(all_downstream)} cascade risk(s)** downstream." if all_downstream else ""),
            "",
            "### Direct Risks",
            "",
        ]

        for card in self.direct:
            lines.append(f"**{card.id}** — {card.name} `[{card.pattern_class}]`")
            lines.append(f"> {card.diagnostic[:160]}...")
            if card.misdiagnosis:
                lines.append(f"> *Common misdiagnosis:* {card.misdiagnosis[0]}")
            if card.id in self.cascades:
                chain_ids = " → ".join(c.id for c in self.cascades[card.id])
                lines.append(f"> *Cascade if unmitigated:* {card.id} → {chain_ids}")
            lines.append("")

        if self.cascades:
            lines += ["### Cascade Chains", ""]
            for source_id, chain in self.cascades.items():
                path = " → ".join([source_id] + [c.id for c in chain])
                lines.append(f"- {path}")
            lines.append("")

        lines += [
            "### Mermaid Diagram",
            "",
            "```mermaid",
            self._render_mermaid_scoped(),
            "```",
        ]
        return "\n".join(lines)

    def render_mermaid(self) -> str:
        return self._render_mermaid_scoped()

    def _render_mermaid_scoped(self) -> str:
        """Mermaid diagram scoped to only the cards in this report."""
        if not self.direct:
            return "flowchart LR\n  empty[No patterns detected]"

        # Collect all nodes in this report
        nodes: dict[str, PatternCard] = {}
        edges: list[tuple[str, str]] = []

        # Direct risks have an input node pointing to them
        for card in self.direct:
            nodes[card.id] = card

        for source_id, chain in self.cascades.items():
            for card in chain:
                nodes[card.id] = card
            # Build edges along the chain
            ids = [source_id] + [c.id for c in chain]
            for i in range(len(ids) - 1):
                a, b = ids[i], ids[i + 1]
                if (a, b) not in edges:
                    edges.append((a, b))

        lines = ["flowchart LR"]
        lines.append('  input["Architecture description"]')
        for card_id, card in nodes.items():
            label = card.id.replace("_", " ")
            cls = card.pattern_class[:4].upper()
            lines.append(f'  {card_id}["{label}\\n[{cls}]"]')
        lines.append("")

        for card in self.direct:
            lines.append(f"  input --> {card.id}")

        for a, b in edges:
            lines.append(f"  {a} --> {b}")

        return "\n".join(lines)


class PatternGraph:
    """
    Directed graph of pattern cascade relationships.

    Nodes: all active PatternCards.
    Edges: A → B when card A has B in its cascades_to list.
    """

    def __init__(self, registry: PatternRegistry) -> None:
        self._registry = registry
        # out_edges[id] = list of target ids this card cascades to
        self._out_edges: Dict[str, List[str]] = {}
        # in_edges[id]  = list of source ids that cascade into this card
        self._in_edges:  Dict[str, List[str]] = {}

        for card in registry.all_active():
            targets = card.cascades_to or []
            self._out_edges[card.id] = list(targets)
            for target_id in targets:
                self._in_edges.setdefault(target_id, []).append(card.id)

    # ---- Core traversal -----------------------------------------------------

    def chain(self, start_id: str, *, max_depth: int = 6) -> List[PatternCard]:
        """
        Return all patterns reachable from start_id via cascade edges (BFS).

        Result is ordered by BFS level — immediate cascades first, then
        second-order, etc. start_id itself is not included.

        Use during incident response: "RETRY_AMPLIFICATION fired — what follows?"
        """
        visited: set[str] = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        result: List[PatternCard] = []

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for target_id in self._out_edges.get(current_id, []):
                if target_id not in visited:
                    visited.add(target_id)
                    card = self._registry.get(target_id)
                    if card and card.is_active:
                        result.append(card)
                        queue.append((target_id, depth + 1))

        return result

    def upstream(self, target_id: str) -> List[PatternCard]:
        """
        Return all patterns that cascade into target_id.

        Use to understand what can cause a pattern you've already identified:
        "I have DLQ_ACCUMULATION — what upstream patterns triggered it?"
        """
        return [
            card
            for source_id in self._in_edges.get(target_id, [])
            if (card := self._registry.get(source_id)) and card.is_active
        ]

    def full_path(self, start_id: str, end_id: str) -> Optional[List[PatternCard]]:
        """
        Return the shortest cascade path from start_id to end_id, or None if no path.
        Includes both endpoints. Used to trace causal chains in postmortems.
        """
        if start_id == end_id:
            card = self._registry.get(start_id)
            return [card] if card else None

        visited: set[str] = {start_id}
        queue: deque[tuple[str, list[str]]] = deque([(start_id, [start_id])])

        while queue:
            current_id, path = queue.popleft()
            for target_id in self._out_edges.get(current_id, []):
                if target_id not in visited:
                    new_path = path + [target_id]
                    if target_id == end_id:
                        return [
                            c for pid in new_path
                            if (c := self._registry.get(pid))
                        ]
                    visited.add(target_id)
                    queue.append((target_id, new_path))

        return None

    # ---- Lint and visualization ----------------------------------------------

    def architectural_lint(self, description: str) -> LintReport:
        """
        Given a plain-English architecture description, return:
          - direct: patterns whose trigger_shapes match the description
          - cascades: for each direct pattern, its full downstream chain

        This is design-time blocking — run it before code is written.

        Example:
            report = graph.architectural_lint(
                "microservice with layered retry policies and a Redis cache"
            )
            print(report.render_markdown())
        """
        direct = self._registry.find_by_trigger(description)
        cascades: Dict[str, List[PatternCard]] = {}
        for card in direct:
            downstream = self.chain(card.id)
            if downstream:
                cascades[card.id] = downstream
        return LintReport(description=description, direct=direct, cascades=cascades)

    def render_mermaid(self) -> str:
        """
        Render the full cascade graph as a Mermaid flowchart.
        Only includes cards that have at least one edge.
        """
        lines = ["flowchart LR"]

        # Nodes with at least one edge
        has_edge: set[str] = set()
        for src, targets in self._out_edges.items():
            if targets:
                has_edge.add(src)
                has_edge.update(targets)

        for card in self._registry.all_active():
            if card.id in has_edge:
                label = card.id.replace("_", " ")
                cls = card.pattern_class[:4].upper()
                lines.append(f'  {card.id}["{label}\\n[{cls}]"]')

        lines.append("")

        for src, targets in sorted(self._out_edges.items()):
            for tgt in targets:
                lines.append(f"  {src} --> {tgt}")

        return "\n".join(lines)

    def render_cascade_summary(self) -> str:
        """
        Render a human-readable summary of all cascade chains.
        Shows which single root pattern can eventually cascade into the most failures.
        """
        lines = ["# Failure Cascade Map\n"]
        # Find root nodes (no in-edges)
        roots = [
            card for card in self._registry.all_active()
            if not self._in_edges.get(card.id)
            and self._out_edges.get(card.id)
        ]
        for root in sorted(roots, key=lambda c: -len(self.chain(c.id))):
            chain = self.chain(root.id)
            path = " → ".join([root.id] + [c.id for c in chain])
            lines.append(f"**{root.id}** ({root.pattern_class})")
            lines.append(f"  Full chain: {path}")
            lines.append(f"  Depth: {len(chain)} downstream pattern(s)")
            lines.append("")
        return "\n".join(lines)
