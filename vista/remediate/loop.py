from ..contracts.artifact_v2 import Artifact
from ..contracts.task_spec_v2 import TaskSpec
from ..memory.graph import ArtifactGraph

class FailureClassifier:  # tiny rules first, model later
    MAP = {
        "ImportError": "dependency",
        "TypeError": "typing",
        "KeyError": "schema_drift",
        "SQL": "migration",
        "Timeout": "performance",
        "Semgrep": "security",
    }
    def classify(self, findings: list[str]) -> list[str]:
        tags=set()
        for f in findings:
            for k,v in self.MAP.items():
                if k.lower() in f.lower(): tags.add(v)
        return sorted(tags or {"unknown"})

class Remediator:
    def run(self, artifact, spec, verify_report, g):
        tags = FailureClassifier().classify(
            sum((r.get('findings', []) for r in verify_report["results"]), [])
        )
        # choose recipe chain by tags; emit patch artifact
        ...
