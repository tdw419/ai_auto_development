import sqlite3
from typing import List, Optional, Dict, Any

class Store:
    def __init__(self, db_path: str = "vista_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    created_at REAL,
                    title TEXT,
                    description TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    kind TEXT,
                    path TEXT,
                    blob_sha256 TEXT,
                    content_ref TEXT,
                    produced_by_task TEXT,
                    parents_json TEXT,
                    metadata_json TEXT,
                    created_at REAL
                )
            """)
            conn.execute("""
              CREATE TABLE IF NOT EXISTS verdicts(
                artifact_id TEXT PRIMARY KEY,
                project_id  TEXT,
                task_id     TEXT,
                created_at  REAL,
                verdict_json TEXT
              )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_verdicts_project_task ON verdicts(project_id, task_id)")

    def put_artifact(self, artifact):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO artifacts
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact.artifact_id,
                artifact.project_id,
                artifact.kind,
                artifact.path,
                artifact.blob_sha256,
                artifact.content_ref,
                artifact.produced_by_task,
                __import__('json').dumps(artifact.parents),
                __import__('json').dumps(artifact.metadata),
                artifact.created_at
            ))

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?",
                (artifact_id,)
            ).fetchone()

        if not row:
            return None

        return {
            "artifact_id":row[0],
            "project_id":row[1],
            "kind":row[2],
            "path":row[3],
            "blob_sha256":row[4],
            "content_ref":row[5],
            "produced_by_task":row[6],
            "parents":__import__('json').loads(row[7]),
            "metadata":__import__('json').loads(row[8]),
            "created_at":row[9]
        }

    def list_artifacts(self, project_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE project_id = ? ORDER BY created_at",
                (project_id,)
            ).fetchall()

        return [{
            "artifact_id":row[0],
            "project_id":row[1],
            "kind":row[2],
            "path":row[3],
            "blob_sha256":row[4],
            "content_ref":row[5],
            "produced_by_task":row[6],
            "parents":__import__('json').loads(row[7]),
            "metadata":__import__('json').loads(row[8]),
            "created_at":row[9]
        } for row in rows]

    def has_artifact(self, artifact_id: str) -> bool:
        return self.get_artifact(artifact_id) is not None

    def create_project(self, project_id: str, title: str = "", description: str = ""):
        """Create a new project"""
        import time
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects VALUES (?, ?, ?, ?)",
                (project_id, time.time(), title or project_id, description)
            )

    def list_projects(self) -> List[str]:
        """List all project IDs from the projects table"""
        project_ids = set()

        # Get from projects table
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT project_id FROM projects ORDER BY project_id"
            ).fetchall()
            project_ids.update(r[0] for r in rows)

        return sorted(project_ids)

    def put_verdict(self, verdict: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""INSERT OR REPLACE INTO verdicts
                         VALUES (?, ?, ?, ?, ?)""", (
                verdict.get("artifact_id"),
                verdict.get("project_id"),
                verdict.get("task_id"),
                __import__('time').time(),
                __import__('json').dumps(verdict, separators=(",",":"))
            ))

    def get_verdict(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("SELECT verdict_json FROM verdicts WHERE artifact_id=?",
                            (artifact_id,)).fetchone()
        return __import__('json').loads(row[0]) if row else None
