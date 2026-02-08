"""
MetaBlooms OS — Mastery Definition Engine

Rationale (CDR Pillar 1):
    Phase 0.5 of MPP. Before any work begins, this engine guides the
    creation of a MASTERY_DEFINITION that answers: "What does world-class
    look like for this task?" Without this, execution proceeds on vibes
    instead of defined criteria.

Constraints (CDR Pillar 2):
    - Optimizes for: forcing explicit success criteria before execution
    - Sacrifices: speed (mastery definition adds a phase before work begins)
    - Bound: must work without web access (sandbox limitation)

Failure modes (CDR Pillar 4):
    - No domain identified -> prompt user, don't guess
    - No success criteria defined -> FAIL CLOSED
    - Knowledge gaps remain OPEN after SEE -> FAIL CLOSED

Integration contract (CDR Pillar 5):
    - Assumes: StateManager available with prior mastery definitions
    - Inputs: task description from user
    - Outputs: MASTERY_DEFINITION.json conforming to schema
    - Side effects: stores in state for cross-session reuse
"""

import json
import os
from datetime import datetime, timezone


class MasteryEngine:
    """Builds and validates MASTERY_DEFINITION artifacts."""

    def __init__(self, os_root, state_manager):
        self.os_root = os_root
        self.state = state_manager
        self.schema = self._load_schema()

    def _load_schema(self):
        schema_path = os.path.join(self.os_root, "schemas", "MASTERY_DEFINITION.schema.json")
        if os.path.isfile(schema_path):
            with open(schema_path) as f:
                return json.load(f)
        return None

    def check_prior_mastery(self, domain):
        """Check if we have prior mastery definitions in this domain.
        Cross-session intelligence reuse: don't re-research what we already know."""
        similar = self.state.find_similar_mastery(domain)
        if similar:
            return {
                "found": True,
                "mastery_ids": similar,
                "definitions": {
                    mid: self.state.get_mastery_definition(mid)
                    for mid in similar
                }
            }
        return {"found": False, "mastery_ids": [], "definitions": {}}

    def create_mastery_definition(self, task_description, domain,
                                   best_practitioners, standards,
                                   world_class_standard, success_criteria,
                                   knowledge_gaps, constraints,
                                   see_queries_used):
        """Create a complete MASTERY_DEFINITION artifact.

        Args:
            task_description: What task this covers (min 20 chars)
            domain: The knowledge domain
            best_practitioners: [{name, why_relevant, source?}]
            standards: [{standard, claim_strength, source?}]
            world_class_standard: Plain-language description (min 20 chars)
            success_criteria: [{criterion_id, description, measurable, required, ...}]
            knowledge_gaps: [{gap_id, description, see_query, status, answer?}]
            constraints: {environmental: [], domain_specific: [], governance: []}
            see_queries_used: [str]
        """
        # Generate mastery_id
        mastery_id = f"MDEF-{domain.upper().replace(' ', '_')[:20]}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        definition = {
            "mastery_id": mastery_id,
            "task_description": task_description,
            "domain_research": {
                "domain": domain,
                "best_practitioners": best_practitioners,
                "standards_identified": standards,
                "see_queries_used": see_queries_used
            },
            "world_class_standard": world_class_standard,
            "success_criteria": success_criteria,
            "knowledge_gaps": knowledge_gaps,
            "constraints": constraints,
            "generated_utc": datetime.now(timezone.utc).isoformat()
        }

        # Validate
        errors = self.validate(definition)
        if errors:
            return None, errors

        # Store in state for cross-session reuse
        self.state.store_mastery_definition(definition)

        # Write to artifacts
        artifact_path = os.path.join(self.os_root, "artifacts", f"{mastery_id}.json")
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w") as f:
            json.dump(definition, f, indent=2)

        return definition, []

    def validate(self, definition):
        """Validate a mastery definition against requirements.
        Returns list of error strings (empty = valid)."""
        errors = []

        # Required fields
        required = ["mastery_id", "task_description", "domain_research",
                     "world_class_standard", "success_criteria",
                     "knowledge_gaps", "constraints"]
        for field in required:
            if field not in definition:
                errors.append(f"Missing required field: {field}")

        # Task description length
        if len(definition.get("task_description", "")) < 20:
            errors.append("task_description must be at least 20 characters")

        # World class standard length
        if len(definition.get("world_class_standard", "")) < 20:
            errors.append("world_class_standard must be at least 20 characters")

        # Success criteria must exist
        sc = definition.get("success_criteria", [])
        if not sc:
            errors.append("At least one success criterion is required")

        # Each criterion needs an ID and description
        for i, criterion in enumerate(sc):
            if "criterion_id" not in criterion:
                errors.append(f"Success criterion {i} missing criterion_id")
            if "description" not in criterion:
                errors.append(f"Success criterion {i} missing description")
            if "measurable" not in criterion:
                errors.append(f"Success criterion {i} missing measurable flag")
            if "required" not in criterion:
                errors.append(f"Success criterion {i} missing required flag")

        # Domain research
        dr = definition.get("domain_research", {})
        if not dr.get("domain"):
            errors.append("domain_research.domain is required")
        if not dr.get("see_queries_used"):
            errors.append("At least one SEE query must be recorded")

        # Constraints structure
        constraints = definition.get("constraints", {})
        for ctype in ["environmental", "domain_specific", "governance"]:
            if ctype not in constraints:
                errors.append(f"constraints.{ctype} is required")

        return errors

    def check_readiness(self, definition):
        """Check if mastery definition is ready for execution.
        Returns (ready: bool, blockers: list)."""
        blockers = []

        # Check for OPEN knowledge gaps
        for gap in definition.get("knowledge_gaps", []):
            if gap.get("status") == "OPEN":
                blockers.append(f"Knowledge gap {gap.get('gap_id')} is still OPEN: {gap.get('description')}")

        # Check all required success criteria have measurement methods
        for sc in definition.get("success_criteria", []):
            if sc.get("measurable") and not sc.get("measurement_method"):
                blockers.append(
                    f"Criterion {sc.get('criterion_id')} is measurable but has no measurement_method"
                )

        return len(blockers) == 0, blockers

    def compare_outputs(self, definition, outputs):
        """Phase 6: Compare execution outputs against mastery success criteria.

        Args:
            definition: The MASTERY_DEFINITION
            outputs: dict mapping criterion_id to {verdict, evidence}

        Returns:
            comparison result with per-criterion verdicts
        """
        results = []
        all_required_met = True

        for sc in definition.get("success_criteria", []):
            cid = sc["criterion_id"]
            output = outputs.get(cid, {})
            verdict = output.get("verdict", "NOT_MET")
            evidence = output.get("evidence", "No output provided")

            result = {
                "criterion_id": cid,
                "description": sc["description"],
                "required": sc.get("required", False),
                "verdict": verdict,
                "evidence": evidence
            }

            if sc.get("required") and verdict == "NOT_MET":
                all_required_met = False
                result["blocking"] = True

            results.append(result)

        return {
            "mastery_id": definition["mastery_id"],
            "comparison_utc": datetime.now(timezone.utc).isoformat(),
            "criteria_results": results,
            "all_required_met": all_required_met,
            "overall": "PASS" if all_required_met else "FAIL"
        }
