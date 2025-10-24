# VISTA Time Utilities

Enterprise-grade timezone handling for AI and agentic systems. Born from the VISTA V-Loop project, these utilities provide robust, timezone-aware datetime operations for production AI workflows.

## Features

- 🕐 **UTC-First** – All operations return timezone-aware UTC datetimes
- 🌐 **ISO 8601** – Consistent timestamp formatting across services
- 🔧 **Zero Dependencies** – Pure Python standard library implementation
- 🐍 **Python 3.8+** – Broad compatibility
- 📚 **Type Hints** – Full typing support for better tooling
- 🔄 **Legacy Compat** – Seamless integration with existing systems

## Installation

```bash
pip install vista-time-utils
```

## Quick Start

```python
from vista_time import get_current_utc_time, to_iso_format, create_future_timestamp

current_time = get_current_utc_time()
print(f"Current UTC: {to_iso_format(current_time)}")

future_iso = create_future_timestamp(hours=24)
print(f"Future timestamp: {future_iso}")
```

## Legacy System Integration

```python
from vista_time.compat import legacy_shim

current = legacy_shim.get_current_utc_time()
iso = legacy_shim.to_iso_format(current)
```

## Development

```bash
pip install -e ".[dev]"
pytest
black src/
isort src/
```

## License

MIT License – see LICENSE for details.
