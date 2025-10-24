# VISTA Time Utilities 🕐

[![PyPI version](https://img.shields.io/pypi/v/vista-time-utils.svg)](https://pypi.org/project/vista-time-utils/)
[![Python Versions](https://img.shields.io/pypi/pyversions/vista-time-utils.svg)](https://pypi.org/project/vista-time-utils/)
[![CI Status](https://github.com/tdw419/ai_auto_development/actions/workflows/vista-ci.yml/badge.svg)](https://github.com/tdw419/ai_auto_development/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Enterprise-grade timezone handling for AI systems and distributed applications.**  
Born from the VISTA V-Loop project, these utilities solve real-world datetime problems in production AI systems.

## Why VISTA Time?

> ⚠️ **Traditional Python datetime pitfalls**
>
> ```python
> from datetime import datetime
>
> naive_time = datetime.now()            # ❌ Naive, no timezone!
> utc_naive = datetime.utcnow()          # ❌ Deprecated and still naive
> local_str = datetime.fromtimestamp(ts) # ❌ Depends on system settings
> ```
>
> ✅ **VISTA Time fixes this**
>
> ```python
> from vista_time import get_current_utc_time
>
> safe_time = get_current_utc_time()     # ✅ Always UTC, always aware
> print(safe_time)                       # 2025-10-24T02:30:00+00:00
> ```

## Features

- ✨ **UTC-First** – All operations return timezone-aware UTC datetimes  
- 🌐 **ISO 8601** – Consistent timestamp formatting across systems  
- 🔧 **Zero Dependencies** – Pure Python standard library implementation  
- 🐍 **Python 3.8+** – Broad compatibility support  
- 📚 **Type Hints** – Full typing support for better development  
- 🔄 **Legacy Compat** – Seamless integration with existing systems  
- 🚀 **Production Ready** – Battle-tested in AI agent systems  

## Quick Install

```bash
pip install vista-time-utils
```

## 60‑Second Quickstart

```python
from vista_time import (
    get_current_utc_time,
    to_iso_format,
    create_future_timestamp,
    is_expired,
)

# 🕐 Current time (UTC, timezone-aware)
current = get_current_utc_time()
print(f"Current: {to_iso_format(current)}")

# ⏰ Cache / TTL handling
cache_until = create_future_timestamp(hours=24)
print(f"Expired? {is_expired(cache_until)}")  # False

# 🔄 Safe round-trip conversions
iso_str = to_iso_format(current)
parsed = from_iso_format(iso_str)
assert parsed == current
```

## Common Use Cases

### 🤖 AI & Agent Systems
```python
from vista_time import get_current_utc_time, create_future_timestamp, is_expired

class AIAgent:
    def __init__(self):
        self.deadline = create_future_timestamp(minutes=30)

    def execute(self):
        if is_expired(self.deadline):
            raise TimeoutError("Agent task exceeded deadline")
        start = get_current_utc_time()
        # ... perform task ...
        end = get_current_utc_time()
        return start, end
```

### 🌐 Web APIs & Services
```python
from vista_time import get_current_utc_time, to_iso_format

def build_response(payload):
    return {
        "data": payload,
        "timestamp": to_iso_format(get_current_utc_time()),
    }
```

### 📊 Data Pipelines & ETL
```python
from vista_time import format_duration, to_iso_format, get_current_utc_time

start = get_current_utc_time()
# ... run pipeline ...
end = get_current_utc_time()

print(f"Pipeline duration: {format_duration(to_iso_format(start), to_iso_format(end))}")
```

## Migrating from Legacy Systems

### From VISTA Internal Utilities
```python
# OLD:
# from examples.11.utils.time_utils import get_current_utc_time

# NEW:
from vista_time import get_current_utc_time
```

### Legacy Shim for Complex Systems
```python
from vista_time.compat import legacy_shim

current = legacy_shim.get_current_utc_time()
iso = legacy_shim.to_iso_format(current)
```

## API Reference

Core helpers available from `vista_time`:

| Function | Description |
|----------|-------------|
| `get_current_utc_time()` | Current UTC time (timezone-aware) |
| `to_iso_format(dt)` | Convert datetime to ISO 8601 string |
| `from_iso_format(iso)` | Parse ISO string into UTC datetime |
| `create_future_timestamp(...)` | Generate future ISO timestamp |
| `is_expired(iso, buffer_seconds=0)` | Check expiration with optional buffer |
| `format_duration(start_iso, end_iso=None)` | Human readable duration |

## Development

```bash
pip install -e ".[dev]"
pytest
black src/
isort src/
```

## Documentation

- [Quickstart Guide](docs/quickstart.md)
- [Migration Guide](docs/guide/migration.md)
- [Examples](docs/examples/)

## Contributing

We welcome contributions! Please open an issue or pull request on GitHub. For large changes, start a discussion first so we can help.

## License

MIT License – see [LICENSE](LICENSE) for details.
