#!/usr/bin/env python3
"""
GATE: LFS Gap Detection
EXIT 0 = PASS, EXIT 12 = FAIL

Checks that every file extension present in os_bundles/ is covered by
a pattern in .gitattributes with LFS tracking.
"""
import sys
import re
import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
failures = []


def parse_lfs_patterns(gitattributes_path):
    """Extract glob patterns from .gitattributes that have filter=lfs."""
    patterns = []
    if not gitattributes_path.exists():
        failures.append("  .gitattributes: FILE NOT FOUND")
        return patterns

    for line in gitattributes_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "filter=lfs" in line:
            pattern = line.split()[0]
            patterns.append(pattern)
    return patterns


def extension_matches_any_pattern(filename, patterns):
    """Check if a filename matches any LFS glob pattern."""
    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
        # Handle patterns like *.part[0-9]* with regex
        regex = fnmatch.translate(pattern)
        if re.match(regex, filename):
            return True
    return False


def main():
    gitattributes = ROOT / ".gitattributes"
    bundles_dir = ROOT / "os_bundles"

    if not bundles_dir.exists():
        print("LFS_GAP_GATE: SKIP (no os_bundles/ directory)")
        sys.exit(0)

    patterns = parse_lfs_patterns(gitattributes)
    if not patterns:
        failures.append("  No LFS patterns found in .gitattributes")
        print(f"LFS_GAP_GATE FAIL: {len(failures)} issues", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(12)

    untracked = []
    for f in sorted(bundles_dir.iterdir()):
        if not f.is_file():
            continue
        if not extension_matches_any_pattern(f.name, patterns):
            untracked.append(f.name)

    if untracked:
        # Group by extension for clarity
        ext_set = set()
        for name in untracked:
            parts = name.rsplit(".", 1)
            if len(parts) > 1:
                ext_set.add(f".{parts[1]}")
            else:
                ext_set.add("(no extension)")

        failures.append(
            f"  {len(untracked)} files not covered by LFS patterns:\n"
            + "\n".join(f"    {f}" for f in untracked)
            + f"\n  Missing extensions: {sorted(ext_set)}"
        )

    if failures:
        print(f"LFS_GAP_GATE FAIL: {len(failures)} issues", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(12)
    else:
        checked = len(list(bundles_dir.iterdir()))
        print(f"LFS_GAP_GATE: PASS ({checked} files, {len(patterns)} patterns)")
        sys.exit(0)


if __name__ == "__main__":
    main()
