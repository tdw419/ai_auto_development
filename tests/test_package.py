#!/usr/bin/env python3
"""Tests for the VISTA Time Utilities package."""

from __future__ import annotations

from datetime import timedelta, timezone
import unittest

from vista_time import (
    create_future_timestamp,
    format_duration,
    from_iso_format,
    get_current_utc_time,
    is_expired,
    to_iso_format,
)
from vista_time.compat import legacy_shim


class TestVistaTimePackage(unittest.TestCase):
    def test_basic_roundtrip(self):
        now = get_current_utc_time()
        self.assertEqual(now.tzinfo, timezone.utc)

        iso = to_iso_format(now)
        self.assertIn("T", iso)

        parsed = from_iso_format(iso)
        self.assertEqual(parsed, now)

    def test_expiration_logic(self):
        future = create_future_timestamp(hours=1)
        past = create_future_timestamp(hours=-1)

        self.assertFalse(is_expired(future))
        self.assertTrue(is_expired(past))

    def test_format_duration(self):
        start = to_iso_format(get_current_utc_time())
        end = to_iso_format(get_current_utc_time() + timedelta(minutes=5))
        formatted = format_duration(start, end)
        self.assertIn("5m", formatted)

    def test_legacy_shim(self):
        now = legacy_shim.get_current_utc_time()
        iso = legacy_shim.to_iso_format(now)
        self.assertEqual(now.tzinfo, timezone.utc)
        self.assertIn("T", iso)


if __name__ == "__main__":
    unittest.main()
