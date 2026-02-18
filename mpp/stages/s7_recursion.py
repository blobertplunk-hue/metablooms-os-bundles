# ECL:
#   id: MPP.S7.GOVERNED_RECURSION
#   role: orchestrator
#   owns: [bounded iteration loop — routes failures back to the earliest broken stage]
#   does_not: [run stages directly (delegates to mpp_pipeline), silently give up]
#   inputs: [pipeline_runner: callable, turn_dir: str, max_iterations: int]
#   outputs: [RecursionResult with full iteration history and final verdict]
#   side_effects: [filesystem — appends to loop/ITERATION_N_RECEIPT.json for each pass]
#   failure_modes: [MAX_ITERATIONS_REACHED → escalate, NO_PROGRESS → escalate,
#                   PRVE_BLOCKED → stop (human required)]
#   invariants: [certification only issued when ALL stages pass in the SAME iteration,
#                escalate is always called when max_iterations is hit — never silent fail]
#   evidence: [loop/LOOP_SUMMARY.md, loop/ITERATION_N_RECEIPT.json]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18
"""
Stage 7 — Governed Recursion: Bounded Loop Controller

Intent:
    Iterate toward correctness without runaway loops or silent giving-up.
    When a stage fails, the loop re-routes to the earliest stage that the
    failure implicates — not just the stage that failed. This ensures each
    loop iteration actually deepens understanding rather than re-trying
    the same broken state.

Scope:
    Orchestrates the full pipeline re-run with loop-back routing.
    Tracks progress between iterations. Escalates loudly on max-out.
    Issues a certification receipt when all stages pass in one iteration.

Non-Goals:
    Does not fix anything. Does not run individual stages in isolation.
    Does not silently pass when max iterations are reached.

Loop-Back Routing Table:
    TEST fails     → re-run from MMD  (maybe there's a gap you missed)
    ECL fails      → re-run from CDR  (aesthetic contract needs adjustment)
    CDR blocked    → re-run from SEE  (gather more evidence, re-propose)
    MMD HIGH gap   → re-run from SEE  (research the specific gap)
    SEE uncited    → re-run from PRVE (problem statement may be wrong)
    PRVE blocked   → STOP — escalate to human (can't research your way out)
"""

from __future__ import annotations

import json
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mpp.stages import StageID, StageResult


# ---- Result type ------------------------------------------------------------

@dataclass
class RecursionResult:
    certified:   bool
    iterations:  int
    history:     List[Dict[str, Any]] = field(default_factory=list)
    final_notes: str                  = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "certified":   self.certified,
            "iterations":  self.iterations,
            "history":     self.history,
            "final_notes": self.final_notes,
        }


# ---- Routing table ----------------------------------------------------------

# Maps a failing stage to the stage the loop should restart from.
# Lower in the pipeline = more thorough re-examination.
_LOOP_BACK: Dict[StageID, Optional[StageID]] = {
    StageID.TEST:      StageID.MMD,   # test fail → revisit gaps
    StageID.ECL:       StageID.CDR,   # clarity fail → revisit aesthetic contract
    StageID.CDR:       StageID.SEE,   # blocked proposal → gather more evidence
    StageID.MMD:       StageID.SEE,   # high gap → research it
    StageID.SEE:       StageID.PRVE,  # uncited claim → revisit problem statement
    StageID.PRVE:      None,          # PRVE blocked → stop, needs human
    StageID.RECURSION: None,
}

STAGE_ORDER = [
    StageID.PRVE, StageID.SEE, StageID.MMD,
    StageID.CDR, StageID.ECL, StageID.TEST,
]


def run(
    pipeline_runner: Callable[[str, Optional[StageID]], List[StageResult]],
    turn_dir: str,
    max_iterations: int = 3,
) -> RecursionResult:
    """
    Drive the pipeline in a bounded loop.

    pipeline_runner(turn_dir, start_from) must run all pipeline stages
    starting from start_from (or from PRVE if None) and return a list
    of StageResult in order.
    """
    root = Path(turn_dir)
    history: List[Dict[str, Any]] = []
    restart_from: Optional[StageID] = None
    prior_failure_stage: Optional[StageID] = None

    for iteration in range(1, max_iterations + 1):
        stage_results = pipeline_runner(turn_dir, restart_from)

        earliest_failure = _find_earliest_failure(stage_results)
        all_passed       = earliest_failure is None

        iteration_record = {
            "iteration":      iteration,
            "time_utc":       _utc(),
            "restart_from":   restart_from.value if restart_from else "PRVE",
            "stages_run":     [r.stage.value for r in stage_results],
            "earliest_fail":  earliest_failure.value if earliest_failure else None,
            "all_passed":     all_passed,
        }
        history.append(iteration_record)
        _write_iteration_receipt(root, iteration, iteration_record, stage_results)

        if all_passed:
            result = RecursionResult(
                certified   = True,
                iterations  = iteration,
                history     = history,
                final_notes = f"CERTIFIED after {iteration} iteration(s).",
            )
            _write_loop_summary(root, result, stage_results)
            _write_certificate(root, iteration, stage_results)
            return result

        # Progress check — if the same stage failed as last time, escalate early
        if prior_failure_stage == earliest_failure and iteration > 1:
            notes = (
                f"ESCALATE: Stage {earliest_failure.value} failed in two consecutive iterations "
                f"with no progress. Human intervention required."
            )
            result = RecursionResult(certified=False, iterations=iteration,
                                     history=history, final_notes=notes)
            _write_loop_summary(root, result, stage_results)
            _emit_escalation(root, notes, stage_results)
            return result

        prior_failure_stage = earliest_failure

        # PRVE blocked = human required immediately
        if earliest_failure == StageID.PRVE:
            notes = (
                "ESCALATE: PRVE is blocked. Research artifacts are missing or unauthorized. "
                "No further iteration can proceed without human action."
            )
            result = RecursionResult(certified=False, iterations=iteration,
                                     history=history, final_notes=notes)
            _write_loop_summary(root, result, stage_results)
            _emit_escalation(root, notes, stage_results)
            return result

        # Determine restart point for next iteration
        restart_from = _LOOP_BACK.get(earliest_failure)
        if restart_from is None:
            notes = f"ESCALATE: No loop-back route for {earliest_failure.value}. Human required."
            result = RecursionResult(certified=False, iterations=iteration,
                                     history=history, final_notes=notes)
            _write_loop_summary(root, result, stage_results)
            _emit_escalation(root, notes, stage_results)
            return result

    # Max iterations reached without certification
    notes = (
        f"ESCALATE: Max iterations ({max_iterations}) reached without certification. "
        "Full diagnostic in loop/LOOP_SUMMARY.md."
    )
    result = RecursionResult(certified=False, iterations=max_iterations,
                             history=history, final_notes=notes)
    _write_loop_summary(root, result, stage_results=[])
    _emit_escalation(root, notes, stage_results=[])
    return result


