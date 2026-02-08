"""
MetaBlooms OS — Assimilation Engine

Rationale (CDR Pillar 1):
    Phase 7.5 of MPP. After execution, this engine compares results
    to mastery criteria, extracts lessons, and promotes them through
    the OBSERVATION -> HYPOTHESIS -> CONSTRAINT -> INVARIANT lifecycle.
    This is how the system gets smarter across sessions.

Constraints (CDR Pillar 2):
    - Optimizes for: monotonic intelligence growth
    - Sacrifices: session speed (assimilation adds a phase after execution)
    - Bound: lessons must serialize to state file for cross-session persistence

Failure modes (CDR Pillar 4):
    - No mastery definition to compare against -> skip comparison, log warning
    - Lesson promotion without evidence -> rejected (stays at current level)
"""

import json
import os
from datetime import datetime, timezone


class AssimilationEngine:
    """Extracts and promotes lessons from execution results."""

    PROMOTION_LEVELS = ["OBSERVATION", "HYPOTHESIS", "CONSTRAINT", "INVARIANT"]

    def __init__(self, os_root, state_manager):
        self.os_root = os_root
        self.state = state_manager
        self._lesson_counter = len(state_manager.state.get("lesson_promotions", []))

    def compare_to_mastery(self, mastery_definition, execution_results):
        """Compare execution outputs to mastery success criteria.

        Args:
            mastery_definition: the MASTERY_DEFINITION used for this task
            execution_results: dict mapping criterion_id to {verdict, evidence}

        Returns:
            comparison with per-criterion verdicts and deltas
        """
        if not mastery_definition:
            return {"skipped": True, "reason": "No mastery definition provided"}

        criteria = mastery_definition.get("success_criteria", [])
        results = []
        deltas = []

        for criterion in criteria:
            cid = criterion["criterion_id"]
            result = execution_results.get(cid, {})
            verdict = result.get("verdict", "NOT_MET")
            evidence = result.get("evidence", "No output")

            entry = {
                "criterion_id": cid,
                "description": criterion["description"],
                "required": criterion.get("required", False),
                "expected": "MET",
                "actual": verdict,
                "evidence": evidence
            }

            if verdict != "MET":
                deltas.append({
                    "criterion_id": cid,
                    "delta_type": "EXPECTATION_GAP",
                    "expected": "MET",
                    "actual": verdict,
                    "description": f"Criterion {cid} was {verdict} instead of MET"
                })

            results.append(entry)

        all_required_met = all(
            r["actual"] == "MET" for r in results if r.get("required")
        )

        return {
            "mastery_id": mastery_definition.get("mastery_id"),
            "comparison_utc": datetime.now(timezone.utc).isoformat(),
            "criteria_results": results,
            "deltas": deltas,
            "all_required_met": all_required_met,
            "overall": "PASS" if all_required_met else "FAIL"
        }

    def extract_lessons(self, mmd_report, rrp_reports, mastery_comparison):
        """Extract lessons from execution artifacts.

        Sources of lessons:
        1. MMD findings that were unexpected
        2. RRP defects that revealed patterns
        3. Mastery comparison deltas
        4. Decision records that succeeded or failed

        Returns list of lesson objects at OBSERVATION level.
        """
        lessons = []

        # From MMD findings
        if mmd_report:
            for finding in mmd_report.get("findings", []):
                if finding.get("severity") in ("CRITICAL", "HIGH"):
                    self._lesson_counter += 1
                    lessons.append({
                        "lesson_id": f"LESSON-{self._lesson_counter:04d}",
                        "current_level": "OBSERVATION",
                        "source": f"MMD/{finding.get('finding_id')}",
                        "observation": finding.get("description"),
                        "category": finding.get("category"),
                        "session": self.state.state.get("sessions_count", 0),
                        "created_utc": datetime.now(timezone.utc).isoformat()
                    })

        # From RRP defects
        if rrp_reports:
            for report in rrp_reports:
                for defect in report.get("defects", []):
                    if defect.get("severity") in ("CRITICAL", "HIGH"):
                        self._lesson_counter += 1
                        lessons.append({
                            "lesson_id": f"LESSON-{self._lesson_counter:04d}",
                            "current_level": "OBSERVATION",
                            "source": f"RRP/{defect.get('defect_id')}",
                            "observation": defect.get("description"),
                            "category": defect.get("category"),
                            "session": self.state.state.get("sessions_count", 0),
                            "created_utc": datetime.now(timezone.utc).isoformat()
                        })

        # From mastery comparison deltas
        if mastery_comparison and not mastery_comparison.get("skipped"):
            for delta in mastery_comparison.get("deltas", []):
                self._lesson_counter += 1
                lessons.append({
                    "lesson_id": f"LESSON-{self._lesson_counter:04d}",
                    "current_level": "OBSERVATION",
                    "source": f"MASTERY_COMPARISON/{delta.get('criterion_id')}",
                    "observation": delta.get("description"),
                    "category": "MASTERY_GAP",
                    "session": self.state.state.get("sessions_count", 0),
                    "created_utc": datetime.now(timezone.utc).isoformat()
                })

        return lessons

    def promote_lesson(self, lesson_id, new_level, evidence, hypothesis=None,
                        constraint_text=None, invariant_checker=None):
        """Promote a lesson to the next level.

        Promotion path: OBSERVATION -> HYPOTHESIS -> CONSTRAINT -> INVARIANT

        Each promotion requires evidence:
        - OBSERVATION -> HYPOTHESIS: pattern observed multiple times
        - HYPOTHESIS -> CONSTRAINT: evidence confirms the hypothesis
        - CONSTRAINT -> INVARIANT: mechanical checker can verify

        Args:
            lesson_id: the lesson to promote
            new_level: target level
            evidence: list of evidence strings
            hypothesis: str (required for HYPOTHESIS level)
            constraint_text: str (required for CONSTRAINT level)
            invariant_checker: str (required for INVARIANT level)
        """
        current_idx = None
        new_idx = self.PROMOTION_LEVELS.index(new_level) if new_level in self.PROMOTION_LEVELS else None

        if new_idx is None:
            return False, f"Unknown promotion level: {new_level}"

        # Find the lesson in state
        for lesson in self.state.state.get("lesson_promotions", []):
            if lesson.get("lesson_id") == lesson_id:
                current_level = lesson.get("current_level", "OBSERVATION")
                current_idx = self.PROMOTION_LEVELS.index(current_level)
                break

        if current_idx is None:
            return False, f"Lesson {lesson_id} not found in state"

        if new_idx <= current_idx:
            return False, f"Cannot demote: {self.PROMOTION_LEVELS[current_idx]} -> {new_level}"

        if new_idx > current_idx + 1:
            return False, f"Cannot skip levels: {self.PROMOTION_LEVELS[current_idx]} -> {new_level}"

        if not evidence:
            return False, "Promotion requires evidence"

        # Level-specific requirements
        if new_level == "HYPOTHESIS" and not hypothesis:
            return False, "HYPOTHESIS promotion requires a hypothesis statement"
        if new_level == "CONSTRAINT" and not constraint_text:
            return False, "CONSTRAINT promotion requires a constraint text"
        if new_level == "INVARIANT" and not invariant_checker:
            return False, "INVARIANT promotion requires a mechanical checker reference"

        # Perform promotion
        success = self.state.promote_lesson(lesson_id, new_level, evidence)
        if success:
            # Update the lesson with level-specific data
            for lesson in self.state.state["lesson_promotions"]:
                if lesson.get("lesson_id") == lesson_id:
                    if hypothesis:
                        lesson["hypothesis"] = hypothesis
                    if constraint_text:
                        lesson["constraint_text"] = constraint_text
                    if invariant_checker:
                        lesson["invariant_checker"] = invariant_checker
                    break

        return success, "Promoted" if success else "Promotion failed"

    def auto_promote_recurring(self):
        """Automatically promote lessons that appear across multiple sessions.

        Rule: If the same category of observation appears in 3+ sessions,
        promote it to HYPOTHESIS with evidence = "Observed in N sessions."
        """
        lessons = self.state.state.get("lesson_promotions", [])
        observations = [l for l in lessons if l.get("current_level") == "OBSERVATION"]

        # Group by category
        categories = {}
        for obs in observations:
            cat = obs.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(obs)

        promotions = []
        for cat, obs_list in categories.items():
            sessions = set(o.get("session", 0) for o in obs_list)
            if len(sessions) >= 3:
                # Promote the first observation in this category
                target = obs_list[0]
                if target.get("current_level") == "OBSERVATION":
                    success, msg = self.promote_lesson(
                        target["lesson_id"],
                        "HYPOTHESIS",
                        evidence=[f"Observed in {len(sessions)} sessions: {sorted(sessions)}"],
                        hypothesis=f"Category '{cat}' is a recurring issue requiring structural attention"
                    )
                    if success:
                        promotions.append(target["lesson_id"])

        return promotions

    def run(self, mastery_definition=None, execution_results=None,
            mmd_report=None, rrp_reports=None):
        """Run full assimilation pipeline.

        Returns assimilation report.
        """
        # Step 1: Compare to mastery
        comparison = self.compare_to_mastery(mastery_definition, execution_results or {})

        # Step 2: Extract lessons
        lessons = self.extract_lessons(mmd_report, rrp_reports or [], comparison)

        # Step 3: Store lessons in state
        for lesson in lessons:
            self.state.store_lesson(lesson)

        # Step 4: Auto-promote recurring observations
        auto_promoted = self.auto_promote_recurring()

        # Step 5: Save state
        self.state.save()

        report = {
            "phase": "ASSIMILATION",
            "assimilation_utc": datetime.now(timezone.utc).isoformat(),
            "mastery_comparison": comparison,
            "lessons_extracted": len(lessons),
            "lessons_auto_promoted": len(auto_promoted),
            "intelligence_summary": self.state.get_intelligence_summary(),
            "lesson_ids": [l["lesson_id"] for l in lessons],
            "auto_promoted_ids": auto_promoted
        }

        # Write report
        receipts_dir = os.path.join(self.os_root, "receipts")
        os.makedirs(receipts_dir, exist_ok=True)
        report_path = os.path.join(receipts_dir, "ASSIMILATION_REPORT.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report
