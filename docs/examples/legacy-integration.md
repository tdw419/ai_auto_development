# Legacy Integration Examples 🏗️

## Drop-In Shim

```python
from vista_time.compat import legacy_shim

def legacy_workflow():
    now = legacy_shim.get_current_utc_time()
    iso = legacy_shim.to_iso_format(now)
    legacy_system.store_timestamp(iso)
```

## Gradual Migration Strategy

1. Replace existing imports with the shim:
   ```python
   from vista_time.compat import legacy_shim as time_utils
   ```
2. Refactor modules incrementally to import from `vista_time` directly.
3. Remove shim references once all modules are updated.

## Verifying Compatibility

```python
from vista_time.compat import legacy_shim
from vista_time import get_current_utc_time

assert legacy_shim.to_iso_format(legacy_shim.get_current_utc_time()) == \
       to_iso_format(get_current_utc_time())
```
