#!/usr/bin/env python3
# ECL:
#   id: MPP.PIPELINE.MAIN
#   role: entrypoint
#   owns: [the complete MPP pipeline — from PRVE through Governed Recursion]
#   does_not: [implement individual stage logic, fix code, write research artifacts]
#   inputs: [turn_dir: str — path to the current turn's artifact directory,
#            start_from: Optional[StageID] — for loop-back routing,
#            max_iterations: int — default 3]
#   outputs: [PipelineResult written to turn_dir/MPP_RESULT.json, exit code 0 (certified) or 1]
#   side_effects: [filesystem — writes receipts, loop artifacts, MPP_RESULT.json, MPP_CERTIFICATE.json]
#   failure_modes: [STAGE_FAILED → governed recursion handles it,
#                   MAX_ITERATIONS → escalation report emitted,
#                   IMPORT_ERROR → exit 1 with message]
#   invariants: [never exits 0 unless MPP_CERTIFICATE.json is written for this run,
#                always writes MPP_RESULT.json regardless of outcome]
#   evidence: [MPP_RESULT.json, MPP_CERTIFICATE.json (if certified)]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
MPP — Mandatory Process Pipeline
Entry Point

Intent:
    Orchestrate all 7 stages in order. Hand off to Governed Recursion
    when any stage fails. Emit a certificate when all stages pass.
    Never exit 0 without a certificate. Never exit silently on failure.

Usage:
    python -m mpp.mpp_pipeline --turn-dir /path/to/turn [--max-iterations 3] [--start-from S3_MMD]

Exit codes:
    0 — CERTIFIED (all stages passed, certificate written)
    1 — BLOCKED   (escalation report written, human action required)
    2 — ERROR     (pipeline itself could not run — check stderr)
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mpp.stages import StageID, StageResult
from mpp.stages import s1_prve, s2_see, s3_mmd, s4_cdr, s5_ecl, s6_test
from mpp.stages.s7_recursion import RecursionResult, run as run_recursion


# ---- Pipeline runner --------------------------------------------------------

def run_pipeline(turn_dir: str,
                 start_from: Optional[StageID] = None) -> List[StageResult]:
    """
    Run the pipeline stages in order, starting from start_from (or PRVE).
    Returns all StageResult objects in execution order.
    Stops at the first failing stage to preserve the fail-closed guarantee.
    """
    ordered_stages = [
        (StageID.PRVE, lambda: s1_prve.run(turn_dir)),
        (StageID.SEE,  lambda: s2_see.run(turn_dir)),
        (StageID.MMD,  lambda: s3_mmd.run(turn_dir)),
        (StageID.CDR,  lambda: s4_cdr.run(turn_dir)),
        (StageID.ECL,  lambda: s5_ecl.run(turn_dir)),
        (StageID.TEST, lambda: s6_test.run(turn_dir)),
    ]

    start_index = 0
    if start_from is not None:
        for i, (stage_id, _) in enumerate(ordered_stages):
            if stage_id == start_from:
                start_index = i
                break

    results: List[StageResult] = []
    for stage_id, runner in ordered_stages[start_index:]:
        result = runner()
        results.append(result)
        if not result.passed:
            break  # Fail-closed: stop at first failure

    return results


# ---- Main entry point -------------------------------------------------------

def main() -> int:
    args = _parse_args()
    turn_dir = args.turn_dir

    if not Path(turn_dir).exists():
        print(f"ERROR: turn directory '{turn_dir}' does not exist.", file=sys.stderr)
        return 2

    start_from: Optional[StageID] = None
    if args.start_from:
        try:
            start_from = StageID(args.start_from)
        except ValueError:
            valid = ", ".join(s.value for s in StageID)
            print(f"ERROR: unknown stage '{args.start_from}'. Valid: {valid}", file=sys.stderr)
            return 2

    print(f"\n{'='*60}")
    print(f"  MPP — Mandatory Process Pipeline")
    print(f"  Turn dir:       {turn_dir}")
    print(f"  Start from:     {start_from.value if start_from else 'S1_PRVE'}")
    print(f"  Max iterations: {args.max_iterations}")
    print(f"{'='*60}\n")

    recursion_result: RecursionResult = run_recursion(
        pipeline_runner = run_pipeline,
        turn_dir        = turn_dir,
        max_iterations  = args.max_iterations,
    )

    _write_result(turn_dir, recursion_result)
    _print_summary(recursion_result)

    return 0 if recursion_result.certified else 1


# ---- Reporting helpers ------------------------------------------------------

def _print_summary(result: RecursionResult) -> None:
    status = "CERTIFIED" if result.certified else "BLOCKED — ESCALATION REQUIRED"
    print(f"\n{'='*60}")
    print(f"  RESULT: {status}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Notes: {result.final_notes}")
    print(f"{'='*60}\n")

    for entry in result.history:
        icon = "✓" if entry["all_passed"] else "✗"
        print(f"  Iter {entry['iteration']} [{icon}] "
              f"start={entry['restart_from']}, "
              f"fail={entry['earliest_fail'] or 'none'}")

    if not result.certified:
        print("\n  → See loop/ESCALATION_REQUIRED.md for remediation steps.\n")
    else:
        print("\n  → MPP_CERTIFICATE.json written. Build authorized.\n")


def _write_result(turn_dir: str, result: RecursionResult) -> None:
    output = {
        "mpp_version":   "1.0.0",
        "turn_dir":      turn_dir,
        "certified":     result.certified,
        "iterations":    result.iterations,
        "final_notes":   result.final_notes,
        "history":       result.history,
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }
    out_path = Path(turn_dir) / "MPP_RESULT.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MPP — Mandatory Process Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stages (in order):
  S1_PRVE  — Pre-Build Research & Validation Engine
  S2_SEE   — Sandcrawler Evidence Engine
  S3_MMD   — Missing Middle Detector
  S4_CDR   — Code Delta Review
  S5_ECL   — Extraordinary Code Law
  S6_TEST  — Test Gate
  S7_*     — Governed Recursion (automatic, not a manual start point)
        """,
    )
    parser.add_argument(
        "--turn-dir", required=True,
        help="Path to the turn directory containing all MPP artifacts.",
    )
    parser.add_argument(
        "--max-iterations", type=int, default=3,
        help="Maximum governed recursion iterations before escalation (default: 3).",
    )
    parser.add_argument(
        "--start-from", default=None,
        help="Stage ID to start from (e.g. S3_MMD). Used internally by governed recursion.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
