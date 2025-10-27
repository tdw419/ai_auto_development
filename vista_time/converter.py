from datetime import datetime
import pytz

def to_timezone(dt, tz_name):
    """Converts a datetime object to a specific timezone."""
    tz = pytz.timezone(tz_name)
    return dt.astimezone(tz)
