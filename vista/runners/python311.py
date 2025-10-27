import subprocess
import tempfile
import os
import hashlib
from typing import Dict, Any, Optional
from ..contracts.artifact_v2 import Artifact
from .context import RunnerRegistry

class Python311Runner:
    """Python 3.11 sandbox runner with uv/venv support and safety checks"""

    def __init__(self, base_path: str = "./runners/python311"):
        self.runner_id = "python311"
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self.denylist = [
            "rm -rf /", "sudo ", "curl http", "wget http", "ssh ",
            "import os.system", "subprocess.call", "eval(", "exec(",
            "__import__('os')", "open('/etc/'", "open('/proc/'"
        ]

    def safety_check(self, artifact: Artifact) -> Optional[Dict[str, Any]]:
        """Basic safety check to prevent host system abuse"""
        if not artifact.path or not os.path.exists(artifact.path):
            return None

        try:
            with open(artifact.path, 'r', errors='ignore') as f:
                content = f.read().lower()

            for dangerous_pattern in self.denylist:
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
        """Execute a Python script in sandboxed environment"""

        # Safety check first
        safety_result = self.safety_check(artifact)
        if safety_result:
            return safety_result

        if not artifact.path or not os.path.exists(artifact.path):
            return {"success": False, "error": "Artifact path not accessible"}

        # Create isolated environment
        with tempfile.TemporaryDirectory(prefix="vista_py311_") as tmpdir:
            # Copy script to temp directory
            script_name = os.path.basename(artifact.path)
            temp_script = os.path.join(tmpdir, script_name)
            with open(artifact.path, 'r') as src, open(temp_script, 'w') as dst:
                dst.write(src.read())

            # Try to run with uv if available, fallback to python
            try:
                # Create uv environment
                subprocess.run(["uv", "venv", os.path.join(tmpdir, ".venv")],
                             check=True, capture_output=True, cwd=tmpdir)

                # Run the script
                if command == "test":
                    result = subprocess.run(
                        ["uv", "run", "pytest", temp_script],
                        capture_output=True, text=True, timeout=30, cwd=tmpdir
                    )
                else:
                    result = subprocess.run(
                        ["uv", "run", "python", temp_script],
                        capture_output=True, text=True, timeout=30, cwd=tmpdir
                    )

                return {
                    "success": result.returncode == 0,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "runner_id": self.runner_id,
                    "timed_out": False
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "Execution timeout",
                    "runner_id": self.runner_id,
                    "timed_out": True
                }
            except FileNotFoundError:
                # Fallback to system python
                try:
                    result = subprocess.run(
                        ["python3.11", temp_script],
                        capture_output=True, text=True, timeout=30
                    )
                    return {
                        "success": result.returncode == 0,
                        "exit_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "runner_id": f"{self.runner_id}-system",
                        "timed_out": False
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Fallback execution failed: {e}",
                        "runner_id": self.runner_id
                    }

# Auto-register runner
RunnerRegistry.register("python311", Python311Runner())
