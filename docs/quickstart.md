# Quickstart 🚀

Learn the essentials of `vista-time-utils` in five minutes.

## 1. Install

```bash
pip install vista-time-utils
```

## 2. Import the Core Helpers

```python
from vista_time import (
    get_current_utc_time,
    to_iso_format,
    from_iso_format,
    create_future_timestamp,
    is_expired,
)
```

## 3. Get Current Time (UTC, Aware)

```python
current = get_current_utc_time()
print(to_iso_format(current))
# 2025-10-24T02:45:00+00:00
```

## 4. Work with Expirations

```python
cache_until = create_future_timestamp(hours=6)
if is_expired(cache_until):
    refresh_cache()
```

## 5. Format Durations

```python
start_iso = to_iso_format(get_current_utc_time())
# ... do work ...
end_iso = to_iso_format(get_current_utc_time())
print(format_duration(start_iso, end_iso))  # e.g. 2m 13s
```

## Next Steps

- [Migration Guide](guide/migration.md) – move legacy code safely
- [Best Practices](guide/best-practices.md) – production recommendations
- [Examples](examples/) – real-world usage patterns
