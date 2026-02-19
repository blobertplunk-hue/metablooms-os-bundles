# mpp/patterns/platforms — per-platform alert adapters
# Each adapter exposes a single render(card: PatternCard) -> str function.
from mpp.patterns.platforms.prometheus import render as prometheus

REGISTRY = {
    "prometheus": prometheus,
}

__all__ = ["REGISTRY"]
