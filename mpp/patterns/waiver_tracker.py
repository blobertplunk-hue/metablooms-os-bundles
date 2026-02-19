# ECL:
#   id: MPP.PATTERNS.WAIVER_TRACKER
#   role: library
#   owns: [recording waivers and incidents, computing waiver accuracy scores,
#          querying waivers before an incident]
#   does_not: [validate pattern IDs against the registry, enforce gates,
#              integrate with s3_mmd (separate turn), read PagerDuty/OpsGenie]
#   inputs: [log_path: Path — JSONL file, defaults to gov/waiver_log.jsonl]
#   outputs: [accuracy score per team+pattern, waiver list before an incident]
#   side_effects: [filesystem — appends entries to waiver_log.jsonl]
#   failure_modes: [TEAM_EMPTY, LOG_UNWRITABLE, MALFORMED_LOG_LINE]
#   invariants: [log is append-only — entries never mutated after write,
#                accuracy() returns None when waiver count < MIN_SAMPLE,
#                a waiver with no subsequent incident within window is ACCURATE,
#                malformed JSONL lines are skipped with a warning — log stays usable]
#   evidence: [turns/003_waiver_accuracy/see/SEE_EVIDENCE_SUMMARY.md]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
Waiver Accuracy Tracker

Records pattern waivers and production incidents, then computes how accurate
those waivers were. A waiver is "accurate" if no incident of the same pattern
type occurred within the claim window after the waiver was filed.

Over time, teams with a habit of waiving real risks accumulate a low accuracy
score — a signal that should trigger a conversation before the next waiver
is accepted.

Usage:
    from mpp.patterns.waiver_tracker import WaiverTracker
    import datetime

    tracker = WaiverTracker()  # defaults to gov/waiver_log.jsonl

    tracker.record_waiver(
        run_id="run-20260219-001",
        pattern_id="NONIDEMPOTENT_RETRY",
        team="payments",
        reason="We use Stripe idempotency keys on all charge calls.",
    )

    tracker.record_incident(
        pattern_id="NONIDEMPOTENT_RETRY",
        team="payments",
        description="Double charge on network timeout retry.",
    )

    score = tracker.accuracy("payments", "NONIDEMPOTENT_RETRY")
    # None if fewer than 5 waivers (insufficient data)
    # float between 0.0 and 1.0 otherwise

IMPORTANT: accuracy() is advisory. Do not use it as a hard gate.
           Use it as a conversation starter with the team.
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

_LOG = logging.getLogger(__name__)

MIN_SAMPLE = 5          # minimum waivers before accuracy() returns a float
_STALE_WARN_DAYS = 7    # warn if provided timestamp is this many days in the past

# Default location: repo_root/gov/waiver_log.jsonl
_DEFAULT_LOG_PATH = Path(__file__).parent.parent.parent / "gov" / "waiver_log.jsonl"


