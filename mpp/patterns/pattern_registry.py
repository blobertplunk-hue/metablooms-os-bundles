# ECL:
#   id: MPP.PATTERNS.REGISTRY
#   role: library
#   owns: [loading, validating, indexing, and rendering pattern cards from mpp/patterns/cards/]
#   does_not: [write or edit cards, conduct research, make architectural decisions]
#   inputs: [cards_dir: Path — defaults to the cards/ directory adjacent to this file]
#   outputs: [PatternCard objects, markdown render strings, index dicts]
#   side_effects: [none — read-only]
#   failure_modes: [CARD_NOT_FOUND, SCHEMA_VIOLATION, CARDS_DIR_MISSING]
#   invariants: [every loaded card passes schema validation before being returned,
#                a card with status=DRAFT is loaded but flagged in all outputs,
#                a card with status=DEPRECATED is loaded but excluded from active index,
#                find_by_trigger uses TF-IDF cosine similarity when sklearn is available,
#                falls back to keyword matching when sklearn is absent (logs warning)]
#   evidence: [test output from tests/test_pattern_registry.py,
#              turns/002_semantic_matching/see/SEE_EVIDENCE_SUMMARY.md]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
Pattern Registry

Loads all JSON pattern cards from mpp/patterns/cards/, validates them against
PATTERN_SCHEMA.json, and provides lookup and rendering functions.

This is a read-only library. It never writes, edits, or creates cards.
Card authorship goes through the Study Protocol and MPP review.

Usage:
    from mpp.patterns.pattern_registry import PatternRegistry

    registry = PatternRegistry()
    card = registry.get("RETRY_AMPLIFICATION")
    print(registry.render_card(card))

    matches = registry.find_by_trigger("retry loop around an external API call")
    for card in matches:
        print(card.name)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "scikit-learn not installed — find_by_trigger() will use keyword matching. "
        "Install scikit-learn for TF-IDF semantic matching: pip install scikit-learn"
    )

_TFIDF_THRESHOLD = 0.15


CARDS_DIR  = Path(__file__).parent / "cards"
SCHEMA_PATH = Path(__file__).parent / "PATTERN_SCHEMA.json"

REQUIRED_FIELDS = [
    "id", "name", "class", "status", "tags", "trigger_shapes",
    "activation", "mechanism", "signal_sequence", "lag",
    "threshold_estimated", "invisible_because", "diagnostic",
    "countermeasures", "sources", "discovered", "last_reviewed",
]

SIGNAL_PHASES_IN_ORDER = ["invisible", "first_anomaly", "escalation", "customer_impact"]


@dataclass
class PatternCard:
    id:                  str
    name:                str
    pattern_class:       str
    status:              str
    tags:                List[str]
    trigger_shapes:      List[str]
    activation:          str
    mechanism:           str
    signal_sequence:     List[Dict[str, str]]
    lag:                 str
    threshold_estimated: str
    invisible_because:   str
    diagnostic:          str
    countermeasures:     List[str]
    sources:             List[Dict[str, str]]
    discovered:          str
    last_reviewed:       str
    alert_metadata:      Optional[Dict] = None

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def is_draft(self) -> bool:
        return self.status == "DRAFT"


class RegistryValidationError(Exception):
    """Raised when a card file fails schema validation."""


