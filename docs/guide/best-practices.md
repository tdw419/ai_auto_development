# Best Practices ✅

Follow these recommendations to ensure robust timezone handling.

## Use UTC Everywhere

- Always work with UTC internally to avoid daylight-saving issues.
- Convert to local time only at the presentation layer.

## Store ISO 8601 Strings

```python
record = {
    "created_at": to_iso_format(get_current_utc_time()),
    "expires_at": create_future_timestamp(hours=12),
}
```

## Avoid Naive Datetimes

- Never rely on `datetime.now()` without a timezone.
- Use `get_current_utc_time()` instead.

## Use Buffers for Expiration

```python
if is_expired(token_expiry, buffer_seconds=30):
    refresh_token()
```

## Consistent Duration Formatting

```python
duration = format_duration(start_iso, end_iso)
log.info("Job finished in %s", duration)
```

## Testing Tips

- Use fixed timestamps for deterministic tests.
- Example:
  ```python
  from datetime import datetime, timezone
  fixed = datetime(2025, 10, 24, tzinfo=timezone.utc)
  ```
