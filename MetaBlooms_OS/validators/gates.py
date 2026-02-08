"""
MetaBlooms OS — Validation Gates

Rationale (CDR Pillar 1):
    Mechanical checks that can be run independently of the LLM.
    Each gate returns PASS/FAIL with specific findings.
    Used by MPP preparation phase and self-verification.

Constraints (CDR Pillar 2):
    - Optimizes for: deterministic, repeatable validation
    - Sacrifices: nuanced judgment (gates are mechanical only)
    - Bound: pure Python, no external dependencies
"""

import json
import os
from datetime import datetime, timezone


class ValidationGates:
    """Collection of mechanical validation gates."""

    def __init__(self, os_root):
        self.os_root = os_root

    def run_all(self):
        """Run all gates, return combined result."""
        results = {}
        results["schema_existence"] = self.gate_schema_existence()
        results["policy_existence"] = self.gate_policy_existence()
        results["json_validity"] = self.gate_json_validity()
        results["state_integrity"] = self.gate_state_integrity()
        results["pattern_catalog"] = self.gate_pattern_catalog()

        overall = all(r["pass"] for r in results.values())
        return {
            "overall": "PASS" if overall else "FAIL",
            "gates": results,
            "validated_utc": datetime.now(timezone.utc).isoformat()
        }

    def gate_schema_existence(self):
        """Check that required schemas exist."""
        schema_dir = os.path.join(self.os_root, "schemas")
        required = [
            "MASTERY_DEFINITION.schema.json",
            "DECISION_RECORD.schema.json",
            "LESSON_PROMOTION.schema.json",
            "TURN_RECEIPT.schema.json",
            "MMD_REPORT.schema.json",
        ]
        missing = []
        for s in required:
            if not os.path.isfile(os.path.join(schema_dir, s)):
                missing.append(s)
        return {
            "pass": len(missing) == 0,
            "missing": missing,
            "total_checked": len(required)
        }

    def gate_policy_existence(self):
        """Check that required policy documents exist."""
        policy_dir = os.path.join(self.os_root, "policies")
        if not os.path.isdir(policy_dir):
            return {"pass": False, "missing": ["policies/ directory"], "total_checked": 0}

        policies = os.listdir(policy_dir)
        required_prefixes = ["MB_MASTER_SPEC", "CDR", "SEE_ENGINE", "RRP", "DELTAGATE"]
        missing = []
        for prefix in required_prefixes:
            if not any(p.startswith(prefix) for p in policies):
                missing.append(prefix)
        return {
            "pass": len(missing) == 0,
            "missing": missing,
            "total_checked": len(required_prefixes)
        }

    def gate_json_validity(self):
        """Check that all JSON files in artifacts/ and schemas/ parse."""
        invalid = []
        for subdir in ["artifacts", "schemas", "receipts"]:
            dirpath = os.path.join(self.os_root, subdir)
            if not os.path.isdir(dirpath):
                continue
            for fname in os.listdir(dirpath):
                if fname.endswith(".json"):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath) as f:
                            json.load(f)
                    except (json.JSONDecodeError, Exception) as e:
                        invalid.append({"file": f"{subdir}/{fname}", "error": str(e)})
        return {
            "pass": len(invalid) == 0,
            "invalid": invalid
        }

    def gate_state_integrity(self):
        """Check state file integrity."""
        state_path = os.path.join(self.os_root, "state", "MB_STATE.json")
        if not os.path.isfile(state_path):
            return {"pass": True, "note": "No state file (fresh session)"}
        try:
            with open(state_path) as f:
                state = json.load(f)
            required_keys = ["version", "sessions_count", "mastery_definitions",
                             "decision_records", "lesson_promotions"]
            missing = [k for k in required_keys if k not in state]
            return {
                "pass": len(missing) == 0,
                "missing_keys": missing,
                "version": state.get("version")
            }
        except Exception as e:
            return {"pass": False, "error": str(e)}

    def gate_pattern_catalog(self):
        """Check pattern catalog exists and is valid."""
        catalog_path = os.path.join(self.os_root, "patterns", "MB_PATTERN_CATALOG.json")
        if not os.path.isfile(catalog_path):
            return {"pass": False, "error": "Pattern catalog missing"}
        try:
            with open(catalog_path) as f:
                catalog = json.load(f)
            patterns = catalog.get("patterns", [])
            return {
                "pass": len(patterns) >= 1,
                "pattern_count": len(patterns),
                "version": catalog.get("version")
            }
        except Exception as e:
            return {"pass": False, "error": str(e)}
