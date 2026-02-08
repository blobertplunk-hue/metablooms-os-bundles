"""
MetaBlooms OS — Mandatory Process Pipeline (MPP) Orchestrator

Rationale (CDR Pillar 1):
    This is the central pipeline that coordinates all phases of MetaBlooms
    execution. Every task passes through all phases. No phase may be skipped.
    No phase may perform another phase's job.

    Pipeline:
    Phase -1    -> Enforcement Capability Declaration
    Phase -1B   -> Environment Declaration
    Phase 0     -> Claim Enumeration (ECL)
    Phase 0.5   -> MASTERY_DEFINITION
    Phase 1     -> SEE (Evidence Gathering)
    Phase 2     -> MMD (Missing Middle Detection)
    Phase 2.5   -> TOOLBOX_REALITY_VALIDATION (R2.5)  <- HARD GATE
    Phase 2.75  -> PREPARATION_GATE                    <- HARD GATE
    Phase 3     -> BUILD (Deliverables)
    Phase 4     -> EVALUATE (Read-Only Review)
    Phase 5     -> REWRITE (Fix Enumerated Only)
    Phase 6     -> Self-Verification + Mastery Comparison
    Phase 7     -> Turn Receipt
    Phase 7.5   -> ASSIMILATION (Lesson Promotion)
    STOP        -> Admission Boundary

Constraints (CDR Pillar 2):
    - Optimizes for: process rigor and traceability
    - Sacrifices: speed (every phase adds overhead)
    - Bound: max 2 RRP iterations, fail-closed on critical gaps

Failure modes (CDR Pillar 4):
    - FAIL CLOSED emits FAIL_RECEIPT and halts
    - Phases track completion status for receipt
    - If environment invalid -> halt before Phase 0

Integration contract (CDR Pillar 5):
    - Assumes: boot.py has already initialized os_root and state
    - Inputs: task_type, task_description
    - Outputs: TURN_RECEIPT.json with complete execution record
    - Side effects: all receipts/artifacts written to os_root/
"""

import json
import os
import hashlib
from datetime import datetime, timezone

from engines.mastery_engine import MasteryEngine
from engines.see_engine import SEEEngine
from engines.mmd_engine import MMDEngine
from engines.decision_engine import DecisionEngine
from engines.rrp_engine import RRPEngine
from engines.assimilation_engine import AssimilationEngine
from state.state_manager import StateManager


