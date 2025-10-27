import subprocess
import json
import os
import tempfile
import shutil
from typing import Dict, Any
from ..contracts.artifact_v2 import Artifact
from .context import RunnerRegistry
from .policy import DENY_PATTERNS, ALLOW_NET

class DockerRunner:
    def __init__(self, image: str = "python:3.11-slim"):
        self.runner_id = f"docker:{image}"
        self.image = image

    def _ensure_image(self):
        """Pull Docker image if not available"""
        try:
            subprocess.run(
                ["docker", "image", "inspect", self.image],
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            print(f"📥 Pulling Docker image: {self.image}")
            subprocess.run(
                ["docker", "pull", self.image],
                check=False, capture_output=True
            )

    def _safety_check(self, artifact: Artifact) -> Dict[str, Any] | None:
        """Enhanced safety check for containerized execution"""
        if not artifact.path or not os.path.exists(artifact.path):
            return {"success": False, "error": "Artifact path not accessible", "runner_id": self.runner_id}

        try:
            with open(artifact.path, 'r', errors='ignore') as f:
                content = f.read().lower()

            for dangerous_pattern in DENY_PATTERNS:
                if dangerous_pattern in content:
                    return {
                        "success": False,
                        "error": f"Security policy violation: {dangerous_pattern}",
                        "runner_id": self.runner_id
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Safety check failed: {e}",
                "runner_id": self.runner_id
            }

        return None

    def execute_script(self, artifact: Artifact, command: str = "run") -> Dict[str, Any]:
        """Execute script in isolated Docker container"""

        # Safety check first
        safety_result = self._safety_check(artifact)
        if safety_result:
            return safety_result

        # Ensure Docker image is available
        try:
            self._ensure_image()
        except Exception as e:
            return {
                "success": False,
                "error": f"Docker setup failed: {e}",
                "runner_id": self.runner_id
            }

        # Create temporary workspace
        work_dir = tempfile.mkdtemp(prefix="vista_docker_")
        try:
            script_name = os.path.basename(artifact.path)
            dest_script = os.path.join(work_dir, script_name)

            # Copy script to workspace
            with open(artifact.path, 'r') as src, open(dest_script, 'w') as dst:
                dst.write(src.read())

            # Build Docker command
            docker_args = [
                "docker", "run", "--rm",
                "--network", "none" if not ALLOW_NET else "bridge",
                "--pids-limit", "256",
                "--memory", "512m",
                "--cpus", "1.0",
                "-v", f"{work_dir}:/workspace:ro",
                "-w", "/workspace",
                self.image,
                "python", script_name
            ]

            # Execute in container
            try:
                result = subprocess.run(
                    docker_args,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )

                return {
                    "success": result.returncode == 0,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "runner_id": self.runner_id,
                    "timed_out": False,
                    "container_image": self.image
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "Execution timeout (120s)",
                    "runner_id": self.runner_id,
                    "timed_out": True
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Execution failed: {e}",
                "runner_id": self.runner_id
            }
        finally:
            # Cleanup
            shutil.rmtree(work_dir, ignore_errors=True)

# Auto-register
RunnerRegistry.register("docker", DockerRunner())
RunnerRegistry.register("docker-alpine", DockerRunner("python:3.11-alpine"))
