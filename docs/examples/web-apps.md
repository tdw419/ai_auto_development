# Web Application Examples 🌐

## API Responses

```python
from fastapi import FastAPI
from vista_time import get_current_utc_time, to_iso_format

app = FastAPI()

@app.get("/status")
def status():
    return {
        "service": "vista-api",
        "timestamp": to_iso_format(get_current_utc_time()),
    }
```

## Session Expiration

```python
from vista_time import create_future_timestamp, is_expired

session_store = {}

def create_session(user_id):
    token = generate_token()
    session_store[token] = {
        "user_id": user_id,
        "expires_at": create_future_timestamp(hours=12),
    }
    return token

def validate_session(token):
    session = session_store.get(token)
    if not session or is_expired(session["expires_at"], buffer_seconds=30):
        raise PermissionError("Session expired")
    return session["user_id"]
```
