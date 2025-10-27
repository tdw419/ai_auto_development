from ...contracts.task_spec_v2 import TaskSpec
from ...contracts.artifact_v2 import Artifact
from ...memory.graph import ArtifactGraph
from ...contracts.stamping import stamp_artifact
import json
import os
import hashlib

class UnitTestCard:
    """Generates unit tests for code artifacts."""
    provides = ["unit_tests"]
    requires = ["codebase"]

    def run(self, spec: TaskSpec, graph: ArtifactGraph) -> Artifact:
        # This is a placeholder for a real unit test generation implementation.
        # In a real scenario, this would use an LLM or static analysis to generate tests.

        test_content = """
import pytest

def test_placeholder():
    assert True
"""
        content_hash = hashlib.sha256(test_content.encode()).hexdigest()
        content_path = f"./artifacts/{content_hash}"
        os.makedirs(os.path.dirname(content_path), exist_ok=True)
        with open(content_path, "w") as f:
            f.write(test_content)

        art = Artifact(
            artifact_id=f"unit_tests_{spec.task_id}",
            project_id=spec.project_id,
            kind="tests",
            path=content_path,
            blob_sha256=content_hash,
            content_ref=content_path,
            produced_by_task=spec.task_id,
            parents=spec.inputs.get("code_artifacts", []),
            metadata={"test_count": 1, "framework": "pytest"}
        )
        return stamp_artifact(art, runner_id="python311")
