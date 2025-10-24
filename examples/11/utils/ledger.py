"""
Verification ledger utilities for storing VISTA judge outcomes.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.time_utils import to_iso, utc_now


LEDGER_PATH = Path("data/verification_ledger.db")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            timestamp TEXT,
            objective_pass INTEGER,
            adversarial_severity TEXT,
            meta_decision TEXT,
            defect_capsule TEXT,
            confidence REAL,
            errors TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS adversarial_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verification_id INTEGER,
            finding_type TEXT,
            description TEXT,
            severity TEXT,
            file_path TEXT,
            line_number INTEGER,
            FOREIGN KEY (verification_id) REFERENCES verification_records(id)
        )
        """
    )
    conn.commit()


def _open_ledger() -> sqlite3.Connection:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LEDGER_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def update_verification_ledger(entry: Dict[str, Any]) -> None:
    conn = _open_ledger()
    cursor = conn.cursor()
    timestamp = entry.get("timestamp") or to_iso(utc_now())
    cursor.execute(
        """
        INSERT INTO verification_records
        (task_id, timestamp, objective_pass, adversarial_severity, meta_decision, defect_capsule, confidence, errors)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.get("task_id"),
            timestamp,
            1 if entry.get("objective_pass") else 0,
            entry.get("adversarial_severity", "none"),
            entry.get("meta_decision", "UNKNOWN"),
            json.dumps(entry.get("defect_capsule")) if entry.get("defect_capsule") else None,
            entry.get("confidence", 0.0),
            json.dumps(entry.get("errors", [])),
        ),
    )
    verification_id = cursor.lastrowid

    for finding in entry.get("adversarial_findings", []):
        cursor.execute(
            """
            INSERT INTO adversarial_findings
            (verification_id, finding_type, description, severity, file_path, line_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                verification_id,
                finding.get("type", "unknown"),
                finding.get("description", ""),
                finding.get("severity", "low"),
                finding.get("file_path"),
                finding.get("line_number"),
            ),
        )

    conn.commit()
    conn.close()


def get_verification_history(task_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _open_ledger()
    cursor = conn.cursor()
    if task_id:
        cursor.execute(
            """
            SELECT * FROM verification_records
            WHERE task_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (task_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM verification_records
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
    rows = cursor.fetchall()
    conn.close()

    history: List[Dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        if record.get("defect_capsule"):
            record["defect_capsule"] = json.loads(record["defect_capsule"])
        if record.get("errors"):
            record["errors"] = json.loads(record["errors"])
        history.append(record)
    return history
