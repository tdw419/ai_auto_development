import subprocess, tempfile, os, shutil
from typing import Dict, Any
from ..contracts.artifact_v2 import Artifact
from .context import RunnerRegistry

class Node22Runner:
    def __init__(self, image: str = "node:22-alpine"):
        self.runner_id = f"docker:{image}"
        self.image = image

    def execute_script(self, artifact: Artifact, command="run") -> Dict[str, Any]:
        if not artifact.path or not os.path.exists(artifact.path):
            return {"success": False, "error": "Artifact path not accessible", "runner_id": self.runner_id}
        tmp = tempfile.mkdtemp(prefix="vista_node_")
        try:
            dst = os.path.join(tmp, os.path.basename(artifact.path))
            open(dst,"w").write(open(artifact.path).read())
            args = [
              "docker","run","--rm","--network","none",
              "-v", f"{tmp}:/work:ro","-w","/work",
              self.image,"node", os.path.basename(dst)
            ]
            p = subprocess.run(args, capture_output=True, text=True, timeout=120)
            return {"success": p.returncode==0, "exit_code": p.returncode,
                    "stdout": p.stdout, "stderr": p.stderr, "runner_id": self.runner_id}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

RunnerRegistry.register("node22", Node22Runner())