# ---- Helpers ----------------------------------------------------------------

def _find_earliest_failure(stage_results: List[StageResult]) -> Optional[StageID]:
    """Return the first stage (in pipeline order) that did not pass."""
    failed = {r.stage for r in stage_results if not r.passed}
    for stage in STAGE_ORDER:
        if stage in failed:
            return stage
    return None


def _write_iteration_receipt(root: Path, iteration: int,
                              record: Dict[str, Any],
                              stage_results: List[StageResult]) -> None:
    loop_dir = root / "loop"
    loop_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        **record,
        "stage_details": [r.as_dict() for r in stage_results],
    }
    (loop_dir / f"ITERATION_{iteration}_RECEIPT.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _write_loop_summary(root: Path, result: RecursionResult,
                         stage_results: List[StageResult]) -> None:
    loop_dir = root / "loop"
    loop_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MPP Governed Recursion — Loop Summary",
        "",
        f"**Certified:** {result.certified}",
        f"**Iterations:** {result.iterations}",
        f"**Final notes:** {result.final_notes}",
        "",
        "## Iteration History",
    ]
    for entry in result.history:
        lines.append(
            f"- Iter {entry['iteration']}: "
            f"start={entry['restart_from']}, "
            f"fail={entry['earliest_fail'] or 'none'}, "
            f"passed={entry['all_passed']}"
        )
    if stage_results:
        lines += ["", "## Final Stage Results"]
        for r in stage_results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"- **{r.stage.value}**: {status} — {r.notes}")
            for issue in r.blocking_issues:
                lines.append(f"  - [{issue.severity.value}] {issue.location}: {issue.description}")

    (loop_dir / "LOOP_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def _write_certificate(root: Path, iteration: int,
                        stage_results: List[StageResult]) -> None:
    import hashlib

    cert_path = root / "MPP_CERTIFICATE.json"
    existing  = {}
    if cert_path.exists():
        try:
            existing = json.loads(cert_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    entries = existing.get("entries", [])
    sha_manifest = {}
    for r in stage_results:
        for artifact in r.artifacts:
            art_path = root / artifact
            if art_path.exists():
                sha_manifest[artifact] = hashlib.sha256(
                    art_path.read_bytes()
                ).hexdigest()

    entries.append({
        "certified_at":    _utc(),
        "iteration":       iteration,
        "pipeline_version": "1.0.0",
        "sha256_manifest": sha_manifest,
        "tests_run":       next(
            (r.notes for r in stage_results if r.stage == StageID.TEST), ""),
        "verdict":         "CERTIFIED",
    })
    cert_path.write_text(
        json.dumps({"entries": entries}, indent=2), encoding="utf-8"
    )


def _emit_escalation(root: Path, notes: str, stage_results: List[StageResult]) -> None:
    """Write a prominent escalation report. Never silent-fail."""
    escalation_path = root / "loop" / "ESCALATION_REQUIRED.md"
    (root / "loop").mkdir(parents=True, exist_ok=True)
    lines = [
        "# ESCALATION REQUIRED",
        "",
        f"> {notes}",
        "",
        "## Action Required",
        "The MPP pipeline cannot self-resolve this failure. Human review is needed.",
        "",
        "## Failing Stages",
    ]
    for r in stage_results:
        if not r.passed:
            lines.append(f"### {r.stage.value}")
            for issue in r.blocking_issues:
                lines.append(f"- **{issue.severity.value}** @ `{issue.location}`")
                lines.append(f"  - {issue.description}")
                lines.append(f"  - Remediation: {issue.remediation}")
    escalation_path.write_text("\n".join(lines), encoding="utf-8")


def _utc() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"
