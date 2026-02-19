#!/usr/bin/env python3
# ECL:
#   id: GVN.PIPELINE.MAIN
#   role: entrypoint
#   owns: [the complete governed pipeline — GVN wrapping MPP, in the correct order]
#   does_not: [implement individual stage logic, substitute for human judgment]
#   inputs: [turn_dir: str, max_iterations: int, skip_governor: bool (for first runs)]
#   outputs: [GovernedResult written to gov/GOV_RESULT.json, exit code 0 (certified) or 1]
#   side_effects: [filesystem — all governance receipts, MPP artifacts, governor log, result file]
#   failure_modes: [GOV_STAGE_BLOCKED → pipeline does not start,
#                   MPP_ESCALATED → governed recursion handles it,
#                   G3_CRITICAL → pipeline health intervention required]
#   invariants: [G0 always runs before PRVE, G1 always runs before CDR,
#                G2 always runs before TEST, G3 always runs last,
#                exit code 0 only when MPP certified AND all governance stages passed]
#   evidence: [gov/GOV_RESULT.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
GVN + MPP — Full Governed Pipeline
Entry Point

Execution order:
    G0 (Context Brief) → PRVE → SEE → G1 (Adversarial MMD) → MMD → CDR
    → ECL → G2 (Behavior Review) → TEST → Governed Recursion → G3 (Governor)

Intent:
    G0 ensures the pipeline has real domain context before it starts.
    G1 injects adversarial gaps before CDR locks the plan.
    G2 validates test quality before TEST runs coverage.
    G3 monitors pipeline health across all runs.

    Every governance stage that fails stops the pipeline.
    G3 is the only governance stage that warns without blocking
    (except for CRITICAL signals, which always block).

Usage:
    python -m mpp.governance.gov_pipeline --turn-dir /path/to/turn [--max-iterations 3]

Exit codes:
    0 — CERTIFIED (governance + MPP both passed)
    1 — BLOCKED   (governance or MPP blocked; see receipts)
    2 — ERROR     (pipeline could not run; check stderr)
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mpp.governance.gov_types import GovSeverity, GovStageResult
from mpp.governance import g0_context_brief, g1_adversarial_mmd, g2_behavior_review, g3_governor
from mpp.governance.pattern_context import load_pattern_context
from mpp.stages import StageID, StageResult
from mpp.stages import s1_prve, s2_see, s3_mmd, s4_cdr, s5_ecl, s6_test
from mpp.stages.s7_recursion import RecursionResult, run as run_recursion


def main() -> int:
    args     = _parse_args()
    turn_dir = args.turn_dir

    if not Path(turn_dir).exists():
        print(f"ERROR: turn directory '{turn_dir}' does not exist.", file=sys.stderr)
        return 2

    _print_header(turn_dir, args.max_iterations)

    gov_results: List[GovStageResult] = []
    mpp_result:  Optional[RecursionResult] = None

    # ---- G0: Context Brief (must pass before PRVE) --------------------------
    g0_result = g0_context_brief.run(turn_dir)
    gov_results.append(g0_result)
    _print_stage(g0_result.stage.value, g0_result.passed, g0_result.notes)

    if not g0_result.passed:
        return _exit_blocked(turn_dir, gov_results, mpp_result,
                             "G0_CONTEXT_BRIEF blocked. Fix the context brief before proceeding.")

    _print_pattern_context_summary(turn_dir)

    # ---- MPP S1–S2 (PRVE, SEE) ----------------------------------------------
    s1 = s1_prve.run(turn_dir)
    s2 = s2_see.run(turn_dir)
    _print_stage(s1.stage.value, s1.passed, s1.notes)
    _print_stage(s2.stage.value, s2.passed, s2.notes)

    if not s1.passed:
        return _exit_blocked(turn_dir, gov_results, mpp_result,
                             "PRVE blocked. Address research artifacts before proceeding.")
    if not s2.passed:
        return _exit_blocked(turn_dir, gov_results, mpp_result,
                             "SEE blocked. Cite all claims before proceeding.")

    # ---- G1: Adversarial MMD (must pass before MMD gate and CDR) ------------
    g1_result = g1_adversarial_mmd.run(turn_dir)
    gov_results.append(g1_result)
    _print_stage(g1_result.stage.value, g1_result.passed, g1_result.notes)

    if not g1_result.passed:
        return _exit_blocked(turn_dir, gov_results, mpp_result,
                             "G1_ADVERSARIAL_MMD blocked. Complete adversarial review before MMD gate.")

    # ---- MPP S3–S5 (MMD, CDR, ECL) -----------------------------------------
    s3 = s3_mmd.run(turn_dir)
    s4 = s4_cdr.run(turn_dir)
    s5 = s5_ecl.run(turn_dir)
    for stage in (s3, s4, s5):
        _print_stage(stage.stage.value, stage.passed, stage.notes)
        if not stage.passed:
            return _exit_blocked(
                turn_dir, gov_results, mpp_result,
                f"{stage.stage.value} blocked. See receipts/ for details."
            )

    # ---- G2: Behavior Review (must pass before TEST) ------------------------
    g2_result = g2_behavior_review.run(turn_dir)
    gov_results.append(g2_result)
    _print_stage(g2_result.stage.value, g2_result.passed, g2_result.notes)

    if not g2_result.passed:
        return _exit_blocked(turn_dir, gov_results, mpp_result,
                             "G2_BEHAVIOR_REVIEW blocked. Resolve test quality issues before running tests.")

    # ---- MPP S6 + Governed Recursion ----------------------------------------
    def pipeline_runner_from_s6(turn_dir: str,
                                 start_from: Optional[StageID]) -> List[StageResult]:
        """
        Governed recursion loops only over the MPP stages (S1–S6).
        Governance stages (G0–G2) do not re-run in the loop —
        they must be fixed manually between iterations.
        """
        stages = [
            (StageID.PRVE, lambda: s1_prve.run(turn_dir)),
            (StageID.SEE,  lambda: s2_see.run(turn_dir)),
            (StageID.MMD,  lambda: s3_mmd.run(turn_dir)),
            (StageID.CDR,  lambda: s4_cdr.run(turn_dir)),
            (StageID.ECL,  lambda: s5_ecl.run(turn_dir)),
            (StageID.TEST, lambda: s6_test.run(turn_dir)),
        ]
        start_index = 0
        if start_from:
            for i, (sid, _) in enumerate(stages):
                if sid == start_from:
                    start_index = i
                    break
        results = []
        for _, runner in stages[start_index:]:
            result = runner()
            results.append(result)
            if not result.passed:
                break
        return results

    mpp_result = run_recursion(
        pipeline_runner = pipeline_runner_from_s6,
        turn_dir        = turn_dir,
        max_iterations  = args.max_iterations,
    )
    _print_stage("S6→RECURSION", mpp_result.certified, mpp_result.final_notes)

    # ---- G3: Governor Loop --------------------------------------------------
    if not args.skip_governor:
        g3_result = g3_governor.run(turn_dir)
        gov_results.append(g3_result)
        _print_stage(g3_result.stage.value, g3_result.passed, g3_result.notes)
        if not g3_result.passed:
            return _exit_blocked(turn_dir, gov_results, mpp_result,
                                 "G3_GOVERNOR detected systemic pipeline health issues.")
    else:
        print("  [G3 skipped — first run, no history to analyze]")

    # ---- Final verdict -------------------------------------------------------
    if mpp_result.certified:
        _write_gov_result(turn_dir, gov_results, mpp_result, certified=True)
        _print_certified(mpp_result.iterations)
        return 0
    else:
        return _exit_blocked(turn_dir, gov_results, mpp_result,
                             "MPP escalated without certification.")


