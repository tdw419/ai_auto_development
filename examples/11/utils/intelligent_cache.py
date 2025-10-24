"""VISTA intelligent caching system."""
from __future__ import annotations

import hashlib
import os
import json
import re
import sqlite3
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional

from utils.time_utils import future_iso, to_iso, utc_now

CACHE_DIR = Path(os.getenv("VISTA_CACHE_DIR", "data/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

LLM_DB = CACHE_DIR / "llm_cache.db"
VERIFICATION_DB = CACHE_DIR / "verification_cache.db"
PATTERN_DB = CACHE_DIR / "pattern_cache.db"


class IntelligentCache:
    """Multi-layer cache with semantic fallbacks."""

    def __init__(self) -> None:
        self._ensure_schema()
        self.llm_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.verification_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.pattern_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_items = 512

    # ------------------------------------------------------------------
    # LLM cache
    # ------------------------------------------------------------------
    def get_llm_response(self, prompt: str, model: str, temperature: float) -> Optional[Any]:
        key = self._llm_key(prompt, model, temperature)
        if key in self.llm_cache:
            self.llm_cache.move_to_end(key)
            return self.llm_cache[key]["response"]
        conn = sqlite3.connect(LLM_DB)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT response FROM llm_cache
            WHERE cache_key=? AND expires_at>?
            """,
            (key, to_iso(utc_now())),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            data = json.loads(row[0])
            self._store_memory(self.llm_cache, key, {"response": data})
            return data
        return None

    def store_llm_response(self, prompt: str, model: str, temperature: float, response: Any, ttl_hours: int = 24) -> None:
        key = self._llm_key(prompt, model, temperature)
        payload = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "response": response,
        }
        self._store_memory(self.llm_cache, key, payload)
        conn = sqlite3.connect(LLM_DB)
        cursor = conn.cursor()
        created_at = utc_now()
        cursor.execute(
            """REPLACE INTO llm_cache
            (cache_key, prompt, model, temperature, response, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                prompt,
                model,
                temperature,
                json.dumps(response),
                to_iso(created_at),
                future_iso(hours=ttl_hours),
            ),
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        return {
            "llm": {
                "memory_items": len(self.llm_cache),
                "stored_rows": self._count_rows(LLM_DB, "llm_cache"),
            },
            "verification": {
                "memory_items": len(self.verification_cache),
                "stored_rows": self._count_rows(VERIFICATION_DB, "verification_cache"),
            },
            "patterns": {
                "memory_items": len(self.pattern_cache),
                "stored_rows": self._count_rows(PATTERN_DB, "pattern_cache"),
            },
        }

    def cleanup(self) -> Dict[str, int]:
        removed = {
            "llm": self._cleanup_db(LLM_DB, "llm_cache"),
            "verification": self._cleanup_db(VERIFICATION_DB, "verification_cache"),
            "patterns": self._cleanup_db(PATTERN_DB, "pattern_cache"),
        }
        self.llm_cache.clear()
        self.verification_cache.clear()
        self.pattern_cache.clear()
        return removed

    # ------------------------------------------------------------------
    # Verification cache
    # ------------------------------------------------------------------
    def get_verification_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if cache_key in self.verification_cache:
            self.verification_cache.move_to_end(cache_key)
            return self.verification_cache[cache_key]["result"]

        conn = sqlite3.connect(VERIFICATION_DB)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT result FROM verification_cache
            WHERE cache_key=? AND expires_at>?""",
            (cache_key, future_iso()),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            data = json.loads(row[0])
            self._store_memory(self.verification_cache, cache_key, {"result": data})
            return data
        return None

    def store_verification_result(
        self,
        cache_key: str,
        result: Dict[str, Any],
        *,
        ttl_hours: int = 12,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "result": result,
            "task_id": task_id,
            "metadata": metadata or {},
        }
        self._store_memory(self.verification_cache, cache_key, payload)

        conn = sqlite3.connect(VERIFICATION_DB)
        cursor = conn.cursor()
        created_at = utc_now()
        cursor.execute(
            """REPLACE INTO verification_cache
            (cache_key, task_id, metadata, result, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                cache_key,
                task_id,
                json.dumps(metadata or {}),
                json.dumps(result),
                to_iso(created_at),
                future_iso(hours=ttl_hours),
            ),
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        ddl_statements = [
            (
                LLM_DB,
                """CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    prompt TEXT,
                    model TEXT,
                    temperature REAL,
                    response TEXT,
                    created_at TEXT,
                    expires_at TEXT
                )""",
            ),
            (
                VERIFICATION_DB,
                """CREATE TABLE IF NOT EXISTS verification_cache (
                    cache_key TEXT PRIMARY KEY,
                    task_id TEXT,
                    metadata TEXT,
                    result TEXT,
                    created_at TEXT,
                    expires_at TEXT
                )""",
            ),
            (
                PATTERN_DB,
                """CREATE TABLE IF NOT EXISTS pattern_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT,
                    created_at TEXT,
                    expires_at TEXT
                )""",
            ),
        ]
        for db, ddl in ddl_statements:
            conn = sqlite3.connect(db)
            conn.execute(ddl)
            conn.commit()
            conn.close()

    def _cleanup_db(self, db_path: Path, table: str) -> int:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE expires_at<=?", (to_iso(utc_now()),))
        removed = cursor.rowcount
        conn.commit()
        conn.close()
        return removed

    def _count_rows(self, db_path: Path, table: str) -> int:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
        except sqlite3.DatabaseError:
            count = 0
        conn.close()
        return count

    def _store_memory(self, cache: OrderedDict, key: str, value: Dict[str, Any]) -> None:
        cache[key] = value
        cache.move_to_end(key)
        if len(cache) > self.max_items:
            cache.popitem(last=False)

    def _llm_key(self, prompt: str, model: str, temperature: float) -> str:
        normalized = re.sub(r"\s+", " ", prompt.strip())
        base = f"{normalized}|{model}|{temperature:.2f}"
        return hashlib.md5(base.encode()).hexdigest()


_cache: Optional[IntelligentCache] = None


def get_cache() -> IntelligentCache:
    global _cache
    if _cache is None:
        _cache = IntelligentCache()
    return _cache
