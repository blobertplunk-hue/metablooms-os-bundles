"""
mpp-server — Shared waiver log HTTP server.

Thin FastAPI app that stores waiver log entries in a local JSONL file
and exposes them over HTTP so multiple teams / machines can share a log.

Requires: pip install mpp-patterns[server]

Usage:
    mpp-server --host 0.0.0.0 --port 8765 --log-path /data/waiver_log.jsonl
    python -m mpp.patterns.server

Endpoints:
    POST /entries            Append one entry (JSON body).
    GET  /entries            Return all entries.
    GET  /entries?team=X&pattern_id=Y   Filter entries.
    GET  /accuracy?team=X&pattern_id=Y&window_days=90   Compute accuracy score.
    GET  /health             Liveness probe — returns {"ok": true}.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


def _build_app(log_path: Path):
    try:
        from fastapi import FastAPI, Query, HTTPException
        from fastapi.responses import JSONResponse
    except ImportError:
        print(
            "mpp-server requires FastAPI. Install with:\n"
            "  pip install mpp-patterns[server]",
            file=sys.stderr,
        )
        sys.exit(1)

    # Import here so the module is importable without FastAPI installed
    from mpp.patterns.backends.jsonl_backend import JsonlBackend
    from mpp.patterns.waiver_tracker import WaiverTracker, MIN_SAMPLE
    from datetime import timedelta, datetime

    backend = JsonlBackend(log_path)
    app = FastAPI(
        title="MPP Waiver Log",
        description="Shared append-only log for pattern waivers and incidents.",
        version="0.1.0",
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/entries", status_code=201)
    def append_entry(entry: dict):
        required = {"type"}
        missing = required - entry.keys()
        if missing:
            raise HTTPException(400, f"Missing required fields: {missing}")
        backend.append(entry)
        return {"appended": True}

    @app.get("/entries")
    def get_entries(
        team: Optional[str] = Query(None),
        pattern_id: Optional[str] = Query(None),
    ):
        entries = backend.load()
        if team:
            entries = [e for e in entries if e.get("team") == team]
        if pattern_id:
            entries = [e for e in entries if e.get("pattern_id") == pattern_id]
        return {"entries": entries, "count": len(entries)}

    @app.get("/accuracy")
    def accuracy(
        team: str = Query(...),
        pattern_id: str = Query(...),
        window_days: int = Query(90, ge=1, le=3650),
    ):
        # Reuse WaiverTracker logic without re-opening a file tracker —
        # build a lightweight in-memory tracker from loaded entries.
        entries = backend.load()

        def _any_incident(waiver_ts: datetime, incidents: list[dict]) -> bool:
            window_end = waiver_ts + timedelta(days=window_days)
            for inc in incidents:
                try:
                    inc_ts = datetime.fromisoformat(inc["timestamp"])
                    if waiver_ts <= inc_ts <= window_end:
                        return True
                except (KeyError, ValueError):
                    pass
            return False

        waivers = [
            e for e in entries
            if e.get("type") == "waiver"
            and e.get("team") == team
            and e.get("pattern_id") == pattern_id
        ]
        incidents = [
            e for e in entries
            if e.get("type") == "incident"
            and e.get("team") == team
            and e.get("pattern_id") == pattern_id
        ]

        if len(waivers) < MIN_SAMPLE:
            return {
                "team": team,
                "pattern_id": pattern_id,
                "accuracy": None,
                "reason": f"Fewer than {MIN_SAMPLE} waivers — insufficient data.",
                "waiver_count": len(waivers),
            }

        accurate = sum(
            1 for w in waivers
            if not _any_incident(datetime.fromisoformat(w["timestamp"]), incidents)
        )
        score = accurate / len(waivers)
        return {
            "team": team,
            "pattern_id": pattern_id,
            "accuracy": round(score, 4),
            "waiver_count": len(waivers),
            "window_days": window_days,
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="MPP shared waiver log server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path(__file__).parent.parent.parent / "gov" / "waiver_log.jsonl",
    )
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("uvicorn not found. Install with: pip install mpp-patterns[server]", file=sys.stderr)
        sys.exit(1)

    app = _build_app(args.log_path)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
