# ECL:
#   id: MPP.PATTERNS.ALERT_GEN
#   role: tool
#   owns: [generating platform-specific alert config files from pattern cards]
#   does_not: [apply alerts to infrastructure, modify card files, load registry config]
#   inputs: [pattern_id: str, platform: str, output_dir: Path]
#   outputs: [Path to written alert file]
#   side_effects: [filesystem — writes one alert file to output_dir]
#   failure_modes: [PATTERN_NOT_FOUND, UNSUPPORTED_PLATFORM, METRIC_HINT_INJECTION,
#                   NONPOSITIVE_THRESHOLD, OUTPUT_DIR_NOT_WRITABLE]
#   invariants: [never produces partial output — either full file or no file,
#                DRAFT cards always carry a warning header in output,
#                FILL_IN sentinels always cause promtool check rules to fail]
#   evidence: [tests/test_alert_gen.py]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-19
"""
Alert Generator

Produces platform-specific alert configuration files from pattern cards.
One file per pattern per platform. Files are committed to mpp/patterns/alerts/
as the canonical alert config for each pattern.

Usage (CLI):
    python -m mpp.patterns.alert_gen RETRY_AMPLIFICATION --platform prometheus
    python -m mpp.patterns.alert_gen --all --platform prometheus

Usage (API):
    from mpp.patterns.alert_gen import generate
    path = generate("RETRY_AMPLIFICATION", platform="prometheus")
    print(f"Written to {path}")

Output location:
    mpp/patterns/alerts/<PATTERN_ID>_<platform>_alerts.yaml

The output file is ready to validate:
    promtool check rules mpp/patterns/alerts/RETRY_AMPLIFICATION_prometheus_alerts.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from mpp.patterns.pattern_registry import PatternCard, PatternRegistry, RegistryValidationError
from mpp.patterns.platforms import REGISTRY as PLATFORM_REGISTRY

ALERTS_DIR = Path(__file__).parent / "alerts"


class PatternNotFoundError(KeyError):
    pass


class UnsupportedPlatformError(ValueError):
    pass


# ---- Public API -------------------------------------------------------------

def generate(
    pattern_id: str,
    *,
    platform:   str  = "prometheus",
    output_dir: Path = ALERTS_DIR,
) -> Path:
    """
    Generate an alert config file for pattern_id on the given platform.

    Returns the path of the written file.
    Raises PatternNotFoundError, UnsupportedPlatformError, or adapter errors.
    """
    adapter = _get_adapter(platform)
    registry = PatternRegistry()
    card = registry.get(pattern_id)

    if card is None:
        available = sorted(registry._cards.keys())
        raise PatternNotFoundError(
            f"Pattern '{pattern_id}' not found. "
            f"Available: {available}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{card.id}_{platform}_alerts.yaml"

    content = adapter(card)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def generate_all(
    *,
    platform:   str  = "prometheus",
    output_dir: Path = ALERTS_DIR,
    status_filter: Optional[str] = None,
) -> List[Path]:
    """
    Generate alert files for all cards matching status_filter.

    status_filter: 'ACTIVE' | 'DRAFT' | None (all non-deprecated)
    Returns list of paths written.
    """
    _get_adapter(platform)   # validate platform before iterating
    registry = PatternRegistry()

    cards: List[PatternCard] = []
    if status_filter == "ACTIVE":
        cards = registry.all_active()
    elif status_filter == "DRAFT":
        cards = registry.all_drafts()
    else:
        cards = registry.all_active() + registry.all_drafts()

    written = []
    for card in cards:
        path = generate(card.id, platform=platform, output_dir=output_dir)
        written.append(path)

    return written


# ---- Helpers ----------------------------------------------------------------

def _get_adapter(platform: str):
    adapter = PLATFORM_REGISTRY.get(platform)
    if adapter is None:
        raise UnsupportedPlatformError(
            f"No adapter for platform '{platform}'. "
            f"Available: {sorted(PLATFORM_REGISTRY.keys())}"
        )
    return adapter


# ---- CLI entry point --------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate platform-specific alert configs from pattern cards.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("pattern_id", nargs="?", help="Pattern ID to generate (e.g. RETRY_AMPLIFICATION)")
    group.add_argument("--all", action="store_true", help="Generate for all ACTIVE cards")

    parser.add_argument("--platform",    default="prometheus",
                        help="Target platform (default: prometheus)")
    parser.add_argument("--output-dir",  type=Path, default=ALERTS_DIR,
                        help=f"Output directory (default: {ALERTS_DIR})")
    parser.add_argument("--include-drafts", action="store_true",
                        help="Include DRAFT cards when using --all")

    args = parser.parse_args()

    try:
        if args.all:
            status = None if args.include_drafts else "ACTIVE"
            paths = generate_all(
                platform=args.platform,
                output_dir=args.output_dir,
                status_filter=status,
            )
            for p in paths:
                print(f"  wrote {p}")
            print(f"\n{len(paths)} file(s) generated.")
        else:
            path = generate(
                args.pattern_id,
                platform=args.platform,
                output_dir=args.output_dir,
            )
            print(f"  wrote {path}")

    except (PatternNotFoundError, UnsupportedPlatformError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
