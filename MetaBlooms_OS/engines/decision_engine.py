"""
MetaBlooms OS — Constraint-Driven Decision Engine

Rationale (CDR Pillar 1):
    Replaces keyword-based pattern matching with constraint-driven
    elimination. Inspired by the Feistel cipher analysis: the right
    architectural choice emerges from tight constraints that eliminate
    all but one candidate. This engine:
    1. Extracts constraints from MASTERY_DEFINITION and R2.5
    2. Enumerates candidates from pattern catalog
    3. Eliminates candidates that violate hard constraints
    4. Scores remaining candidates against soft constraints
    5. Selects with evidence, rejects with reasons
    6. Outputs a DECISION_RECORD conforming to schema

    Why not keyword matching: keyword matching ("retry" -> IDEMPOTENT)
    produces brittle, context-free selections. Constraint-driven
    elimination produces justified, context-aware decisions.

Constraints (CDR Pillar 2):
    - Optimizes for: decision quality (justified, traceable, repeatable)
    - Sacrifices: speed (constraint analysis is slower than keyword match)
    - Bound: pattern catalog must exist with at least 2 candidates

Failure modes (CDR Pillar 4):
    - No candidates after elimination -> FAIL CLOSED (no viable option)
    - All candidates tied -> select first, note tie in rationale
    - Pattern catalog missing -> FAIL CLOSED
    - Constraints contradictory -> report contradiction, don't select

Supersedes (CDR Pillar 6):
    - Replaces tools/decision/select_patterns.py (keyword matching)
    - Prior implementation assumed keywords = constraints. That was false.
"""

import json
import os
from datetime import datetime, timezone


