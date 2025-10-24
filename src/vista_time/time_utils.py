#!/usr/bin/env python3
"""
VISTA Time Utilities - Core timezone-aware functions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


def get_current_utc_time() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso_format(dt: datetime) -> str:
    """Convert a datetime into an ISO 8601 string with timezone information."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def from_iso_format(iso_string: str) -> datetime:
    """Convert an ISO 8601 string into a timezone-aware datetime (defaults to UTC)."""
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_future_timestamp(*, days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    """Create a future timestamp (ISO 8601) offset from now."""
    future_time = get_current_utc_time() + timedelta(days=days, hours=hours, minutes=minutes)
    return to_iso_format(future_time)


def is_expired(timestamp_iso: str, *, buffer_seconds: int = 0) -> bool:
    """Return True if the timestamp has passed (with optional buffer)."""
    try:
        timestamp = from_iso_format(timestamp_iso)
    except (ValueError, TypeError):
        return True

    reference = get_current_utc_time()
    if buffer_seconds:
        reference -= timedelta(seconds=buffer_seconds)
    return timestamp <= reference


def format_duration(start_iso: str, end_iso: Optional[str] = None) -> str:
    """Return human-readable duration between two ISO timestamps."""
    try:
        start = from_iso_format(start_iso)
        end = from_iso_format(end_iso) if end_iso else get_current_utc_time()
    except (ValueError, TypeError):
        return "unknown"

    delta = end - start
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"
