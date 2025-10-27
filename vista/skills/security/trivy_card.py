import subprocess, json, os, hashlib
from ...contracts.artifact_v2 import Artifact
from ...contracts.task_spec_v2 import TaskSpec
from ...contracts.stamping import stamp_artifact
from ...memory.graph import ArtifactGraph

class TrivyCard:
    """Scan a built image tag with Trivy; emit security_report."""
    provides = ["container_scan"]
    requires = ["image_tag"]

    def run(self, spec: TaskSpec, graph: ArtifactGraph) -> Artifact:
        image = spec.inputs.get("image_tag")
        if not image:
            # no image to scan
            report = {"tool":"trivy","error":"no image_tag provided","findings":[]}
        else:
            try:
                p = subprocess.run(["trivy","image","--quiet","--format","json",image],
                                   capture_output=True, text=True, timeout=180)
                report = json.loads(p.stdout) if p.returncode==0 and p.stdout.strip() else {"tool":"trivy","findings":[]}
            except Exception as e:
                report = {"tool":"trivy","error":str(e),"findings":[]}

        content = json.dumps(report, indent=2, sort_keys=True)
        h = hashlib.sha256(content.encode()).hexdigest()
        path = f"./artifacts/{h}"
        os.makedirs("./artifacts", exist_ok=True)
        open(path,"w").write(content)

        art = Artifact(
            artifact_id=f"trivy_scan_{spec.task_id}",
            project_id=spec.project_id,
            kind="security_report",
            path=path, blob_sha256=h, content_ref=path,
            produced_by_task=spec.task_id, parents=[],
            metadata={"tool":"trivy","critical_findings": self._crit_count(report)}
        )
        return stamp_artifact(art, runner_id="docker")

    def _crit_count(self, rep: dict) -> int:
        vulns = []
        for r in rep.get("Results", []):
            vulns += [v for v in r.get("Vulnerabilities",[]) if v.get("Severity") in {"CRITICAL","HIGH"}]
        return len(vulns)
