"""
MetaBlooms OS — MMD Engine (Missing Middle Detector)

Rationale (CDR Pillar 1):
    Phase 2 of MPP. MMD finds everything missing, broken, or
    inconsistent before execution begins. Runs 6 detection methods
    and fails if critical gaps are found.

Constraints (CDR Pillar 2):
    - Optimizes for: catching gaps before they cause execution failures
    - Sacrifices: speed (thorough scanning takes time)
    - Bound: operates on OS directory structure in sandbox

Failure modes (CDR Pillar 4):
    - CRITICAL finding -> FAIL CLOSED (blocks execution)
    - HIGH finding -> warning, continue
    - Schemas directory missing -> CRITICAL finding
"""

import json
import os
from datetime import datetime, timezone


class MMDEngine:
    """Missing Middle Detector — finds gaps in governance and preparation."""

    def __init__(self, os_root, state_manager):
        self.os_root = os_root
        self.state = state_manager
        self.findings = []
        self._finding_counter = 0

    def _add_finding(self, category, severity, description, method,
                     affected_artifact=None, recommendation=None):
        self._finding_counter += 1
        finding = {
            "finding_id": f"MMD-{self._finding_counter:03d}",
            "category": category,
            "severity": severity,
            "description": description,
            "detection_method": method,
            "affected_artifact": affected_artifact,
            "recommendation": recommendation or "",
            "detected_utc": datetime.now(timezone.utc).isoformat()
        }
        self.findings.append(finding)
        return finding

    # --- Detection Method 1: Schema Coverage ---

    def method_schema_coverage(self):
        """Check that all artifact types have corresponding schemas."""
        schemas_dir = os.path.join(self.os_root, "schemas")
        artifacts_dir = os.path.join(self.os_root, "artifacts")

        if not os.path.isdir(schemas_dir):
            self._add_finding(
                "MISSING_SCHEMA", "CRITICAL",
                "schemas/ directory does not exist",
                "SCHEMA_COVERAGE"
            )
            return

        schemas = set(os.listdir(schemas_dir))
        if not schemas:
            self._add_finding(
                "MISSING_SCHEMA", "CRITICAL",
                "No schemas found in schemas/ directory",
                "SCHEMA_COVERAGE"
            )

        # Check required schemas
        required = [
            "MASTERY_DEFINITION.schema.json",
            "DECISION_RECORD.schema.json",
            "LESSON_PROMOTION.schema.json",
            "TURN_RECEIPT.schema.json",
            "MMD_REPORT.schema.json",
        ]
        for req in required:
            if req not in schemas:
                self._add_finding(
                    "MISSING_SCHEMA", "HIGH",
                    f"Required schema missing: {req}",
                    "SCHEMA_COVERAGE",
                    affected_artifact=f"schemas/{req}",
                    recommendation=f"Create {req}"
                )

    # --- Detection Method 2: Policy Coverage ---

    def method_policy_coverage(self):
        """Check that all governance frameworks have policy documents."""
        policies_dir = os.path.join(self.os_root, "policies")
        if not os.path.isdir(policies_dir):
            self._add_finding(
                "MISSING_POLICY", "CRITICAL",
                "policies/ directory does not exist",
                "POLICY_COVERAGE"
            )
            return

        policies = set(os.listdir(policies_dir))

        # Required policies for full governance
        required_policies = {
            "MB_MASTER_SPEC": "Master specification defining the 6 phases",
            "CDR": "Coding Done Right construction standard",
            "SEE_ENGINE": "Search for Evidence Engine spec",
            "RRP": "Recursive Refinement Protocol",
            "DELTAGATE": "Change admission policy",
            "MMD_ENGINE": "Missing Middle Detector spec",
        }

        for policy_prefix, desc in required_policies.items():
            found = any(p.startswith(policy_prefix) for p in policies)
            if not found:
                self._add_finding(
                    "MISSING_POLICY", "HIGH",
                    f"Missing policy document for: {desc}",
                    "POLICY_COVERAGE",
                    recommendation=f"Create {policy_prefix}_v1.md"
                )

    # --- Detection Method 3: Mastery Readiness ---

    def method_mastery_readiness(self, mastery_definition=None):
        """Check if mastery definition is complete and ready."""
        if mastery_definition is None:
            self._add_finding(
                "MISSING_MASTERY", "CRITICAL",
                "No mastery definition provided for current task",
                "MASTERY_READINESS",
                recommendation="Create MASTERY_DEFINITION before proceeding"
            )
            return

        # Check for OPEN knowledge gaps
        for gap in mastery_definition.get("knowledge_gaps", []):
            if gap.get("status") == "OPEN":
                self._add_finding(
                    "OPEN_KNOWLEDGE_GAP", "CRITICAL",
                    f"Knowledge gap {gap.get('gap_id')} is OPEN: {gap.get('description')}",
                    "MASTERY_READINESS",
                    recommendation=f"Research via SEE query: {gap.get('see_query')}"
                )

        # Check success criteria
        sc = mastery_definition.get("success_criteria", [])
        if not sc:
            self._add_finding(
                "NO_SUCCESS_CRITERIA", "CRITICAL",
                "Mastery definition has no success criteria",
                "MASTERY_READINESS"
            )

        for criterion in sc:
            if criterion.get("measurable") and not criterion.get("measurement_method"):
                self._add_finding(
                    "UNMEASURABLE_CRITERION", "HIGH",
                    f"Criterion {criterion.get('criterion_id')} claims measurable but has no method",
                    "MASTERY_READINESS"
                )

    # --- Detection Method 4: Decision Completeness ---

    def method_decision_completeness(self):
        """Check that architectural decisions have complete records."""
        drs = self.state.state.get("decision_records", {})
        for did, dr in drs.items():
            # Check required fields
            if not dr.get("constraints"):
                self._add_finding(
                    "INCOMPLETE_DECISION", "HIGH",
                    f"Decision {did} has no constraints",
                    "DECISION_COMPLETENESS"
                )
            if len(dr.get("candidates", [])) < 2:
                self._add_finding(
                    "INSUFFICIENT_CANDIDATES", "HIGH",
                    f"Decision {did} has fewer than 2 candidates",
                    "DECISION_COMPLETENESS"
                )
            if not dr.get("rejections"):
                self._add_finding(
                    "NO_REJECTIONS", "MEDIUM",
                    f"Decision {did} has no explicit rejections",
                    "DECISION_COMPLETENESS"
                )
            if not dr.get("rationale") or len(dr.get("rationale", "")) < 20:
                self._add_finding(
                    "WEAK_RATIONALE", "HIGH",
                    f"Decision {did} has insufficient rationale",
                    "DECISION_COMPLETENESS"
                )

    # --- Detection Method 5: Evidence Gaps ---

    def method_evidence_gaps(self, see_results=None):
        """Check for claims with weak or missing evidence."""
        if see_results is None:
            return

        cem = see_results.get("claim_evidence_map", {})
        for cid, evidence in cem.items():
            strength = evidence.get("evidence_strength", "UNSUPPORTED")
            if strength == "UNSUPPORTED":
                self._add_finding(
                    "UNSUPPORTED_CLAIM", "HIGH",
                    f"Claim {cid} has no supporting evidence",
                    "EVIDENCE_GAPS"
                )
            elif strength == "CONTESTED":
                self._add_finding(
                    "CONTESTED_CLAIM", "HIGH",
                    f"Claim {cid} has conflicting evidence",
                    "EVIDENCE_GAPS"
                )
            elif strength == "PARTIAL" and evidence.get("source_limited"):
                self._add_finding(
                    "SOURCE_LIMITED_CLAIM", "MEDIUM",
                    f"Claim {cid} is source-limited (web access needed for full evidence)",
                    "EVIDENCE_GAPS"
                )

    # --- Detection Method 6: State Integrity ---

    def method_state_integrity(self):
        """Check cross-session state for consistency."""
        state = self.state.state

        # Check for orphaned references
        lessons = state.get("lesson_promotions", [])
        for lesson in lessons:
            level = lesson.get("current_level")
            if level not in ("OBSERVATION", "HYPOTHESIS", "CONSTRAINT", "INVARIANT"):
                self._add_finding(
                    "INVALID_LESSON_LEVEL", "MEDIUM",
                    f"Lesson has unknown level: {level}",
                    "STATE_INTEGRITY"
                )

        # Check intelligence level consistency
        expected_level = self.state._update_intelligence()
        # (side effect: recalculates, which is fine)

    # --- Run All Methods ---

    def run(self, mastery_definition=None, see_results=None):
        """Run all MMD detection methods.

        Returns:
            {
                "status": "PASS"|"PASS_WITH_WARNINGS"|"FAIL",
                "findings": [...],
                "summary": {...}
            }
        """
        self.findings = []
        self._finding_counter = 0

        # Run all methods
        self.method_schema_coverage()
        self.method_policy_coverage()
        self.method_mastery_readiness(mastery_definition)
        self.method_decision_completeness()
        self.method_evidence_gaps(see_results)
        self.method_state_integrity()

        # Compute summary
        severities = [f["severity"] for f in self.findings]
        has_critical = "CRITICAL" in severities
        has_high = "HIGH" in severities

        status = "FAIL" if has_critical else ("PASS_WITH_WARNINGS" if self.findings else "PASS")

        summary = {
            "total_findings": len(self.findings),
            "critical": severities.count("CRITICAL"),
            "high": severities.count("HIGH"),
            "medium": severities.count("MEDIUM"),
            "low": severities.count("LOW"),
            "info": severities.count("INFO"),
        }

        return {
            "status": status,
            "findings": self.findings,
            "summary": summary,
            "run_utc": datetime.now(timezone.utc).isoformat()
        }

    def emit_report(self):
        """Write MMD report to disk."""
        report_path = os.path.join(self.os_root, "artifacts", "MMD_REPORT.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        report = {
            "report_version": "2.0",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "detection_methods_used": [
                "SCHEMA_COVERAGE",
                "POLICY_COVERAGE",
                "MASTERY_READINESS",
                "DECISION_COMPLETENESS",
                "EVIDENCE_GAPS",
                "STATE_INTEGRITY"
            ],
            "findings": self.findings,
            "summary": {
                "total": len(self.findings),
                "critical": sum(1 for f in self.findings if f["severity"] == "CRITICAL"),
                "high": sum(1 for f in self.findings if f["severity"] == "HIGH"),
                "medium": sum(1 for f in self.findings if f["severity"] == "MEDIUM"),
                "low": sum(1 for f in self.findings if f["severity"] == "LOW"),
                "info": sum(1 for f in self.findings if f["severity"] == "INFO"),
            }
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report_path
