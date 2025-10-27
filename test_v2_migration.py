#!/usr/bin/env python3
"""
Test the V2 migration with a simple blog project
"""
import tempfile
import os
from vista.contracts.task_spec_v2 import TaskSpec, TaskState
from vista.contracts.artifact_v2 import Artifact
from vista.memory.store import Store
from vista.memory.graph import ArtifactGraph
from vista.verify.harness import VerdictEngine
from vista.skills.security.sast_card import SASTCard

def ensure_example_file():
    """Create example code file for SAST to scan"""
    os.makedirs("./examples", exist_ok=True)
    p = "./examples/blog_app.py"
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write('''"""
Simple blog application for VISTA V-Loop testing
"""
import sqlite3
from typing import List, Optional

def get_recent_posts(limit: int = 10) -> List[dict]:
    """Fetch recent blog posts"""
    # This is test code - in real app, use proper error handling
    conn = sqlite3.connect("blog.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM posts ORDER BY created_at DESC LIMIT {limit}"
    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]

def hello(name: str) -> str:
    return f'Hello {name}!'

if __name__ == "__main__":
    print(hello("VISTA"))
''')
    return p

def test_v2_system():
    """End-to-end test of the V2 system"""
    print("🧪 Testing VISTA V-Loop V2 Migration...")

    # Use a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
        store = Store(db_path=db_file.name)
        graph = ArtifactGraph(store)
        verifier = VerdictEngine()

        # Create a test project
        project_id = "test_blog_v2"

        # Create sample code file and artifact
        code_path = ensure_example_file()

        # Calculate actual file hash for realism
        import hashlib
        with open(code_path, 'rb') as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()

        code_artifact = Artifact(
            artifact_id="blog_code_v1",
            project_id=project_id,
            kind="code",
            path=code_path,
            blob_sha256=content_hash,
            content_ref=f"./artifacts/{content_hash}",
            produced_by_task="initial_code_gen",
            parents=[],
            metadata={"lines": 25, "language": "python", "runner_id": "python311"}
        )
        store.put_artifact(code_artifact)
        graph.sync_from_store(project_id)

        # Create security scan task
        security_task = TaskSpec(
            task_id="security_scan_001",
            project_id=project_id,
            role="security",
            goal="Scan blog application for vulnerabilities",
            inputs={"code_artifacts": [code_artifact.artifact_id]},
            deliverables=["security_report.json"],
            acceptance=["No critical vulnerabilities found"],
            priority=2
        )

        # Run SAST card
        sast = SASTCard()
        security_report = sast.run(security_task, graph)
        store.put_artifact(security_report)

        # Verify the security report
        graph.sync_from_store(project_id)  # Refresh with new artifact
        verification = verifier.verify(security_report, security_task, graph)

        print(f"✅ Security scan completed: {verification['pass']}")
        print(f"✅ Overall score: {verification['overall_score']:.2f}")
        print(f"✅ Judges executed: {len(verification['results'])}")

        # Test artifact graph
        context = graph.neighborhood(security_report.artifact_id)
        print(f"✅ Graph context: {len(context)} related artifacts")

        # Verify response structure
        assert "artifact_id" in verification
        assert "runner_id" in verification
        for result in verification["results"]:
            assert "pass" in result  # Should be aliased from pass_

        print("🎉 V2 Migration Test Successful!")
        return verification

if __name__ == "__main__":
    test_v2_system()