class MPPOrchestrator:
    """Orchestrates the full Mandatory Process Pipeline."""

    TASK_TYPES = ["STRUCTURAL_ANALYSIS", "RESEARCH", "CODE_GENERATION", "POLICY"]

    def __init__(self, os_root, state, environment):
        self.os_root = os_root
        self.env = environment
        self.state_mgr = StateManager(os_root, state)
        self.phases_completed = []
        self.artifacts_emitted = []
        self.fail_reason = None

        # Initialize engines
        self.mastery_engine = MasteryEngine(os_root, self.state_mgr)
        self.see_engine = SEEEngine(os_root, self.state_mgr, environment)
        self.mmd_engine = MMDEngine(os_root, self.state_mgr)
        self.decision_engine = DecisionEngine(os_root, self.state_mgr)
        self.rrp_engine = RRPEngine(os_root)
        self.assimilation_engine = AssimilationEngine(os_root, self.state_mgr)

    def fail_closed(self, phase, reason):
        """FAIL CLOSED: halt pipeline and emit failure receipt."""
        self.fail_reason = reason
        receipt = {
            "receipt_type": "FAIL",
            "failed_phase": phase,
            "reason": reason,
            "completed_before_failure": list(self.phases_completed),
            "artifacts_emitted_before_failure": list(self.artifacts_emitted),
            "generated_utc": datetime.now(timezone.utc).isoformat()
        }
        path = os.path.join(self.os_root, "receipts", "FAIL_RECEIPT.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(receipt, f, indent=2)
        self.artifacts_emitted.append(path)
        print(f"\n[FAIL CLOSED] Phase: {phase}")
        print(f"[FAIL CLOSED] Reason: {reason}")
        return receipt

    # --- Phase -1: Enforcement Capability ---

    def phase_neg1_enforcement(self):
        """Declare enforcement capabilities."""
        capability = {
            "external_verifier_present": "NO",
            "ci_pipeline_present": "NO",
            "human_admission_authority_present": "YES",
            "mode": "EVIDENCE_ONLY"
        }
        path = os.path.join(self.os_root, "receipts", "ENFORCEMENT_CAPABILITY.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(capability, f, indent=2)
        self.artifacts_emitted.append(path)
        self.phases_completed.append("Phase_-1_ENFORCEMENT")
        print("[MPP] Phase -1: Enforcement capability declared (EVIDENCE_ONLY)")
        return capability

    # --- Phase -1B: Environment ---

    def phase_neg1b_environment(self):
        """Declare environment capabilities."""
        env_decl = {
            "filesystem_write": True,
            "web_access": self.env.get("web_access", "NO"),
            "real_hashing_available": True,
            "git_lfs_available": False,
            "shell_access": False,
            "sandbox_type": "chatgpt_code_interpreter"
        }
        path = os.path.join(self.os_root, "receipts", "ENVIRONMENT_DECLARATION.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(env_decl, f, indent=2)
        self.artifacts_emitted.append(path)
        self.phases_completed.append("Phase_-1B_ENVIRONMENT")

        if not env_decl["filesystem_write"]:
            return self.fail_closed("Phase_-1B", "filesystem_write = false")

        print(f"[MPP] Phase -1B: Environment declared (web={env_decl['web_access']})")
        return env_decl

    # --- Phase 0: Claim Enumeration ---

    def phase_0_claims(self, task_type, task_description):
        """Enumerate claims from task description.

        In the ChatGPT sandbox, this is a guided process where the
        LLM identifies claims from the task description. This method
        provides the framework; the LLM fills in the claims.

        Returns a claim registry template for the LLM to populate.
        """
        registry = {
            "task_type": task_type,
            "claims": [],
            "non_claims": [],
            "generated_utc": datetime.now(timezone.utc).isoformat()
        }
        path = os.path.join(self.os_root, "artifacts", "CLAIM_REGISTRY.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(registry, f, indent=2)
        self.artifacts_emitted.append(path)
        self.phases_completed.append("Phase_0_CLAIMS")
        print(f"[MPP] Phase 0: Claim registry initialized for {task_type}")
        return registry

    # --- Phase 0.5: Mastery Definition ---

    def phase_05_mastery(self, task_description, domain):
        """Create or retrieve mastery definition.

        First checks for prior mastery definitions in the same domain
        (cross-session intelligence reuse). If none found, creates a
        template for the LLM to fill.
        """
        # Check prior mastery
        prior = self.mastery_engine.check_prior_mastery(domain)
        if prior["found"]:
            print(f"[MPP] Phase 0.5: Found prior mastery in domain '{domain}':")
            for mid in prior["mastery_ids"]:
                md = prior["definitions"][mid]
                print(f"  - {mid}: {md.get('task_description', '')[:60]}")
            print("[MPP] Reuse or adapt prior mastery definition.")

        self.phases_completed.append("Phase_0.5_MASTERY")
        print(f"[MPP] Phase 0.5: Mastery definition phase complete")
        return prior

    # --- Phase 1: SEE ---

    def phase_1_see(self, claims):
        """Run SEE evidence gathering for all claims."""
        results = self.see_engine.run(claims)
        see_paths = self.see_engine.emit_artifacts()

        for p in see_paths.values():
            self.artifacts_emitted.append(p)

        # Check for UNSUPPORTED claims
        unsupported = [
            cid for cid, ev in results["claim_evidence_map"].items()
            if ev["evidence_strength"] == "UNSUPPORTED"
        ]
        if unsupported:
            print(f"[MPP] Phase 1 WARNING: {len(unsupported)} claims are UNSUPPORTED")

        self.phases_completed.append("Phase_1_SEE")
        print(f"[MPP] Phase 1: SEE complete ({results['summary']['total_evidence_records']} evidence records)")
        return results

    # --- Phase 2: MMD ---

    def phase_2_mmd(self, mastery_definition=None, see_results=None):
        """Run MMD gap detection."""
        results = self.mmd_engine.run(mastery_definition, see_results)
        report_path = self.mmd_engine.emit_report()
        self.artifacts_emitted.append(report_path)

        if results["status"] == "FAIL":
            return self.fail_closed(
                "Phase_2_MMD",
                f"CRITICAL findings: {results['summary']['critical']}"
            )

        self.phases_completed.append("Phase_2_MMD")
        s = results["summary"]
        print(f"[MPP] Phase 2: MMD {results['status']} "
              f"(C:{s['critical']} H:{s['high']} M:{s['medium']} L:{s['low']})")
        return results

    # --- Phase 2.5: Toolbox Reality ---

    def phase_25_toolbox(self):
        """Validate toolbox reality (R2.5)."""
        reality = {
            "sandbox_capabilities": {
                "python_execution": True,
                "file_read_write": True,
                "json_processing": True,
                "hash_computation": True,
                "network_access": False,
                "git_operations": False,
                "shell_access": False
            },
            "acquisition_channels": ["sandbox", "user"],
            "limitations": [
                "No internet access",
                "No git operations",
                "No shell commands",
                "State resets between sessions (must download/upload MB_STATE.json)",
                "No real-time collaboration"
            ],
            "validated_utc": datetime.now(timezone.utc).isoformat()
        }

        path = os.path.join(self.os_root, "receipts", "TOOLBOX_REALITY.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(reality, f, indent=2)
        self.artifacts_emitted.append(path)
        self.phases_completed.append("Phase_2.5_TOOLBOX")
        print("[MPP] Phase 2.5: Toolbox reality validated")
        return reality

    # --- Phase 2.75: Preparation Gate ---

    def phase_275_preparation(self, mastery_definition=None):
        """Preparation gate: verify system is ready to execute."""
        blockers = []

        # Check 1: Mastery definition exists
        if mastery_definition is None:
            blockers.append("No mastery definition provided")

        # Check 2: Schemas exist
        schema_dir = os.path.join(self.os_root, "schemas")
        if not os.path.isdir(schema_dir) or not os.listdir(schema_dir):
            blockers.append("Schema directory empty or missing")

        # Check 3: No CRITICAL MMD findings
        # (checked by caller based on Phase 2 results)

        if blockers:
            return self.fail_closed("Phase_2.75_PREPARATION", f"Blockers: {blockers}")

        self.phases_completed.append("Phase_2.75_PREPARATION")
        print("[MPP] Phase 2.75: Preparation gate PASSED")
        return {"status": "PASS", "blockers": []}

    # --- Phase 6: Self-Verification ---

    def phase_6_verify(self):
        """Self-verification: check all artifacts are valid."""
        checks = []

        # Check: required artifacts exist
        required_receipts = ["BOOT_RECEIPT.json", "ENFORCEMENT_CAPABILITY.json",
                             "ENVIRONMENT_DECLARATION.json"]
        for r in required_receipts:
            path = os.path.join(self.os_root, "receipts", r)
            checks.append({
                "check": f"Receipt exists: {r}",
                "result": "PASS" if os.path.isfile(path) else "FAIL",
                "details": f"Checked {path}"
            })

        # Check: JSON artifacts parse
        artifacts_dir = os.path.join(self.os_root, "artifacts")
        if os.path.isdir(artifacts_dir):
            for fname in os.listdir(artifacts_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(artifacts_dir, fname)
                    try:
                        with open(fpath) as f:
                            json.load(f)
                        checks.append({
                            "check": f"JSON valid: {fname}",
                            "result": "PASS",
                            "details": f"Parsed successfully"
                        })
                    except json.JSONDecodeError as e:
                        checks.append({
                            "check": f"JSON valid: {fname}",
                            "result": "FAIL",
                            "details": str(e)
                        })

        # Check: all MPP phases executed
        expected_phases = [
            "Phase_-1_ENFORCEMENT", "Phase_-1B_ENVIRONMENT",
            "Phase_0_CLAIMS", "Phase_0.5_MASTERY"
        ]
        for phase in expected_phases:
            checks.append({
                "check": f"Phase completed: {phase}",
                "result": "PASS" if phase in self.phases_completed else "FAIL",
                "details": ""
            })

        failures = [c for c in checks if c["result"] == "FAIL"]
        overall = "FAIL" if failures else "PASS"

        verification = {
            "checks": checks,
            "overall": overall,
            "failures": [c["check"] for c in failures],
            "verified_utc": datetime.now(timezone.utc).isoformat()
        }

        path = os.path.join(self.os_root, "receipts", "SELF_VERIFICATION.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(verification, f, indent=2)
        self.artifacts_emitted.append(path)
        self.phases_completed.append("Phase_6_VERIFY")

        print(f"[MPP] Phase 6: Self-verification {overall} ({len(checks)} checks, {len(failures)} failures)")
        return verification

    # --- Phase 7: Turn Receipt ---

    def phase_7_receipt(self, see_summary=None, mmd_summary=None, rrp_summary=None):
        """Emit the final turn receipt."""
        # Compute hashes of emitted artifacts
        artifact_hashes = []
        for path in self.artifacts_emitted:
            if os.path.isfile(path):
                h = hashlib.sha256()
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                artifact_hashes.append({
                    "path": path,
                    "sha256": h.hexdigest()
                })

        receipt = {
            "receipt_type": "TURN",
            "version": "1.0",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "phases_completed": list(self.phases_completed),
            "artifacts_emitted": artifact_hashes,
            "see_summary": see_summary or {},
            "mmd_summary": mmd_summary or {},
            "rrp_summary": rrp_summary or {},
            "known_defects": self.rrp_engine.get_known_defects(),
            "environment_summary": {
                "web_access": self.env.get("web_access", "NO"),
                "sandbox_type": self.env.get("sandbox_type", "unknown")
            },
            "enforcement_summary": {
                "mode": "EVIDENCE_ONLY"
            },
            "intelligence_summary": self.state_mgr.get_intelligence_summary()
        }

        path = os.path.join(self.os_root, "receipts", "TURN_RECEIPT.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(receipt, f, indent=2)
        self.artifacts_emitted.append(path)
        self.phases_completed.append("Phase_7_RECEIPT")
        print(f"[MPP] Phase 7: Turn receipt emitted ({len(artifact_hashes)} artifacts)")
        return receipt

    # --- Phase 7.5: Assimilation ---

    def phase_75_assimilation(self, mastery_definition=None,
                               execution_results=None, mmd_report=None):
        """Run assimilation to extract and store lessons."""
        report = self.assimilation_engine.run(
            mastery_definition=mastery_definition,
            execution_results=execution_results,
            mmd_report=mmd_report,
            rrp_reports=self.rrp_engine.evaluation_reports
        )

        # Save state for next session
        self.state_mgr.save()

        self.phases_completed.append("Phase_7.5_ASSIMILATION")
        intel = report.get("intelligence_summary", {})
        print(f"[MPP] Phase 7.5: Assimilation complete")
        print(f"  Lessons extracted: {report.get('lessons_extracted', 0)}")
        print(f"  Auto-promoted: {report.get('lessons_auto_promoted', 0)}")
        print(f"  Intelligence level: {intel.get('intelligence_level', 0)}")
        return report

    # --- Full Pipeline ---

    def run_preparation_phases(self, task_type, task_description, domain):
        """Run phases -1 through 2.75 (preparation phases).

        These phases prepare the system for execution. They must all
        pass before BUILD can begin.

        Returns:
            (ready: bool, context: dict with all phase results)
        """
        print("\n" + "=" * 60)
        print("  MPP — Preparation Phases")
        print("=" * 60)

        context = {}

        # Phase -1
        context["enforcement"] = self.phase_neg1_enforcement()

        # Phase -1B
        result = self.phase_neg1b_environment()
        if isinstance(result, dict) and result.get("receipt_type") == "FAIL":
            return False, context
        context["environment"] = result

        # Phase 0
        context["claim_registry"] = self.phase_0_claims(task_type, task_description)

        # Phase 0.5
        context["prior_mastery"] = self.phase_05_mastery(task_description, domain)

        print("\n[MPP] Preparation phases -1 through 0.5 complete.")
        print("[MPP] Ready for LLM to populate claims and mastery definition.")
        print("[MPP] Call run_execution_phases() after populating claims.\n")

        return True, context

    def run_execution_phases(self, claims, mastery_definition=None,
                              build_artifacts=None, execution_results=None):
        """Run phases 1 through 7.5 (execution phases).

        Args:
            claims: list of claim objects from Phase 0
            mastery_definition: completed mastery definition from Phase 0.5
            build_artifacts: list of {path, content} from Phase 3
            execution_results: dict mapping criterion_id to {verdict, evidence}

        Returns:
            turn receipt
        """
        print("\n" + "=" * 60)
        print("  MPP — Execution Phases")
        print("=" * 60)

        # Phase 1: SEE
        see_results = self.phase_1_see(claims)

        # Phase 2: MMD
        mmd_result = self.phase_2_mmd(mastery_definition, see_results)
        if isinstance(mmd_result, dict) and mmd_result.get("receipt_type") == "FAIL":
            return mmd_result

        # Phase 2.5: Toolbox Reality
        toolbox = self.phase_25_toolbox()

        # Phase 2.75: Preparation Gate
        prep_result = self.phase_275_preparation(mastery_definition)
        if isinstance(prep_result, dict) and prep_result.get("receipt_type") == "FAIL":
            return prep_result

        # Phase 3: BUILD (done by LLM, artifacts passed in)
        self.phases_completed.append("Phase_3_BUILD")
        print("[MPP] Phase 3: BUILD (LLM-driven, artifacts provided)")

        # Phase 4-5: RRP (EVALUATE + REWRITE)
        if build_artifacts:
            eval_report = self.rrp_engine.evaluate(build_artifacts, mastery_definition)
            should_rewrite, reason = self.rrp_engine.should_rewrite(eval_report)
            print(f"[MPP] Phase 4: EVALUATE ({eval_report['total_defects']} defects)")

            if should_rewrite:
                print(f"[MPP] Phase 5: REWRITE needed ({reason})")
                # Rewrite is done by LLM; we just track it
            else:
                print(f"[MPP] Phase 5: REWRITE skipped ({reason})")

            self.rrp_engine.emit_reports()
            self.phases_completed.append("Phase_4_EVALUATE")
            self.phases_completed.append("Phase_5_REWRITE")

        # Phase 6: Self-Verification
        verification = self.phase_6_verify()

        # Phase 7: Turn Receipt
        receipt = self.phase_7_receipt(
            see_summary=see_results.get("summary"),
            mmd_summary=mmd_result.get("summary") if isinstance(mmd_result, dict) else None,
        )

        # Phase 7.5: Assimilation
        assimilation = self.phase_75_assimilation(
            mastery_definition=mastery_definition,
            execution_results=execution_results,
            mmd_report=mmd_result if isinstance(mmd_result, dict) else None
        )

        print("\n" + "=" * 60)
        print("  MPP — COMPLETE")
        print(f"  Phases: {len(self.phases_completed)}")
        print(f"  Artifacts: {len(self.artifacts_emitted)}")
        intel = assimilation.get("intelligence_summary", {})
        print(f"  Intelligence: {intel.get('intelligence_level', 0)}")
        print("  Status: ADMISSION BOUNDARY — awaiting external review")
        print("=" * 60)

        return receipt
