# AI Systems Examples 🤖

## Agent Task Management

```python
from vista_time import (
    create_future_timestamp,
    format_duration,
    get_current_utc_time,
    is_expired,
    to_iso_format,
)

class AIAgent:
    def __init__(self):
        self.timeout = create_future_timestamp(minutes=20)

    def run(self):
        if is_expired(self.timeout):
            raise TimeoutError("Agent exceeded workload window")

        start = get_current_utc_time()
        # ... perform actions ...
        end = get_current_utc_time()

        return {
            "started_at": to_iso_format(start),
            "completed_at": to_iso_format(end),
            "duration": format_duration(to_iso_format(start), to_iso_format(end)),
        }
```

## Model Training Pipelines

```python
from vista_time import format_duration, get_current_utc_time, to_iso_format

def train_model():
    training_start = get_current_utc_time()
    # ... training loop ...
    training_end = get_current_utc_time()

    print("Training duration:", format_duration(
        to_iso_format(training_start), to_iso_format(training_end)
    ))
```
