# Migration Guide 🔄

This guide helps you migrate existing datetime code to `vista-time-utils`.

## From VISTA Internal Utilities

```python
# OLD
# from examples.11.utils.time_utils import get_current_utc_time, to_iso_format

# NEW
from vista_time import get_current_utc_time, to_iso_format
```

## From Python Standard Library

```python
from datetime import datetime

naive = datetime.now()  # ❌ Naive, no timezone
utc_naive = datetime.utcnow()  # ❌ Deprecated, still naive

from vista_time import get_current_utc_time

safe = get_current_utc_time()  # ✅ Timezone-aware, UTC enforced
```

## Legacy Systems with Custom Path Logic

```python
from vista_time.compat import legacy_shim

current = legacy_shim.get_current_utc_time()
iso = legacy_shim.to_iso_format(current)
```

## Checklist

- [ ] Replace standard-library datetime calls with `vista_time` helpers
- [ ] Ensure all stored timestamps are ISO 8601 strings with timezone info
- [ ] Use `create_future_timestamp` for TTL/expiration values
- [ ] Replace manual duration logic with `format_duration`
- [ ] Use the legacy shim for systems that cannot refactor immediately
