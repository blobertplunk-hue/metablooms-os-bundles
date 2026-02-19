"""Abstract base for WaiverTracker storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class WaiverBackend(ABC):
    """
    Storage contract for WaiverTracker.

    Implementations must be append-only: once appended, entries are never
    modified or deleted. append() must be durable before returning.
    """

    @abstractmethod
    def append(self, entry: dict) -> None:
        """Durably append one entry to the log."""

    @abstractmethod
    def load(self) -> list[dict]:
        """
        Return all entries in insertion order.

        Malformed entries should be skipped with a logged warning — never raise.
        """
