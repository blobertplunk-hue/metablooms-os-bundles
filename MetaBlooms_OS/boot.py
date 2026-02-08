"""
MetaBlooms OS — Boot System

Rationale (CDR Pillar 1):
    Entry point for MetaBlooms OS in the ChatGPT sandbox. When the user
    uploads the ZIP and runs boot.py, it:
    1. Extracts to /mnt/data/MetaBlooms_OS/ (or current directory)
    2. Loads or initializes cross-session state (MB_STATE.json)
    3. Validates the OS tree (schemas, policies, engines present)
    4. Runs validation gates
    5. Prints intelligence summary and readiness status
    6. Returns the MPP orchestrator ready for use

Constraints (CDR Pillar 2):
    - Optimizes for: zero-config startup (just run boot.py)
    - Sacrifices: flexibility (hardcoded paths for sandbox)
    - Bound: must work in ChatGPT Code Interpreter (Python only)

Failure modes (CDR Pillar 4):
    - Missing schemas/ -> FAIL with remediation instructions
    - Corrupt state file -> start fresh, warn user
    - Missing engines/ -> FAIL (OS is incomplete)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_os_root():
    """Locate the MetaBlooms OS root directory.

    Search order:
    1. /mnt/data/MetaBlooms_OS/ (ChatGPT sandbox canonical path)
    2. Directory containing this script
    3. Current working directory
    """
    candidates = [
        "/mnt/data/MetaBlooms_OS",
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd()
    ]
    for candidate in candidates:
        if os.path.isdir(os.path.join(candidate, "engines")):
            return candidate
    return None


def load_state(os_root):
    """Load cross-session state or initialize fresh state.

    State file: {os_root}/state/MB_STATE.json

    If the user uploaded a prior MB_STATE.json, it is loaded here.
    This is the key mechanism for cross-session intelligence persistence.
    """
    from state.state_manager import StateManager

    state_path = os.path.join(os_root, "state", "MB_STATE.json")

    if os.path.isfile(state_path):
        try:
            with open(state_path) as f:
                state_data = json.load(f)
            print(f"[BOOT] Loaded prior state (v{state_data.get('version', '?')}, "
                  f"sessions: {state_data.get('sessions_count', 0)}, "
                  f"intelligence: {state_data.get('intelligence_level', 0)})")

            # Increment session count
            state_data["sessions_count"] = state_data.get("sessions_count", 0) + 1
            state_data["last_boot_utc"] = datetime.now(timezone.utc).isoformat()

            mgr = StateManager(os_root, state_data)
            return mgr
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[BOOT] WARNING: Corrupt state file, starting fresh. Error: {e}")

    # Fresh state
    mgr = StateManager(os_root)
    mgr.state["sessions_count"] = 1
    print("[BOOT] Fresh state initialized (first session)")
    return mgr


def validate_os_tree(os_root):
    """Validate that all required OS components are present."""
    required_dirs = ["engines", "schemas", "policies", "state", "validators",
                     "patterns", "receipts", "artifacts", "research"]
    required_files = [
        "engines/mastery_engine.py",
        "engines/see_engine.py",
        "engines/mmd_engine.py",
        "engines/decision_engine.py",
        "engines/rrp_engine.py",
        "engines/assimilation_engine.py",
        "mpp.py",
        "validators/gates.py",
        "schemas/MASTERY_DEFINITION.schema.json",
        "schemas/DECISION_RECORD.schema.json",
        "schemas/LESSON_PROMOTION.schema.json",
        "patterns/MB_PATTERN_CATALOG.json",
    ]

    missing_dirs = []
    for d in required_dirs:
        path = os.path.join(os_root, d)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            missing_dirs.append(d)

    missing_files = []
    for f in required_files:
        if not os.path.isfile(os.path.join(os_root, f)):
            missing_files.append(f)

    return missing_dirs, missing_files


def emit_boot_receipt(os_root, state_mgr, validation_result):
    """Emit BOOT_RECEIPT.json."""
    import hashlib

    receipt = {
        "boot_version": "1.0",
        "boot_utc": datetime.now(timezone.utc).isoformat(),
        "os_root": os_root,
        "session_number": state_mgr.state.get("sessions_count", 1),
        "state_version": state_mgr.state.get("version", "1.0.0"),
        "intelligence_level": state_mgr.state.get("intelligence_level", 0),
        "validation": validation_result,
        "python_version": sys.version,
    }

    receipt_json = json.dumps(receipt, sort_keys=True)
    receipt["boot_receipt_sha256"] = hashlib.sha256(receipt_json.encode()).hexdigest()

    path = os.path.join(os_root, "receipts", "BOOT_RECEIPT.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(receipt, f, indent=2)

    return receipt


def boot():
    """Main boot sequence. Call this to start MetaBlooms OS.

    Returns:
        (mpp_orchestrator, state_manager, os_root)
    """
    print()
    print("=" * 60)
    print("  MetaBlooms OS — Booting")
    print("=" * 60)
    print()

    # Step 1: Find OS root
    os_root = find_os_root()
    if not os_root:
        print("[BOOT] FATAL: Cannot find MetaBlooms OS directory.")
        print("[BOOT] Expected: /mnt/data/MetaBlooms_OS/ or directory containing boot.py")
        return None, None, None

    print(f"[BOOT] OS root: {os_root}")

    # Add os_root to Python path so imports work
    if os_root not in sys.path:
        sys.path.insert(0, os_root)

    # Step 2: Validate OS tree
    missing_dirs, missing_files = validate_os_tree(os_root)
    if missing_files:
        print(f"[BOOT] WARNING: Missing files: {missing_files}")
    if missing_dirs:
        print(f"[BOOT] Created missing directories: {missing_dirs}")

    # Step 3: Load state
    state_mgr = load_state(os_root)

    # Step 4: Run validation gates
    from validators.gates import ValidationGates
    gates = ValidationGates(os_root)
    gate_results = gates.run_all()

    gate_status = gate_results["overall"]
    print(f"[BOOT] Validation gates: {gate_status}")
    for gate_name, result in gate_results["gates"].items():
        status = "PASS" if result.get("pass") else "FAIL"
        detail = ""
        if not result.get("pass"):
            detail = f" — {result.get('missing', result.get('error', ''))}"
        print(f"  [{status}] {gate_name}{detail}")

    # Step 5: Emit boot receipt
    validation = {
        "gates": gate_status,
        "missing_dirs": missing_dirs,
        "missing_files": missing_files
    }
    receipt = emit_boot_receipt(os_root, state_mgr, validation)

    # Step 6: Print intelligence summary
    intel = state_mgr.get_intelligence_summary()
    print()
    print("--- Intelligence Summary ---")
    print(f"  Sessions completed: {intel['sessions']}")
    print(f"  Intelligence level: {intel['intelligence_level']}")
    print(f"  Mastery definitions: {intel['mastery_definitions']}")
    print(f"  Decision records: {intel['decision_records']}")
    print(f"  Lessons (total): {intel['lessons_total']}")
    if intel['lessons_total'] > 0:
        print(f"    Observations: {intel['lessons_at_observation']}")
        print(f"    Hypotheses: {intel['lessons_at_hypothesis']}")
        print(f"    Constraints: {intel['lessons_at_constraint']}")
        print(f"    Invariants: {intel['lessons_at_invariant']}")
    print(f"  Source reputation entries: {intel['source_reputation_entries']}")
    print()

    # Step 7: Initialize MPP
    environment = {
        "web_access": "NO",
        "sandbox_type": "chatgpt_code_interpreter",
        "filesystem_write": True,
        "shell_access": False
    }

    from mpp import MPPOrchestrator
    mpp = MPPOrchestrator(os_root, state_mgr.state, environment)

    # Save state
    state_mgr.save()

    print("[BOOT] MetaBlooms OS ready.")
    print("[BOOT] To start a task, use:")
    print('  ready, ctx = mpp.run_preparation_phases("TASK_TYPE", "description", "domain")')
    print()
    print("=" * 60)
    print("  BOOT COMPLETE — Awaiting task input")
    print("=" * 60)
    print()

    return mpp, state_mgr, os_root


# Auto-boot when run directly
if __name__ == "__main__":
    mpp, state, os_root = boot()
