"""
mpp-check — Stop hook / pre-push pattern compliance check.

Reads a git diff from stdin (or runs `git diff HEAD` if stdin is a tty),
extracts the added lines, and calls find_by_trigger() on them.
Prints a warning for every pattern that fires. Always exits 0 so it never
blocks a commit — it's a nudge, not a gate.

CLI usage (pipe from git diff):
    git diff HEAD | mpp-check
    git diff HEAD | python -m mpp.patterns.check_hook

Stop hook usage (Claude Code project .claude/settings.json):
    "command": "git diff HEAD --unified=0 | mpp-check 2>/dev/null || true"
"""

from __future__ import annotations

import sys
import os
from pathlib import Path


def _read_diff() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    # Fallback: run git diff HEAD directly
    import subprocess
    result = subprocess.run(
        ["git", "diff", "HEAD", "--unified=0"],
        capture_output=True, text=True,
    )
    return result.stdout


def _extract_added_lines(diff: str) -> str:
    """Return only the added lines ('+' prefix) from a unified diff."""
    lines = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return " ".join(lines)


def main() -> None:
    diff = _read_diff()
    if not diff.strip():
        return

    added = _extract_added_lines(diff)
    if not added.strip():
        return

    try:
        # Support running from the repo root or as an installed package
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from mpp.patterns.pattern_registry import PatternRegistry
        registry = PatternRegistry()
    except Exception as exc:
        # Never block on registry load failure
        print(f"[mpp-check] registry unavailable: {exc}", file=sys.stderr)
        return

    matches = registry.find_by_trigger(added)
    if not matches:
        return

    seen: set[str] = set()
    unique = [c for c in matches if not (c.id in seen or seen.add(c.id))]

    print(f"\n[mpp-check] {len(unique)} pattern(s) detected in this diff:", file=sys.stderr)
    for card in unique:
        print(f"  ! {card.id} — {card.name}", file=sys.stderr)
        diag = (card.diagnostic or "")[:120]
        if diag:
            print(f"    Diagnostic: {diag}...", file=sys.stderr)
    print(
        "  -> run: python -c \"from mpp.patterns import PatternRegistry as R;"
        " r=R(); print(r.render_card(r.get('<ID>')))\"",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    # Exit 0 — this is a nudge, not a hard block
    sys.exit(0)


if __name__ == "__main__":
    main()
