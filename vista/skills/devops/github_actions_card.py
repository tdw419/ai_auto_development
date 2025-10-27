from ...contracts.task_spec_v2 import TaskSpec
from ...contracts.artifact_v2 import Artifact
from ...memory.graph import ArtifactGraph
from ...contracts.stamping import stamp_artifact
import os
import hashlib

class GitHubActionsCard:
    """Generates a GitHub Actions CI workflow for a Python application."""
    provides = ["ci_cd_pipeline"]
    requires = ["codebase"]

    def run(self, spec: TaskSpec, graph: ArtifactGraph) -> Artifact:
        ci_workflow_content = """
name: Python CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Test with pytest
      run: |
        pip install pytest
        pytest
"""
        content_hash = hashlib.sha256(ci_workflow_content.encode()).hexdigest()
        content_path = f"./artifacts/{content_hash}"
        os.makedirs(os.path.dirname(content_path), exist_ok=True)
        with open(content_path, "w") as f:
            f.write(ci_workflow_content)

        art = Artifact(
            artifact_id=f"github_actions_{spec.task_id}",
            project_id=spec.project_id,
            kind="ci_cd_pipeline",
            path=content_path,
            blob_sha256=content_hash,
            content_ref=content_path,
            produced_by_task=spec.task_id,
            parents=spec.inputs.get("code_artifacts", []),
            metadata={"workflow_name": "Python CI"}
        )
        return stamp_artifact(art, runner_id="python311")
