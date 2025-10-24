#!/usr/bin/env python3
"""
Timezone-aware datetime helpers shared across VISTA components.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current time with explicit UTC tzinfo."""
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    """Render a datetime as ISO 8601 with timezone information."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def from_iso(value: str) -> datetime:
    """Parse ISO 8601 string and ensure result is UTC-aware."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        logger.warning("Failed to parse ISO timestamp %s: %s", value, exc)
        return utc_now()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def future_iso(*, days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    """Produce ISO timestamp offset from now."""
    return to_iso(utc_now() + timedelta(days=days, hours=hours, minutes=minutes))


def is_expired(iso_ts: str, *, grace_seconds: int = 0) -> bool:
    """Return True if ISO timestamp is in the past (with optional grace)."""
    ts = from_iso(iso_ts)
    threshold = utc_now() - timedelta(seconds=grace_seconds)
    return ts <= threshold


def format_duration(start_iso: str, end_iso: Optional[str] = None) -> str:
    """Human readable duration between two ISO timestamps."""
    start = from_iso(start_iso)
    end = from_iso(end_iso) if end_iso else utc_now()
    delta = end - start
    total_seconds = int(delta.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


# Backwards-compatible helper names for legacy modules
def get_current_utc_time() -> datetime:
    """Alias for utc_now used by legacy code."""
    return utc_now()


def to_iso_format(dt: datetime) -> str:
    """Alias for to_iso used by legacy code."""
    return to_iso(dt)
