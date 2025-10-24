#!/usr/bin/env python3
"""Timezone utility coverage."""
import unittest
from datetime import timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

EXAMPLES_UTILS = Path(__file__).resolve().parents[1]
if str(EXAMPLES_UTILS) not in sys.path:
    sys.path.append(str(EXAMPLES_UTILS))

from utils import time_utils


class TestTimezoneUtilities(unittest.TestCase):
    def test_utc_now_is_timezone_aware(self):
        now = time_utils.utc_now()
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset(), timedelta(0))

    def test_iso_round_trip(self):
        now = time_utils.utc_now()
        iso = time_utils.to_iso(now)
        parsed = time_utils.from_iso(iso)
        self.assertEqual(parsed, now)

    def test_future_and_expiration(self):
        future_iso = time_utils.future_iso(minutes=5)
        past_iso = time_utils.to_iso(time_utils.utc_now() - timedelta(minutes=5))
        self.assertFalse(time_utils.is_expired(future_iso))
        self.assertTrue(time_utils.is_expired(past_iso))

    def test_format_duration(self):
        start = time_utils.to_iso(time_utils.utc_now())
        end = time_utils.to_iso(time_utils.utc_now() + timedelta(minutes=1, seconds=5))
        duration = time_utils.format_duration(start, end)
        self.assertIn("1m", duration)


if __name__ == "__main__":
    unittest.main()
