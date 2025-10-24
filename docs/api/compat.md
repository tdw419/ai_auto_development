# Compatibility Layer

The compatibility module (`vista_time.compat`) exposes a shim for legacy systems.

## `LegacyTimeShim`

### `ensure_available() -> bool`
Always returns `True`. Included for historical parity.

### `get_current_utc_time() -> datetime`
Proxy for `vista_time.get_current_utc_time`.

### `to_iso_format(dt: datetime) -> str`
Proxy for `vista_time.to_iso_format`.

## `legacy_shim`

A singleton instance of `LegacyTimeShim` provided for convenience:

```python
from vista_time.compat import legacy_shim

timestamp = legacy_shim.to_iso_format(legacy_shim.get_current_utc_time())
```
