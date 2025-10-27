from ...contracts.task_spec_v2 import TaskSpec
from ...contracts.artifact_v2 import Artifact
from ...memory.graph import ArtifactGraph
from ...contracts.stamping import stamp_artifact
import os
import hashlib

class DockerfileCard:
    """Generates a Dockerfile for a Python application."""
    provides = ["dockerfile"]
    requires = ["codebase"]

    def run(self, spec: TaskSpec, graph: ArtifactGraph) -> Artifact:
        dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
"""
        content_hash = hashlib.sha256(dockerfile_content.encode()).hexdigest()
        content_path = f"./artifacts/{content_hash}"
        os.makedirs(os.path.dirname(content_path), exist_ok=True)
        with open(content_path, "w") as f:
            f.write(dockerfile_content)

        art = Artifact(
            artifact_id=f"dockerfile_{spec.task_id}",
            project_id=spec.project_id,
            kind="dockerfile",
            path=content_path,
            blob_sha256=content_hash,
            content_ref=content_path,
            produced_by_task=spec.task_id,
            parents=spec.inputs.get("code_artifacts", []),
            metadata={"base_image": "python:3.11-slim"}
        )
        return stamp_artifact(art, runner_id="python311")
