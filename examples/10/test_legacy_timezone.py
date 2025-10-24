#!/usr/bin/env python3
"""Tests for legacy timezone handling."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from path_shim import get_current_utc_time, to_iso_format  # noqa: E402
from agents import run_agent_workflow  # noqa: E402
from db_manager import LanceDBManager  # noqa: E402


class TestLegacyTimezone(unittest.TestCase):
    def test_path_shim(self):
        now = get_current_utc_time()
        iso = to_iso_format(now)
        self.assertIsNotNone(now.tzinfo)
        self.assertIn("T", iso)
        self.assertTrue(iso.endswith("Z") or "+" in iso)

    def test_agent_workflow_timestamps(self):
        result = run_agent_workflow({"demo": "task"})
        self.assertIn("started_at", result)
        self.assertIn("completed_at", result)
        self.assertIn("T", result["started_at"])
        self.assertIn("T", result["completed_at"])

    def test_database_records_timezone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir)
            manager = LanceDBManager(db_path=str(db_path))
            manager.store_turn(
                turn_id="legacy-test",
                agent_role="builder",
                content="demo",
                embedding=[0.0] * 768,
                metadata={"task_id": "legacy", "turn_number": 0, "status": "passed"},
            )

            df = manager.turns_table.to_pandas()
            record = df[df["turn_id"] == "legacy-test"].iloc[0]
            self.assertIn("T", record["timestamp"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
