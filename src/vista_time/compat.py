#!/usr/bin/env python3
"""
Legacy compatibility helpers for VISTA Time Utilities.
"""
from __future__ import annotations

from .time_utils import get_current_utc_time, to_iso_format


class LegacyTimeShim:
    """Shim for legacy systems that previously required manual path setup."""

    @staticmethod
    def ensure_available() -> bool:
        """Always return True to mirror legacy behaviour."""
        return True

    @staticmethod
    def get_current_utc_time():
        """Proxy to the modern helper."""
        return get_current_utc_time()

    @staticmethod
    def to_iso_format(dt):
        """Proxy to the modern helper."""
        return to_iso_format(dt)


legacy_shim = LegacyTimeShim()

__all__ = ["LegacyTimeShim", "legacy_shim"]