class PatternRegistry:
    """
    Loads and indexes all pattern cards from the cards/ directory.

    On construction, all cards are validated. If any card fails validation,
    a RegistryValidationError is raised with a list of all violations.
    """

    def __init__(self, cards_dir: Path = CARDS_DIR) -> None:
        if not cards_dir.exists():
            raise FileNotFoundError(f"Pattern cards directory not found: {cards_dir}")
        self._cards: Dict[str, PatternCard] = {}
        self._load_all(cards_dir)
        self._build_tfidf_index()

    # ---- Public API ---------------------------------------------------------

    def get(self, pattern_id: str) -> Optional[PatternCard]:
        """Return a card by its ID, or None if not found."""
        return self._cards.get(pattern_id.upper())

    def all_active(self) -> List[PatternCard]:
        """Return all cards with status=ACTIVE, sorted by id."""
        return sorted(
            (c for c in self._cards.values() if c.is_active),
            key=lambda c: c.id,
        )

    def all_drafts(self) -> List[PatternCard]:
        """Return all cards with status=DRAFT, sorted by id."""
        return sorted(
            (c for c in self._cards.values() if c.is_draft),
            key=lambda c: c.id,
        )

    def find_by_class(self, pattern_class: str) -> List[PatternCard]:
        """Return all active cards matching a class (architectural, operational, data, ...)."""
        return [c for c in self.all_active() if c.pattern_class == pattern_class]

    def find_by_tag(self, tag: str) -> List[PatternCard]:
        """Return all active cards that include the given tag."""
        tag_lower = tag.lower()
        return [c for c in self.all_active() if tag_lower in (t.lower() for t in c.tags)]

    def find_by_trigger(self, code_description: str) -> List[PatternCard]:
        """
        Return active cards whose trigger shapes are semantically similar to code_description.

        Uses TF-IDF cosine similarity (threshold=0.15) when scikit-learn is available.
        Falls back to keyword set-intersection when sklearn is not installed.
        Returns cards ranked by similarity score descending.
        """
        if not code_description.strip():
            return []

        if _SKLEARN_AVAILABLE and self._tfidf_matrix is not None:
            return self._find_by_trigger_tfidf(code_description)
        return self._find_by_trigger_keywords(code_description)

    # ---- Trigger search implementations -------------------------------------

    def _find_by_trigger_tfidf(self, code_description: str) -> List[PatternCard]:
        query_vec = self._tfidf_vectorizer.transform([code_description.lower()])
        scores = cosine_similarity(query_vec, self._tfidf_matrix)[0]
        active = self.all_active()
        scored = [
            (float(scores[i]), active[i])
            for i in range(len(active))
            if scores[i] >= _TFIDF_THRESHOLD
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [card for _, card in scored]

    def _find_by_trigger_keywords(self, code_description: str) -> List[PatternCard]:
        query_words = set(re.findall(r"\w+", code_description.lower()))
        scored: List[tuple[int, PatternCard]] = []
        for card in self.all_active():
            trigger_text = " ".join(card.trigger_shapes).lower()
            trigger_words = set(re.findall(r"\w+", trigger_text))
            score = len(query_words & trigger_words)
            if score > 0:
                scored.append((score, card))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [card for _, card in scored]

    def render_card(self, card: PatternCard) -> str:
        """Render a card to a human-readable markdown string."""
        signals = "\n".join(
            f"  - [{s['phase']}] {s['signal']}"
            for s in card.signal_sequence
        )
        countermeasures = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(card.countermeasures))
        sources = "\n".join(
            f"  - {s['title']} ({s['type']})"
            + (f" — {s['url']}" if s.get("url") else "")
            for s in card.sources
        )
        draft_warning = "\n> **DRAFT — not yet reviewed.**\n" if card.is_draft else ""

        return f"""\
**PATTERN: {card.name}**{draft_warning}
ID: {card.id} | CLASS: {card.pattern_class} | STATUS: {card.status}
TAGS: {', '.join(card.tags)}

TRIGGER SHAPES (check this pattern when you see):
{chr(10).join(f'  - {s}' for s in card.trigger_shapes)}

ACTIVATION: {card.activation}

MECHANISM: {card.mechanism}

SIGNAL SEQUENCE:
{signals}

LAG: {card.lag}
THRESHOLD: {card.threshold_estimated}

INVISIBLE BECAUSE: {card.invisible_because}

DIAGNOSTIC: {card.diagnostic}

COUNTERMEASURES:
{countermeasures}

SOURCES:
{sources}

Discovered: {card.discovered} | Last reviewed: {card.last_reviewed}
"""

    def render_index(self) -> str:
        """Render a compact index of all active cards."""
        lines = ["# Pattern Library — Active Cards\n"]
        for card in self.all_active():
            lines.append(f"- **{card.id}** — {card.name} `[{card.pattern_class}]`")
        if self.all_drafts():
            lines.append("\n## Drafts (not yet reviewed)\n")
            for card in self.all_drafts():
                lines.append(f"- **{card.id}** — {card.name} `[{card.pattern_class}]` DRAFT")
        return "\n".join(lines)

    # ---- Loading and validation ----------------------------------------------

    def _load_all(self, cards_dir: Path) -> None:
        violations: List[str] = []
        for path in sorted(p for p in cards_dir.glob("*.json")
                           if p.stem.upper() != "TEMPLATE"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                card = _validate_and_parse(raw, path)
                self._cards[card.id] = card
            except RegistryValidationError as err:
                violations.append(str(err))
            except (json.JSONDecodeError, OSError) as err:
                violations.append(f"{path.name}: {err}")

        if violations:
            raise RegistryValidationError(
                f"{len(violations)} card(s) failed validation:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )

    def _build_tfidf_index(self) -> None:
        """Build a TF-IDF matrix over all active cards' trigger shapes at load time."""
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None

        if not _SKLEARN_AVAILABLE:
            return

        active = self.all_active()
        if not active:
            return

        corpus = [
            " ".join(card.trigger_shapes).lower()
            for card in active
        ]
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        matrix = vectorizer.fit_transform(corpus)
        self._tfidf_vectorizer = vectorizer
        self._tfidf_matrix = matrix


# ---- Card parsing and validation --------------------------------------------

def _validate_and_parse(raw: object, path: Path) -> PatternCard:
    if not isinstance(raw, dict):
        raise RegistryValidationError(f"{path.name}: root must be a JSON object.")

    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise RegistryValidationError(f"{path.name}: missing required fields: {missing}")

    _check_enum(path, "class", raw["class"], ["architectural", "operational", "data", "security", "concurrency"])
    _check_enum(path, "status", raw["status"], ["DRAFT", "ACTIVE", "DEPRECATED"])
    _check_id_format(path, raw["id"])
    _check_signal_sequence(path, raw["signal_sequence"])
    _check_sources_have_postmortem_or_blog(path, raw["sources"])

    return PatternCard(
        id                  = raw["id"],
        name                = raw["name"],
        pattern_class       = raw["class"],
        status              = raw["status"],
        tags                = raw["tags"],
        trigger_shapes      = raw["trigger_shapes"],
        activation          = raw["activation"],
        mechanism           = raw["mechanism"],
        signal_sequence     = raw["signal_sequence"],
        lag                 = raw["lag"],
        threshold_estimated = raw["threshold_estimated"],
        invisible_because   = raw["invisible_because"],
        diagnostic          = raw["diagnostic"],
        countermeasures     = raw["countermeasures"],
        sources             = raw["sources"],
        discovered          = raw["discovered"],
        last_reviewed       = raw["last_reviewed"],
        alert_metadata      = raw.get("alert_metadata"),
    )


def _check_enum(path: Path, field_name: str, value: str, allowed: List[str]) -> None:
    if value not in allowed:
        raise RegistryValidationError(
            f"{path.name}: '{field_name}' is '{value}'; must be one of {allowed}."
        )


def _check_id_format(path: Path, pattern_id: str) -> None:
    if not re.match(r"^[A-Z][A-Z0-9_]+$", pattern_id):
        raise RegistryValidationError(
            f"{path.name}: id '{pattern_id}' must be SCREAMING_SNAKE_CASE."
        )


def _check_signal_sequence(path: Path, sequence: object) -> None:
    if not isinstance(sequence, list) or len(sequence) < 4:
        raise RegistryValidationError(
            f"{path.name}: signal_sequence must be a list with at least 4 entries."
        )
    for entry in sequence:
        if not isinstance(entry, dict) or "phase" not in entry or "signal" not in entry:
            raise RegistryValidationError(
                f"{path.name}: each signal_sequence entry must have 'phase' and 'signal'."
            )
        if entry["phase"] not in SIGNAL_PHASES_IN_ORDER:
            raise RegistryValidationError(
                f"{path.name}: signal phase '{entry['phase']}' is not valid. "
                f"Must be one of {SIGNAL_PHASES_IN_ORDER}."
            )


def _check_sources_have_postmortem_or_blog(path: Path, sources: object) -> None:
    if not isinstance(sources, list) or len(sources) == 0:
        raise RegistryValidationError(f"{path.name}: sources must be a non-empty list.")
    valid_types = {"postmortem", "engineering-blog", "documentation", "research", "book"}
    for source in sources:
        if not isinstance(source, dict) or "type" not in source:
            raise RegistryValidationError(f"{path.name}: each source must have a 'type' field.")
        if source["type"] not in valid_types:
            raise RegistryValidationError(
                f"{path.name}: source type '{source['type']}' is not valid. Must be one of {valid_types}."
            )
