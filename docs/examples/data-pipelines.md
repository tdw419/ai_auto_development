# Data Pipeline Examples 📊

## ETL Duration Logging

```python
from vista_time import format_duration, get_current_utc_time, to_iso_format

def run_etl():
    start = get_current_utc_time()
    # ... extract, transform, load ...
    end = get_current_utc_time()
    print("ETL finished in", format_duration(to_iso_format(start), to_iso_format(end)))
```

## Audit Logging

```python
from vista_time import get_current_utc_time, to_iso_format

def audit_event(event_name, payload):
    log_entry = {
        "event": event_name,
        "payload": payload,
        "recorded_at": to_iso_format(get_current_utc_time()),
    }
    write_to_log(log_entry)
```
