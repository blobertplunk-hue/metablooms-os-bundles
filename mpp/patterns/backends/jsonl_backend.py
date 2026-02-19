"""Local JSONL file backend — the default for WaiverTracker."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mpp.patterns.backends.base import WaiverBackend

_LOG = logging.getLogger(__name__)

_DEFAULT_LOG_PATH = Path(__file__).parent.parent.parent.parent / "gov" / "waiver_log.jsonl"


class JsonlBackend(WaiverBackend):
    """
    Stores waiver log entries as newline-delimited JSON in a local file.

    Thread-safety: appends are POSIX-atomic for entries under ~4 KB (PIPE_BUF).
    Concurrent writers may rarely produce a malformed line; load() skips those
    with a warning.
    """

    def __init__(self, log_path: Path = _DEFAULT_LOG_PATH) -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._path.touch(exist_ok=True)
        except OSError as exc:
            raise OSError(
                f"Cannot write to waiver log: {self._path}. "
                "Check that the parent directory exists and is writable."
            ) from exc

    def append(self, entry: dict) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")

    def load(self) -> list[dict]:
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
