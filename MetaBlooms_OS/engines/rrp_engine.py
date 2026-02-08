"""
MetaBlooms OS — RRP Engine (Recursive Refinement Protocol)

Rationale (CDR Pillar 1):
    Phases 4-5 of MPP. Evaluates BUILD outputs against schemas, CDR
    pillars, and success criteria. Rewrites only enumerated defects.
    Max 2 iterations with convergence test.

Constraints (CDR Pillar 2):
    - Optimizes for: quality improvement without scope creep
    - Sacrifices: unlimited iteration (bounded at 2)
    - Bound: only fixes enumerated defects, no new features
"""

import json
import os
from datetime import datetime, timezone


class RRPEngine:
    """Recursive Refinement Protocol — BUILD -> EVALUATE -> REWRITE."""

    MAX_ITERATIONS = 2

    def __init__(self, os_root):
        self.os_root = os_root
        self.iteration = 0
        self.evaluation_reports = []
        self.rewrite_reports = []

    def evaluate(self, artifacts, mastery_definition=None):
        """Phase 4: Read-only evaluation of BUILD outputs.

        Args:
            artifacts: list of {path, content_or_object}
            mastery_definition: optional, for mastery comparison

        Returns:
            evaluation report with defects
        """
        self.iteration += 1
        defects = []
        defect_counter = 0

        for artifact in artifacts:
            path = artifact.get("path", "unknown")
            content = artifact.get("content")

            # Check 1: JSON parseable (if .json)
            if path.endswith(".json") and isinstance(content, str):
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    defect_counter += 1
                    defects.append({
                        "defect_id": f"DEF-{defect_counter:03d}",
                        "severity": "CRITICAL",
                        "category": "SCHEMA_VIOLATION",
                        "artifact": path,
                        "description": f"Invalid JSON: {e}",
                        "location": "file"
                    })

            # Check 2: CDR rationale present (for .py files)
            if path.endswith(".py") and isinstance(content, str):
                if "Rationale" not in content and "rationale" not in content:
                    defect_counter += 1
                    defects.append({
                        "defect_id": f"DEF-{defect_counter:03d}",
                        "severity": "HIGH",
                        "category": "CDR_VIOLATION",
                        "artifact": path,
                        "description": "CDR-NORATIONALE: No rationale header found",
                        "location": "module header"
                    })

            # Check 3: Required fields (for JSON objects)
            if isinstance(content, dict):
                self._check_required_fields(content, path, defects, defect_counter)

        report = {
            "phase": "EVALUATE",
            "iteration": self.iteration,
            "artifacts_evaluated": [a.get("path") for a in artifacts],
            "defects": defects,
            "total_defects": len(defects),
            "scope_creep_items": [],
            "evaluated_utc": datetime.now(timezone.utc).isoformat()
        }

        self.evaluation_reports.append(report)
        return report

    def _check_required_fields(self, obj, path, defects, counter):
        """Check JSON object for common required fields."""
        # Mastery definitions need specific fields
        if "mastery_id" in obj:
            for field in ["task_description", "success_criteria", "constraints"]:
                if field not in obj:
                    counter += 1
                    defects.append({
                        "defect_id": f"DEF-{counter:03d}",
                        "severity": "HIGH",
                        "category": "MISSING_FIELD",
                        "artifact": path,
                        "description": f"Missing required field: {field}",
                        "location": f"root.{field}"
                    })

        # Decision records need specific fields
        if "decision_id" in obj:
            for field in ["constraints", "candidates", "selected", "rejections", "rationale"]:
                if field not in obj:
                    counter += 1
                    defects.append({
                        "defect_id": f"DEF-{counter:03d}",
                        "severity": "HIGH",
                        "category": "MISSING_FIELD",
                        "artifact": path,
                        "description": f"Missing required field: {field}",
                        "location": f"root.{field}"
                    })

    def should_rewrite(self, evaluation_report):
        """Check if rewrite is warranted and allowed.

        Returns:
            (should_rewrite: bool, reason: str)
        """
        if self.iteration > self.MAX_ITERATIONS:
            return False, f"Max iterations ({self.MAX_ITERATIONS}) reached"

        defects = evaluation_report.get("defects", [])
        if not defects:
            return False, "No defects found"

        # Convergence test: if this isn't the first iteration, check convergence
        if len(self.evaluation_reports) >= 2:
            prev_count = self.evaluation_reports[-2].get("total_defects", 0)
            curr_count = evaluation_report.get("total_defects", 0)
            if curr_count >= prev_count:
                return False, f"Not converging: {curr_count} >= {prev_count} defects"

        return True, f"{len(defects)} defects to fix"

    def plan_rewrite(self, evaluation_report):
        """Plan which defects to fix and in what order.

        Returns:
            list of defects to fix, ordered by severity
        """
        defects = evaluation_report.get("defects", [])
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(defects, key=lambda d: severity_order.get(d.get("severity"), 4))

    def record_rewrite(self, fixes_applied, defects_deferred=None, oscillating=None):
        """Record the results of a rewrite phase.

        Args:
            fixes_applied: [{defect_id, fix_description, artifacts_modified}]
            defects_deferred: [{defect_id, reason}]
            oscillating: [{defect_id}]
        """
        report = {
            "phase": "REWRITE",
            "iteration": self.iteration,
            "fixes_applied": fixes_applied or [],
            "defects_deferred": defects_deferred or [],
            "oscillating_defects": oscillating or [],
            "known_defects_remaining": [],
            "rewritten_utc": datetime.now(timezone.utc).isoformat()
        }
        self.rewrite_reports.append(report)
        return report

    def get_known_defects(self):
        """Get defects remaining after all iterations."""
        if not self.evaluation_reports:
            return []
        last_eval = self.evaluation_reports[-1]
        fixed_ids = set()
        for rr in self.rewrite_reports:
            for fix in rr.get("fixes_applied", []):
                fixed_ids.add(fix.get("defect_id"))
        return [
            d for d in last_eval.get("defects", [])
            if d["defect_id"] not in fixed_ids
        ]

    def emit_reports(self):
        """Write evaluation and rewrite reports to disk."""
        receipts_dir = os.path.join(self.os_root, "receipts")
        os.makedirs(receipts_dir, exist_ok=True)

        paths = []
        for report in self.evaluation_reports:
            path = os.path.join(receipts_dir, f"EVALUATION_REPORT_{report['iteration']}.json")
            with open(path, "w") as f:
                json.dump(report, f, indent=2)
            paths.append(path)

        for report in self.rewrite_reports:
            path = os.path.join(receipts_dir, f"REWRITE_REPORT_{report['iteration']}.json")
            with open(path, "w") as f:
                json.dump(report, f, indent=2)
            paths.append(path)

        return paths