# ---- Output helpers ---------------------------------------------------------

def _print_pattern_context_summary(turn_dir: str) -> None:
    """Print the G0 lint summary so the operator sees what risks were detected."""
    ctx = load_pattern_context(turn_dir)
    if ctx is None or not ctx.detected:
        print("  [Pattern lint] No architectural risk patterns detected in Context Brief.")
        return
    print(f"\n  [Pattern lint] {len(ctx.detected)} risk(s) detected:")
    for p in ctx.detected:
        risk = p.severity_label.upper()
        chain = " → ".join([p.pattern_id] + p.cascade_chain) if p.cascade_chain else p.pattern_id
        print(f"    {risk:8}  {chain}")
    if ctx.block_patterns:
        print(f"\n  [Pattern lint] {len(ctx.block_patterns)} block-risk pattern(s) —")
        print(f"  [Pattern lint] PRVE, G1, MMD, and G2 will enforce cascade coverage.")
    print()


def _print_header(turn_dir: str, max_iterations: int) -> None:
    print(f"\n{'='*60}")
    print(f"  GVN + MPP — Full Governed Pipeline")
    print(f"  Turn dir:       {turn_dir}")
    print(f"  Max iterations: {max_iterations}")
    print(f"{'='*60}")
    print(f"\n  {'Stage':<30} {'Status'}")
    print(f"  {'-'*45}")


def _print_stage(stage_name: str, passed: bool, notes: str) -> None:
    icon   = "✓" if passed else "✗"
    status = "PASS" if passed else "BLOCKED"
    print(f"  {icon} {stage_name:<30} {status}")
    if not passed:
        print(f"    → {notes}")


def _print_certified(iterations: int) -> None:
    print(f"\n{'='*60}")
    print(f"  RESULT: CERTIFIED")
    print(f"  Iterations: {iterations}")
    print(f"  gov/GOV_RESULT.json written.")
    print(f"  MPP_CERTIFICATE.json written.")
    print(f"{'='*60}\n")


def _exit_blocked(turn_dir: str, gov_results: List[GovStageResult],
                  mpp_result: Optional[RecursionResult], reason: str) -> int:
    print(f"\n{'='*60}")
    print(f"  RESULT: BLOCKED")
    print(f"  Reason: {reason}")
    print(f"{'='*60}\n")
    _write_gov_result(turn_dir, gov_results, mpp_result, certified=False, reason=reason)
    return 1


def _write_gov_result(turn_dir: str, gov_results: List[GovStageResult],
                      mpp_result: Optional[RecursionResult],
                      certified: bool, reason: str = "") -> None:
    gov_dir = Path(turn_dir) / "gov"
    gov_dir.mkdir(parents=True, exist_ok=True)

    output: Dict[str, Any] = {
        "certified":       certified,
        "reason":          reason,
        "generated_utc":   datetime.datetime.utcnow().isoformat() + "Z",
        "governance":      [r.as_dict() for r in gov_results],
        "mpp_certified":   mpp_result.certified if mpp_result else False,
        "mpp_iterations":  mpp_result.iterations if mpp_result else 0,
        "mpp_notes":       mpp_result.final_notes if mpp_result else "",
    }
    (gov_dir / "GOV_RESULT.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GVN + MPP — Full Governed Pipeline",
    )
    parser.add_argument("--turn-dir", required=True,
                        help="Path to the turn directory.")
    parser.add_argument("--max-iterations", type=int, default=3,
                        help="Max governed recursion iterations (default: 3).")
    parser.add_argument("--skip-governor", action="store_true",
                        help="Skip G3 Governor (use on first run with no history).")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