class WaiverTracker:
    """
    Append-only log of pattern waivers and production incidents.

    Thread-safety: append writes are POSIX-atomic for entries under ~4 KB
    (PIPE_BUF limit). Concurrent processes may rarely produce a malformed
    line; the reader skips such lines with a warning.
    """

    def __init__(self, log_path: Path = _DEFAULT_LOG_PATH) -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Verify writability on construction — fail loudly, not silently later
        try:
            self._path.touch(exist_ok=True)
        except OSError as exc:
            raise OSError(
                f"Cannot write to waiver log: {self._path}. "
                "Check that the parent directory exists and is writable."
            ) from exc

    # ---- Write API ----------------------------------------------------------

    def record_waiver(
        self,
        *,
        run_id: str,
        pattern_id: str,
        team: str,
        reason: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record that a pattern was waived in an MPP run.

        Args:
            run_id:     Unique identifier for the MPP pipeline run.
            pattern_id: Pattern library ID (e.g. "NONIDEMPOTENT_RETRY").
            team:       Team that owns the feature being reviewed.
            reason:     Justification text from the MMD waiver.
            timestamp:  Defaults to now (UTC). Pass explicitly for back-fills.
        """
        _require_nonempty("team", team)
        ts = _resolve_ts(timestamp)
        self._append({
            "type": "waiver",
            "run_id": run_id,
            "pattern_id": pattern_id,
            "team": team,
            "reason": reason,
            "timestamp": ts.isoformat(),
        })

    def record_incident(
        self,
        *,
        pattern_id: str,
        team: str,
        description: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a production incident that matched a pattern.

        Args:
            pattern_id:  Pattern library ID of the failure that occurred.
            team:        Team whose system experienced the incident.
            description: Short description of what happened.
            timestamp:   Defaults to now (UTC).
        """
        _require_nonempty("team", team)
        ts = _resolve_ts(timestamp)
        self._append({
            "type": "incident",
            "pattern_id": pattern_id,
            "team": team,
            "description": description,
            "timestamp": ts.isoformat(),
        })

    def record_correction(
        self,
        *,
        corrects_run_id: str,
        field: str,
        old_value: str,
        new_value: str,
        reason: str,
    ) -> None:
        """
        Append a correction entry. Does not modify the original entry.

        Use when a waiver or incident was filed with an error (e.g. wrong team name).
        Corrections are advisory — callers decide whether to honour them.
        """
        self._append({
            "type": "correction",
            "corrects_run_id": corrects_run_id,
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
            "timestamp": _now_utc().isoformat(),
        })

    # ---- Query API ----------------------------------------------------------

    def accuracy(
        self,
        team: str,
        pattern_id: str,
        *,
        window_days: int = 90,
    ) -> Optional[float]:
        """
        Return the fraction of waivers that were NOT followed by an incident
        within window_days. Returns None if fewer than MIN_SAMPLE waivers exist.

        A waiver is "accurate" when no incident of the same pattern type occurs
        within window_days after the waiver was filed.

        IMPORTANT: This score is advisory. Do not use it as a hard gate.
        """
        entries = self._load()
        waivers = [
            e for e in entries
            if e.get("type") == "waiver"
            and e.get("team") == team
            and e.get("pattern_id") == pattern_id
        ]
        if len(waivers) < MIN_SAMPLE:
            return None

        incidents = [
            e for e in entries
            if e.get("type") == "incident"
            and e.get("team") == team
            and e.get("pattern_id") == pattern_id
        ]

        accurate = sum(
            1 for w in waivers
            if not _any_incident_in_window(
                datetime.fromisoformat(w["timestamp"]),
                window_days,
                incidents,
            )
        )
        return accurate / len(waivers)

    def waivers_before_incident(
        self,
        *,
        pattern_id: str,
        team: str,
        incident_timestamp: datetime,
        window_days: int = 90,
    ) -> List[dict]:
        """
        Return waivers filed by team for pattern_id within window_days before
        incident_timestamp (inclusive on both ends).

        Use for post-mortem queries: "did anyone waive this before it happened?"
        """
        cutoff = incident_timestamp - timedelta(days=window_days)
        entries = self._load()
        return [
            e for e in entries
            if e.get("type") == "waiver"
            and e.get("team") == team
            and e.get("pattern_id") == pattern_id
            and cutoff <= datetime.fromisoformat(e["timestamp"]) <= incident_timestamp
        ]

    def all_teams(self) -> list[str]:
        """Return sorted list of all distinct team names in the log."""
        return sorted({
            e["team"]
            for e in self._load()
            if "team" in e
        })

    def all_patterns(self) -> list[str]:
        """Return sorted list of all distinct pattern IDs in the log."""
        return sorted({
            e["pattern_id"]
            for e in self._load()
            if "pattern_id" in e
        })

    # ---- Internal -----------------------------------------------------------

    def _append(self, entry: dict) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        entries = []
        with self._path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entries.append(json.loads(raw))
                except json.JSONDecodeError as exc:
                    _LOG.warning(
                        "Skipping malformed log line %d in %s: %s",
                        lineno, self._path, exc,
                    )
        return entries


# ---- Helpers ----------------------------------------------------------------

def _require_nonempty(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} must be a non-empty string, got: {value!r}")


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


def _resolve_ts(ts: Optional[datetime]) -> datetime:
    if ts is None:
        return _now_utc()
    now = _now_utc()
    if (now - ts).days > _STALE_WARN_DAYS:
        warnings.warn(
            f"Provided timestamp {ts.isoformat()} is more than {_STALE_WARN_DAYS} days "
            "in the past. Ensure this is intentional (back-fill) and not a clock error.",
            stacklevel=3,
        )
    return ts


def _any_incident_in_window(
    waiver_ts: datetime,
    window_days: int,
    incidents: list[dict],
) -> bool:
    window_end = waiver_ts + timedelta(days=window_days)
    return any(
        waiver_ts <= datetime.fromisoformat(i["timestamp"]) <= window_end
        for i in incidents
    )
