# API Reference

## `vista_time` Module

### `get_current_utc_time() -> datetime`
Return the current timezone-aware UTC datetime.

### `to_iso_format(dt: datetime) -> str`
Convert a datetime to an ISO 8601 string, normalising to UTC when needed.

### `from_iso_format(iso_string: str) -> datetime`
Parse an ISO 8601 string and return a timezone-aware UTC datetime.

### `create_future_timestamp(*, days=0, hours=0, minutes=0) -> str`
Return a future timestamp (ISO 8601) offset from now.

### `is_expired(timestamp_iso: str, *, buffer_seconds: int = 0) -> bool`
Return `True` if the timestamp has passed (optionally with a buffer).

### `format_duration(start_iso: str, end_iso: Optional[str] = None) -> str`
Return a human-readable duration between two ISO timestamps.
