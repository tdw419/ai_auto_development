import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timezone
import pytz

# Add vista_time to the path
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vista_time.converter import to_timezone

@given(st.datetimes(timezones=st.just(pytz.utc)), st.sampled_from(pytz.common_timezones))
def test_to_timezone_fuzz(dt, tz_name):
    """Fuzz test for timezone conversion."""
    converted_dt = to_timezone(dt, tz_name)
    assert converted_dt.tzinfo.zone == tz_name
