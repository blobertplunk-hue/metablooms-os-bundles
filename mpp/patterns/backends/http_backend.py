"""HTTP backend — posts entries to a shared waiver log server.

Requires urllib (stdlib only, no extra deps).

Usage:
    from mpp.patterns.backends.http_backend import HttpBackend
    from mpp.patterns.waiver_tracker import WaiverTracker

    tracker = WaiverTracker(backend=HttpBackend("http://waiver-server:8765"))

The server is the companion mpp.patterns.server (mpp-server CLI).
Any HTTP endpoint that honours the same contract works:
    POST /entries          body: JSON entry object
    GET  /entries          returns: {"entries": [...]}
    GET  /entries?team=X&pattern_id=Y
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from mpp.patterns.backends.base import WaiverBackend

_LOG = logging.getLogger(__name__)


class HttpBackend(WaiverBackend):
    """
    Sends waiver log entries to a remote HTTP server.

    append() raises on non-2xx so the caller knows the entry was not stored.
    load() returns [] on error and logs a warning — never raises.
    """

    def __init__(self, base_url: str, *, timeout: int = 10) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def append(self, entry: dict) -> None:
        url = f"{self._base}/entries"
        body = json.dumps(entry).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status >= 300:
                    raise OSError(f"Server returned {resp.status} for POST {url}")
        except urllib.error.URLError as exc:
            raise OSError(f"HttpBackend.append failed: {exc}") from exc

    def load(self, *, team: Optional[str] = None, pattern_id: Optional[str] = None) -> list[dict]:
        params: dict[str, str] = {}
        if team:
            params["team"] = team
        if pattern_id:
            params["pattern_id"] = pattern_id
        qs = ("?" + urllib.parse.urlencode(params)) if params else ""
        url = f"{self._base}/entries{qs}"
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
                return data.get("entries", [])
        except Exception as exc:
            _LOG.warning("HttpBackend.load failed (%s), returning empty list", exc)
            return []