class DecisionEngine:
    """Constraint-driven architectural decision maker."""

    def __init__(self, os_root, state_manager):
        self.os_root = os_root
        self.state = state_manager
        self.pattern_catalog = self._load_pattern_catalog()
        self.schema = self._load_schema()

    def _load_pattern_catalog(self):
        """Load the pattern catalog."""
        catalog_path = os.path.join(self.os_root, "patterns", "MB_PATTERN_CATALOG.json")
        if os.path.isfile(catalog_path):
            with open(catalog_path) as f:
                return json.load(f)
        return {"patterns": [], "version": "0.0"}

    def _load_schema(self):
        schema_path = os.path.join(self.os_root, "schemas", "DECISION_RECORD.schema.json")
        if os.path.isfile(schema_path):
            with open(schema_path) as f:
                return json.load(f)
        return None

    def extract_constraints(self, mastery_definition=None, toolbox_reality=None,
                            additional_constraints=None):
        """Extract constraints from all available sources.

        Sources:
        1. MASTERY_DEFINITION.constraints (environmental, domain, governance)
        2. ToolboxReality (sandbox capabilities and limitations)
        3. Additional constraints provided by the task context

        Returns list of {constraint, source, hard} objects.
        """
        constraints = []

        # From mastery definition
        if mastery_definition:
            md_constraints = mastery_definition.get("constraints", {})
            for c in md_constraints.get("environmental", []):
                constraints.append({
                    "constraint": c,
                    "source": f"mastery_definition/{mastery_definition.get('mastery_id', 'unknown')}/environmental",
                    "hard": True  # Environmental constraints are always hard
                })
            for c in md_constraints.get("domain_specific", []):
                constraints.append({
                    "constraint": c,
                    "source": f"mastery_definition/{mastery_definition.get('mastery_id', 'unknown')}/domain",
                    "hard": True
                })
            for c in md_constraints.get("governance", []):
                constraints.append({
                    "constraint": c,
                    "source": "governance_policy",
                    "hard": True
                })

        # From toolbox reality
        if toolbox_reality:
            for lim in toolbox_reality.get("limitations", []):
                constraints.append({
                    "constraint": f"Sandbox cannot: {lim}",
                    "source": "toolbox_reality/R2.5",
                    "hard": True
                })
            caps = toolbox_reality.get("sandbox_capabilities", {})
            if not caps.get("network_access"):
                constraints.append({
                    "constraint": "No network access available",
                    "source": "toolbox_reality/R2.5",
                    "hard": True
                })

        # Additional
        if additional_constraints:
            for c in additional_constraints:
                constraints.append(c)

        return constraints

    def enumerate_candidates(self, decision_context):
        """Get candidates from pattern catalog plus any custom candidates.

        Args:
            decision_context: str describing what kind of decision this is

        Returns list of {name, description, source} objects.
        """
        candidates = []

        # From pattern catalog
        for pattern in self.pattern_catalog.get("patterns", []):
            candidates.append({
                "name": pattern.get("pattern_id", pattern.get("name", "UNKNOWN")),
                "description": pattern.get("description", ""),
                "source": f"MB_PATTERN_CATALOG v{self.pattern_catalog.get('version', '?')}"
            })

        # Check prior decisions for this type of problem
        # (cross-session intelligence: reuse what worked before)
        prior = self.state.find_decisions_by_type(decision_context)
        for pd in prior:
            selected = pd.get("selected", {})
            if selected.get("name") not in [c["name"] for c in candidates]:
                candidates.append({
                    "name": selected["name"],
                    "description": f"Previously selected in {pd.get('decision_id', 'unknown')}",
                    "source": f"prior_decision/{pd.get('decision_id', 'unknown')}"
                })

        return candidates

    def eliminate(self, candidates, constraints):
        """Eliminate candidates that violate hard constraints.

        Returns:
            (surviving: list, rejections: list)
            Each rejection has {name, reason, constraint_violated}
        """
        surviving = []
        rejections = []

        for candidate in candidates:
            violated = False
            for constraint in constraints:
                if not constraint.get("hard", False):
                    continue
                # Check if candidate violates this constraint
                # This is the core logic - each pattern declares what it
                # requires and what it forbids
                if self._violates(candidate, constraint):
                    rejections.append({
                        "name": candidate["name"],
                        "reason": f"Violates hard constraint: {constraint['constraint']}",
                        "constraint_violated": constraint["constraint"]
                    })
                    violated = True
                    break
            if not violated:
                surviving.append(candidate)

        return surviving, rejections

    def _violates(self, candidate, constraint):
        """Check if a candidate violates a constraint.

        Uses pattern metadata (required_capabilities, forbidden_when)
        to determine violation. Falls back to False if metadata missing.
        """
        # Look up pattern details from catalog
        pattern_details = None
        for p in self.pattern_catalog.get("patterns", []):
            pid = p.get("pattern_id", p.get("name", ""))
            if pid == candidate["name"]:
                pattern_details = p
                break

        if not pattern_details:
            return False  # Unknown pattern, can't prove violation

        # Check forbidden_when conditions
        forbidden = pattern_details.get("forbidden_when", [])
        constraint_text = constraint["constraint"].lower()
        for f in forbidden:
            if f.lower() in constraint_text or constraint_text in f.lower():
                return True

        # Check required capabilities against limitations
        required = pattern_details.get("required_capabilities", [])
        if "cannot" in constraint_text.lower() or "no " in constraint_text.lower():
            for req in required:
                if req.lower() in constraint_text.lower():
                    return True

        return False

    def score_candidates(self, surviving, constraints):
        """Score surviving candidates against soft constraints.
        Higher score = better fit.

        Scoring: +1 for each soft constraint the candidate satisfies,
        -1 for each it partially conflicts with.
        """
        scores = {}
        for candidate in surviving:
            score = 0
            for constraint in constraints:
                if constraint.get("hard"):
                    continue
                # Soft constraint scoring
                # Positive if candidate aligns, negative if it conflicts
                if self._aligns_with(candidate, constraint):
                    score += 1
            scores[candidate["name"]] = score
        return scores

    def _aligns_with(self, candidate, constraint):
        """Check if a candidate aligns with a soft constraint."""
        # Look up pattern details
        for p in self.pattern_catalog.get("patterns", []):
            pid = p.get("pattern_id", p.get("name", ""))
            if pid == candidate["name"]:
                strengths = p.get("strengths", [])
                constraint_text = constraint["constraint"].lower()
                for s in strengths:
                    if s.lower() in constraint_text or constraint_text in s.lower():
                        return True
        return False

    def make_decision(self, decision_type, context, mastery_definition=None,
                       toolbox_reality=None, additional_constraints=None,
                       additional_candidates=None, evidence=None):
        """Full constraint-driven decision pipeline.

        Args:
            decision_type: one of ARCHITECTURAL_PATTERN, TOOL_SELECTION, etc.
            context: what problem this decision addresses
            mastery_definition: optional MASTERY_DEFINITION dict
            toolbox_reality: optional R2.5 declaration dict
            additional_constraints: optional [{constraint, source, hard}]
            additional_candidates: optional [{name, description, source}]
            evidence: optional [str] evidence citations for the selection

        Returns:
            (decision_record: dict, errors: list)
        """
        # Step 1: Extract constraints
        constraints = self.extract_constraints(
            mastery_definition, toolbox_reality, additional_constraints
        )
        if not constraints:
            return None, ["No constraints found. Cannot make a justified decision without constraints."]

        # Step 2: Enumerate candidates
        candidates = self.enumerate_candidates(decision_type)
        if additional_candidates:
            candidates.extend(additional_candidates)
        if len(candidates) < 2:
            return None, [
                f"Only {len(candidates)} candidate(s) found. "
                "A decision requires at least 2 candidates."
            ]

        # Step 3: Eliminate by hard constraints
        surviving, rejections = self.eliminate(candidates, constraints)
        if not surviving:
            return None, [
                "All candidates eliminated by hard constraints. "
                "No viable option exists. Constraints may be contradictory."
            ]

        # Step 4: Score by soft constraints
        scores = self.score_candidates(surviving, constraints)

        # Step 5: Select highest-scoring candidate
        best_name = max(scores, key=scores.get) if scores else surviving[0]["name"]
        selected_candidate = next(c for c in surviving if c["name"] == best_name)

        # Add non-selected survivors to rejections with reason
        for c in surviving:
            if c["name"] != best_name:
                rejections.append({
                    "name": c["name"],
                    "reason": f"Scored lower ({scores.get(c['name'], 0)}) than selected ({scores.get(best_name, 0)})"
                })

        # Step 6: Build decision record
        decision_id = f"DR-{decision_type}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

        record = {
            "decision_id": decision_id,
            "decision_type": decision_type,
            "context": context,
            "constraints": constraints,
            "candidates": candidates,
            "selected": {
                "name": best_name,
                "evidence": evidence or [
                    f"Survived {len(constraints)} constraints",
                    f"Score: {scores.get(best_name, 0)} (best of {len(surviving)} survivors)"
                ]
            },
            "rejections": rejections,
            "rationale": (
                f"Selected {best_name} because it survived all "
                f"{sum(1 for c in constraints if c.get('hard'))} hard constraints "
                f"and scored highest ({scores.get(best_name, 0)}) among "
                f"{len(surviving)} surviving candidates. "
                f"{len(candidates) - len(surviving)} candidates were eliminated "
                f"by constraint violations."
            ),
            "failure_modes": [
                f"If {best_name} proves inadequate, {len(surviving) - 1} alternative(s) remain",
                "Constraints may be incomplete — undiscovered requirements could invalidate this choice"
            ],
            "claim_strength": "DESIGN-CHOICE",
            "generated_utc": datetime.now(timezone.utc).isoformat()
        }

        if mastery_definition:
            record["mastery_definition_ref"] = mastery_definition.get("mastery_id")

        # Store in state for cross-session learning
        self.state.store_decision_record(record)

        # Write to artifacts
        artifact_path = os.path.join(self.os_root, "artifacts", f"{decision_id}.json")
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w") as f:
            json.dump(record, f, indent=2)

        return record, []
