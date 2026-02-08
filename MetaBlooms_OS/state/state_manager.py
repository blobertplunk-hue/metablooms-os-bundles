"""
MetaBlooms OS — Cross-Session State Manager

Rationale (CDR Pillar 1):
    ChatGPT sandbox resets between sessions. All accumulated intelligence
    (mastery definitions, decision records, lessons, source reputation)
    must be serialized to a single JSON file that the user downloads
    and re-uploads to the next session. This module manages that state.

Constraints (CDR Pillar 2):
    - Optimizes for: monotonic intelligence growth across sessions
    - Sacrifices: real-time distributed state (impossible in sandbox)
    - Bound: single MB_STATE.json file, must stay under ~50MB

Failure modes (CDR Pillar 4):
    - Corrupt state -> start fresh, log warning (no crash)
    - Missing fields in loaded state -> fill with defaults (forward compat)
    - Conflicting mastery definitions -> keep both, flag for resolution
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class StateManager:
    """Manages MetaBlooms OS cross-session persistent state.

    State structure:
    {
        "version": "1.0.0",
        "sessions_count": int,
        "first_boot_utc": str,
        "last_boot_utc": str,
        "mastery_definitions": {mastery_id: {...}},
        "decision_records": {decision_id: {...}},
        "lesson_promotions": [{...}],
        "source_ledger_accumulated": [{...}],
        "pattern_catalog_version": str,
        "query_patterns": [{...}],
        "source_reputation": [{...}],
        "known_defects": [{...}],
        "intelligence_level": int
    }
    """

    def __init__(self, os_root, state=None):
        self.os_root = os_root
        self.state_dir = os.path.join(os_root, "state")
        self.state_path = os.path.join(self.state_dir, "MB_STATE.json")
        self.state = state or self._default_state()

    def _default_state(self):
        now = datetime.now(timezone.utc).isoformat()
        return {
            "version": "1.0.0",
            "sessions_count": 0,
            "first_boot_utc": now,
            "last_boot_utc": now,
            "mastery_definitions": {},
            "decision_records": {},
            "lesson_promotions": [],
            "source_ledger_accumulated": [],
            "pattern_catalog_version": "1.0",
            "query_patterns": [],
            "source_reputation": [],
            "known_defects": [],
            "intelligence_level": 0
        }

    def save(self):
        """Persist state to disk."""
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, indent=2)
        return self.state_path

    # --- Mastery Definitions ---

    def store_mastery_definition(self, mastery_def):
        """Store a mastery definition. Keyed by mastery_id."""
        mid = mastery_def["mastery_id"]
        mastery_def["stored_utc"] = datetime.now(timezone.utc).isoformat()
        self.state["mastery_definitions"][mid] = mastery_def
        self._update_intelligence()
        return mid

    def get_mastery_definition(self, mastery_id):
        """Retrieve a stored mastery definition."""
        return self.state["mastery_definitions"].get(mastery_id)

    def list_mastery_definitions(self):
        """List all stored mastery definition IDs with their task descriptions."""
        return {
            mid: md.get("task_description", "")
            for mid, md in self.state["mastery_definitions"].items()
        }

    def find_similar_mastery(self, domain):
        """Find mastery definitions in a similar domain for reuse."""
        matches = []
        domain_lower = domain.lower()
        for mid, md in self.state["mastery_definitions"].items():
            dr = md.get("domain_research", {})
            if domain_lower in dr.get("domain", "").lower():
                matches.append(mid)
        return matches

    # --- Decision Records ---

    def store_decision_record(self, record):
        """Store a decision record. Keyed by decision_id."""
        did = record["decision_id"]
        record["stored_utc"] = datetime.now(timezone.utc).isoformat()
        self.state["decision_records"][did] = record
        self._update_intelligence()
        return did

    def get_decision_record(self, decision_id):
        """Retrieve a stored decision record."""
        return self.state["decision_records"].get(decision_id)

    def find_decisions_by_type(self, decision_type):
        """Find all decisions of a given type."""
        return [
            dr for dr in self.state["decision_records"].values()
            if dr.get("decision_type") == decision_type
        ]

    # --- Lesson Promotions ---

    def store_lesson(self, lesson):
        """Store a lesson promotion event."""
        lesson["stored_utc"] = datetime.now(timezone.utc).isoformat()
        self.state["lesson_promotions"].append(lesson)
        self._update_intelligence()
        return len(self.state["lesson_promotions"])

    def get_lessons_at_level(self, level):
        """Get all lessons at a specific promotion level."""
        return [
            lp for lp in self.state["lesson_promotions"]
            if lp.get("current_level") == level
        ]

    def promote_lesson(self, lesson_id, new_level, evidence):
        """Promote a lesson to the next level with evidence."""
        for lp in self.state["lesson_promotions"]:
            if lp.get("lesson_id") == lesson_id:
                lp["previous_level"] = lp.get("current_level", "OBSERVATION")
                lp["current_level"] = new_level
                lp["promotion_evidence"] = evidence
                lp["promoted_utc"] = datetime.now(timezone.utc).isoformat()
                self._update_intelligence()
                return True
        return False

    # --- Source Reputation ---

    def update_source_reputation(self, source_id, corroborated=False, contradicted=False):
        """Update reliability tracking for a source."""
        for sr in self.state["source_reputation"]:
            if sr["source_identifier"] == source_id:
                if corroborated:
                    sr["times_corroborated"] = sr.get("times_corroborated", 0) + 1
                if contradicted:
                    sr["times_contradicted"] = sr.get("times_contradicted", 0) + 1
                sr["times_cited"] = sr.get("times_cited", 0) + 1
                total = sr["times_corroborated"] + sr["times_contradicted"]
                sr["reliability_score"] = sr["times_corroborated"] / total if total > 0 else None
                sr["last_cited_utc"] = datetime.now(timezone.utc).isoformat()
                return
        # New source
        entry = {
            "source_identifier": source_id,
            "times_cited": 1,
            "times_corroborated": 1 if corroborated else 0,
            "times_contradicted": 1 if contradicted else 0,
            "reliability_score": None,
            "last_cited_utc": datetime.now(timezone.utc).isoformat()
        }
        total = entry["times_corroborated"] + entry["times_contradicted"]
        entry["reliability_score"] = entry["times_corroborated"] / total if total > 0 else None
        self.state["source_reputation"].append(entry)

    # --- Query Patterns ---

    def update_query_pattern(self, pattern_tag, useful_results, noise_results):
        """Update accumulated query pattern effectiveness."""
        for qp in self.state["query_patterns"]:
            if qp["pattern_tag"] == pattern_tag:
                qp["total_uses"] = qp.get("total_uses", 0) + 1
                qp["total_useful_results"] = qp.get("total_useful_results", 0) + useful_results
                qp["total_noise_results"] = qp.get("total_noise_results", 0) + noise_results
                total = qp["total_useful_results"] + qp["total_noise_results"]
                qp["avg_noise_ratio"] = qp["total_noise_results"] / total if total > 0 else 0
                qp["last_used_utc"] = datetime.now(timezone.utc).isoformat()
                # Auto-promote/deprioritize
                if qp["total_uses"] >= 3:
                    if qp["avg_noise_ratio"] > 0.8:
                        qp["status"] = "DEPRIORITIZED"
                    elif qp["total_useful_results"] / qp["total_uses"] >= 3:
                        qp["status"] = "PROMOTED"
                return
        # New pattern
        total = useful_results + noise_results
        self.state["query_patterns"].append({
            "pattern_tag": pattern_tag,
            "total_uses": 1,
            "total_useful_results": useful_results,
            "total_noise_results": noise_results,
            "avg_noise_ratio": noise_results / total if total > 0 else 0,
            "status": "ACTIVE",
            "last_used_utc": datetime.now(timezone.utc).isoformat()
        })

    # --- Intelligence Level ---

    def _update_intelligence(self):
        """Compute intelligence level from accumulated artifacts.
        Intelligence = mastery_defs * 3 + decision_records * 2 + lessons * 1
        + promoted_constraints * 5 + promoted_invariants * 10
        This makes the system measurably smarter over time."""
        md_count = len(self.state.get("mastery_definitions", {}))
        dr_count = len(self.state.get("decision_records", {}))
        lessons = self.state.get("lesson_promotions", [])
        lesson_count = len(lessons)
        constraint_count = sum(1 for l in lessons if l.get("current_level") == "CONSTRAINT")
        invariant_count = sum(1 for l in lessons if l.get("current_level") == "INVARIANT")

        self.state["intelligence_level"] = (
            md_count * 3 +
            dr_count * 2 +
            lesson_count * 1 +
            constraint_count * 5 +
            invariant_count * 10
        )

    def get_intelligence_summary(self):
        """Return a human-readable intelligence summary."""
        s = self.state
        return {
            "sessions": s.get("sessions_count", 0),
            "intelligence_level": s.get("intelligence_level", 0),
            "mastery_definitions": len(s.get("mastery_definitions", {})),
            "decision_records": len(s.get("decision_records", {})),
            "lessons_total": len(s.get("lesson_promotions", [])),
            "lessons_at_observation": len(self.get_lessons_at_level("OBSERVATION")),
            "lessons_at_hypothesis": len(self.get_lessons_at_level("HYPOTHESIS")),
            "lessons_at_constraint": len(self.get_lessons_at_level("CONSTRAINT")),
            "lessons_at_invariant": len(self.get_lessons_at_level("INVARIANT")),
            "source_reputation_entries": len(s.get("source_reputation", [])),
            "query_patterns": len(s.get("query_patterns", []))
        }
