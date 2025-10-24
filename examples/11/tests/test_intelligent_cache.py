#!/usr/bin/env python3
import importlib
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def _load_cache_module(cache_dir: Path):
    os.environ["VISTA_CACHE_DIR"] = str(cache_dir)
    from utils import intelligent_cache  # local import for reload

    importlib.reload(intelligent_cache)
    intelligent_cache._cache = None
    return intelligent_cache


class TestIntelligentCache(unittest.TestCase):
    def setUp(self):
        self.tempdir = Path(tempfile.mkdtemp())
        cache_module = _load_cache_module(self.tempdir / "cache")
        self.cache_module = cache_module
        self.cache = cache_module.IntelligentCache()

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ.pop("VISTA_CACHE_DIR", None)
        importlib.reload(self.cache_module)
        self.cache_module._cache = None

    def test_llm_cache_roundtrip(self):
        prompt = '{"system":"test","user":"hello","response_format":"json"}'
        payload = {"answer": 42}
        self.cache.store_llm_response(prompt, "demo-model", 0.25, payload, ttl_hours=1)

        cached = self.cache.get_llm_response(prompt, "demo-model", 0.25)
        self.assertEqual(cached, payload)

        cached_again = self.cache.get_llm_response(prompt, "demo-model", 0.25)
        self.assertEqual(cached_again, payload)

    def test_timestamp_records_are_timezone_aware(self):
        prompt = "timezone-check"
        payload = {"note": "tz"}
        self.cache.store_llm_response(prompt, "demo-model", 0.1, payload, ttl_hours=1)

        conn = sqlite3.connect(self.cache_module.LLM_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT created_at, expires_at FROM llm_cache WHERE prompt=?", (prompt,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        created, expires = row
        self.assertTrue(created.endswith("+00:00") or created.endswith("Z"))
        self.assertTrue(expires.endswith("+00:00") or expires.endswith("Z"))

    def test_verification_cache_cleanup(self):
        self.cache.store_verification_result("live", {"pass": True}, ttl_hours=1, task_id="task-1")
        self.cache.store_verification_result("expired", {"pass": False}, ttl_hours=0, task_id="task-1")

        removed = self.cache.cleanup()
        self.assertGreaterEqual(removed["verification"], 1)
        self.assertIsNotNone(self.cache.get_verification_result("live"))
        self.assertIsNone(self.cache.get_verification_result("expired"))
        self.assertNotIn("expired", self.cache.verification_cache)

    def test_expired_llm_entries_removed_after_cleanup(self):
        prompt = "short-ttl"
        payload = {"data": "soon gone"}
        self.cache.store_llm_response(prompt, "demo-model", 0.2, payload, ttl_hours=0)
        key = self.cache._llm_key(prompt, "demo-model", 0.2)
        self.assertIn(key, self.cache.llm_cache)

        time.sleep(0.1)
        removed = self.cache.cleanup()
        self.assertGreaterEqual(removed["llm"], 1)
        self.assertNotIn(key, self.cache.llm_cache)
        self.assertIsNone(self.cache.get_llm_response(prompt, "demo-model", 0.2))

    def test_stats_structure(self):
        stats = self.cache.stats()
        self.assertIn("llm", stats)
        self.assertIn("verification", stats)
        self.assertIn("patterns", stats)
        self.assertIn("memory_items", stats["llm"])
        self.assertIn("stored_rows", stats["llm"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
