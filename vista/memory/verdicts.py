import sqlite3, json, time
from typing import Optional, Dict, Any

class VerdictStore:
    def __init__(self, db_path: str = "vista_memory.db"):
        self.db_path = db_path
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
              CREATE TABLE IF NOT EXISTS verdicts(
                artifact_id TEXT PRIMARY KEY,
                project_id  TEXT,
                task_id     TEXT,
                created_at  REAL,
                verdict_json TEXT
              )
            """)

    def put(self, verdict: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""INSERT OR REPLACE INTO verdicts
                         VALUES (?, ?, ?, ?, ?)""", (
                verdict.get("artifact_id"),
                verdict.get("project_id"),
                verdict.get("task_id"),
                time.time(),
                json.dumps(verdict, separators=(",",":"))
            ))

    def get(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("SELECT verdict_json FROM verdicts WHERE artifact_id=?",
                            (artifact_id,)).fetchone()
        return json.loads(row[0]) if row else None
