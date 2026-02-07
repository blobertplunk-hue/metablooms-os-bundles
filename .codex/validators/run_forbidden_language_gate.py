#!/usr/bin/env python3
"""
GATE: Forbidden Language Detection
EXIT 0 = PASS, EXIT 13 = FAIL

Scans agent-emitted artifacts for forbidden words.
Exemptions:
  - Bundle filenames (os_bundles/ contents)
  - The forbidden language section in SUPER_PROMPT
  - Human-authored governance docs (BOOT.md, CDR_v2.md)
  - Direct quotes from bundle filenames within catalog/lineage
"""
import sys
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_WORDS = [
    "enforced", "verified", "running", "active", "wired",
    "booted", "compliant", "guaranteed",
]

# Files exempt from scanning (human-authored or contain the rules themselves)
EXEMPT_FILES = {
    ".codex/kernel/BOOT.md",
    ".codex/policies/SUPER_PROMPT_v2.2.md",
    ".codex/policies/SUPER_PROMPT_v2.3.md",
    ".codex/policies/CDR_v2.md",
    ".codex/policies/BUNDLE_LIFECYCLE_v1.md",  # references qualifier names
}

# Scan these directories for agent-emitted content
SCAN_DIRS = [
    ROOT / ".codex" / "receipts",
    ROOT / ".codex" / "research",
]

# Also scan these specific files (agent-generated artifacts)
# NOTE: MMD_REPORT.json is exempt — it discusses forbidden language as a finding
# (meta-reference). Scanning it would flag every mention of the rule itself.
SCAN_FILES = []

failures = []
checked = 0


def get_bundle_filenames():
    """Load filenames that are valid exemptions (they contain forbidden words naturally)."""
    bundles_dir = ROOT / "os_bundles"
    if not bundles_dir.exists():
        return set()
    return {f.name for f in bundles_dir.iterdir() if f.is_file()}


def scan_file(filepath, bundle_names):
    """Scan a file for forbidden words, respecting exemptions."""
    global checked
    checked += 1

    rel_path = str(filepath.relative_to(ROOT))
    if rel_path in EXEMPT_FILES:
        return

    try:
        content = filepath.read_text(errors="replace")
    except Exception:
        return

    for line_num, line in enumerate(content.splitlines(), 1):
        line_lower = line.lower()

        for word in FORBIDDEN_WORDS:
            if word not in line_lower:
                continue

            # Check if this occurrence is inside a bundle filename reference
            is_filename_ref = any(name in line for name in bundle_names if word.upper() in name.upper())
            if is_filename_ref:
                continue

            # Check if it's in a JSON "filename" field value
            if '"filename"' in line and word.upper() in line:
                continue

            # Check for the word as a standalone term (not part of another word)
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, line_lower):
                failures.append(
                    f"  {rel_path}:{line_num}: forbidden word '{word}'\n"
                    f"    > {line.strip()[:120]}"
                )


def main():
    bundle_names = get_bundle_filenames()

    # Scan receipt files
    for scan_dir in SCAN_DIRS:
        if scan_dir.exists():
            for f in scan_dir.rglob("*.json"):
                scan_file(f, bundle_names)
            for f in scan_dir.rglob("*.md"):
                scan_file(f, bundle_names)

    # Scan specific artifact files
    for f in SCAN_FILES:
        if f.exists():
            scan_file(f, bundle_names)

    if failures:
        print(f"FORBIDDEN_LANG_GATE FAIL: {len(failures)} violations across {checked} files", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(13)
    else:
        print(f"FORBIDDEN_LANG_GATE: PASS ({checked} files scanned)")
        sys.exit(0)


if __name__ == "__main__":
    main()
