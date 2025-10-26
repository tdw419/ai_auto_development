from __future__ import annotations
import sqlite3, json, time, os, uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sentence_transformers import SentenceTransformer
import lancedb  # assumes LanceDB already used elsewhere
from lancedb.pydantic import LanceModel, Vector
from dataclasses import dataclass

# Define the schema for the LanceDB table to ensure it can be created when empty.
# The vector dimension 384 corresponds to the 'all-MiniLM-L6-v2' model.
class ArtifactEmbeddingModel(LanceModel):
    id: str
    project_id: str
    agent_type: str
    artifact_type: str
    ts: str
    vector: Vector(384)
    preview: str

@dataclass
class Artifact:
    id: str
    project_id: str
    agent_type: str
    artifact_type: str
    content: Dict[str, Any]
    confidence: float
    dependencies: List[str]
    created_at: str

@dataclass
class Project:
    id: str
    name: str
    description: str
    created_at: str
    status: str

class AgentDatabase:
    def __init__(self, db_path: str = "vista_agents.db", lancedb_uri: str = "./lancedb"):
        self.db_path = db_path
        self._ensure_dirs(lancedb_uri)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._init_tables()

        # embeddings
        self._embed = SentenceTransformer("all-MiniLM-L6-v2")
        self._ldb = lancedb.connect(lancedb_uri)
        self._artifacts_tbl = self._ldb.open_table("artifacts_embeddings") \
            if "artifacts_embeddings" in self._ldb.table_names() \
            else self._ldb.create_table("artifacts_embeddings", schema=ArtifactEmbeddingModel)

    def _ensure_dirs(self, lancedb_uri: str):
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        os.makedirs(lancedb_uri, exist_ok=True)

    def _init_tables(self):
        cur = self.conn.cursor()

        # Projects
        cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            created_at TEXT,
            status TEXT
        );""")

        # Artifacts
        cur.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            agent_type TEXT,
            artifact_type TEXT,
            content TEXT,             -- JSON
            confidence REAL,
            dependencies TEXT,        -- JSON array
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );""")

        # FTS over artifact textual content for quick grep-like search
        cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
            id UNINDEXED, project_id, agent_type, artifact_type, text_content
        );
        """)

        # Decisions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY,
            agent_type TEXT,
            context TEXT,
            decision TEXT,
            outcome TEXT,
            confidence REAL,
            created_at TEXT
        );""")

        # Indices
        cur.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_proj ON artifacts(project_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_agent ON artifacts(agent_type);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type  ON artifacts(artifact_type);")

        self.conn.commit()

    # -------- Projects --------
    def create_project(self, project_id: str, name: str, description: str, status: str = "active"):
        self.conn.execute(
            "INSERT OR REPLACE INTO projects (id, name, description, created_at, status) VALUES (?,?,?,?,?)",
            (project_id, name, description, datetime.now(timezone.utc).isoformat(), status)
        )
        self.conn.commit()

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieves a single project by its ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, description, created_at, status FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if row:
            return Project(*row)
        return None

    # -------- Artifacts --------
    def store_artifact(self, project_id: str, output) -> None:
        cur = self.conn.cursor()
        ts = getattr(output, "timestamp", datetime.now(timezone.utc).isoformat())
        deps = getattr(output, "dependencies", []) or []
        for artifact_type, content in output.output_artifacts.items():
            row_id = f"{output.task_id}_{artifact_type}"
            content_json = json.dumps(content, ensure_ascii=False)
            cur.execute("""
                INSERT OR REPLACE INTO artifacts
                (id, project_id, agent_type, artifact_type, content, confidence, dependencies, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (row_id, project_id, output.specialist_type.value, artifact_type,
                  content_json, output.confidence, json.dumps(deps), ts))

            # FTS doc
            text_blob = self._flatten_text(content)
            cur.execute("""
                INSERT INTO artifacts_fts (id, project_id, agent_type, artifact_type, text_content)
                VALUES (?,?,?,?,?)
            """, (row_id, project_id, output.specialist_type.value, artifact_type, text_blob))

            # LanceDB embedding
            vec = self._embed.encode([text_blob])[0].tolist()
            self._artifacts_tbl.add([{
                "id": row_id,
                "project_id": project_id,
                "agent_type": output.specialist_type.value,
                "artifact_type": artifact_type,
                "ts": ts,
                "vector": vec,
                "preview": text_blob[:512]
            }])

        self.conn.commit()

    def get_project_artifacts(self, project_id: str) -> List[Artifact]:
        """Retrieves all artifacts associated with a specific project."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, project_id, agent_type, artifact_type, content, confidence, dependencies, created_at
            FROM artifacts
            WHERE project_id = ?
            ORDER BY created_at ASC
        """, (project_id,))

        return [Artifact(
            id=row[0],
            project_id=row[1],
            agent_type=row[2],
            artifact_type=row[3],
            content=json.loads(row[4]),
            confidence=row[5],
            dependencies=json.loads(row[6]),
            created_at=row[7]
        ) for row in cur.fetchall()]

    def get_related_artifacts(self, agent_type: str, project_id: str, limit: int = 10) -> List[Artifact]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, project_id, agent_type, artifact_type, content, confidence, dependencies, created_at
            FROM artifacts
            WHERE project_id = ? AND agent_type != ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (project_id, agent_type, limit))

        return [Artifact(
            id=row[0],
            project_id=row[1],
            agent_type=row[2],
            artifact_type=row[3],
            content=json.loads(row[4]),
            confidence=row[5],
            dependencies=json.loads(row[6]),
            created_at=row[7]
        ) for row in cur.fetchall()]

    def semantic_search_artifacts(self, query: str, project_id: Optional[str] = None, k: int = 8) -> List[Dict[str, Any]]:
        qvec = self._embed.encode([query])[0].tolist()
        filt = None if project_id is None else f"project_id = '{project_id}'"
        hits = self._artifacts_tbl.search(qvec).where(filt).limit(k).to_list()
        return hits

    def fts_search(self, query: str, project_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        params: Tuple[Any, ...]
        if project_id:
            cur.execute("""
                SELECT id, agent_type, artifact_type, snippet(artifacts_fts, 4, '[', ']', '...', 10)
                FROM artifacts_fts
                WHERE artifacts_fts MATCH ? AND project_id = ?
                LIMIT ?;
            """, (query, project_id, limit))
        else:
            cur.execute("""
                SELECT id, agent_type, artifact_type, snippet(artifacts_fts, 4, '[', ']', '...', 10)
                FROM artifacts_fts
                WHERE artifacts_fts MATCH ?
                LIMIT ?;
            """, (query, limit))
        return [{"id": i, "agent": a, "type": t, "snippet": s} for (i, a, t, s) in cur.fetchall()]

    def _flatten_text(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    # -------- Decisions --------
    def store_decision(self, agent_type: str, context: str, decision: str, outcome: str, confidence: float, metadata: Dict = None):
        """Stores an agent's decision for later analysis and learning."""
        self.conn.execute("""
            INSERT INTO decisions (id, agent_type, context, decision, outcome, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            agent_type,
            context,
            decision,
            outcome,
            confidence,
            datetime.now(timezone.utc).isoformat()
        ))
        self.conn.commit()
