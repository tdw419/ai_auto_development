"""
SQLite-backed store for remediation history and defect searches.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from utils.time_utils import to_iso, utc_now

RAG_DB = Path("data/rag_history.db")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS defect_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defect_title TEXT,
            defect_data TEXT,
            resolution_strategy TEXT,
            resolved INTEGER DEFAULT 0,
            similarity_score REAL DEFAULT 0.5,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _open_db() -> sqlite3.Connection:
    RAG_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(RAG_DB))
    _ensure_schema(conn)
    return conn


def search_similar_defects(defect_capsule: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Return simple keyword-based matches from the defect history."""
    title = defect_capsule.get("title", "")
    keywords = set(title.lower().split())

    conn = _open_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT defect_data, resolution_strategy, resolved, similarity_score, created_at FROM defect_history "
        "ORDER BY similarity_score DESC, created_at DESC LIMIT ?",
        (limit * 3,),  # fetch more for filtering
    )

    results: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        defect_data = json.loads(row[0])
        resolution = json.loads(row[1])
        resolved = bool(row[2])
        score = row[3]

        score += _keyword_overlap(keywords, defect_data.get("title", ""))
        results.append(
            {
                "defect_data": defect_data,
                "resolution_strategy": resolution,
                "resolved": resolved,
                "similarity_score": score,
                "created_at": row[4],
            }
        )

    conn.close()
    results.sort(key=lambda item: item.get("similarity_score", 0), reverse=True)
    return results[:limit]


def store_remediation_pattern(defect_capsule: Dict[str, Any], remediation_plan: Dict[str, Any]) -> None:
    """Persist remediation plan for future retrieval."""
    conn = _open_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO defect_history (defect_title, defect_data, resolution_strategy, resolved, similarity_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            defect_capsule.get("title", "unknown defect"),
            json.dumps(defect_capsule),
            json.dumps(remediation_plan),
            1,
            0.8,
            to_iso(utc_now()),
        ),
    )
    conn.commit()
    conn.close()


def _keyword_overlap(keywords: set[str], text: str) -> float:
    if not text:
        return 0.0
    words = set(text.lower().split())
    if not words:
        return 0.0
    return len(keywords & words) / len(words)
