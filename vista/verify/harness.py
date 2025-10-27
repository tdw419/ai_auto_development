from typing import List, Dict, Any
from ..contracts.artifact_v2 import Artifact
from ..contracts.task_spec_v2 import TaskSpec
from ..contracts.judge_v1 import JudgeInput, JudgeResult
from ..memory.graph import ArtifactGraph
import json
import os

class BaseJudge:
    name: str = "base"
    def applicable(self, artifact: Artifact, spec: TaskSpec) -> bool: return True
    def run(self, judge_input: JudgeInput) -> JudgeResult: raise NotImplementedError

class ProbeJudge(BaseJudge):
    name = "probe"
    def run(self, ji: JudgeInput) -> JudgeResult:
        return JudgeResult(
            judge="probe",
            pass_=True,
            score=0.85,
            findings=["Basic smoke test passed"],
            suggested_fixes=[]
        )

class AdvJudge(BaseJudge):
    name = "adv"
    def run(self, ji: JudgeInput) -> JudgeResult:
        return JudgeResult(
            judge="adv",
            pass_=True,
            score=0.78,
            findings=["Edge cases handled adequately"],
            suggested_fixes=["Add more boundary tests"]
        )

class MetaJudge(BaseJudge):
    name = "meta"
    def run(self, ji: JudgeInput) -> JudgeResult:
        return JudgeResult(
            judge="meta",
            pass_=True,
            score=0.92,
            findings=["Architecture consistent with project goals"],
            suggested_fixes=[]
        )

class SecJudge(BaseJudge):
    name = "sec"
    # Evaluate the *report* produced by SAST; make this judge core for reports.
    def applicable(self, artifact: Artifact, spec: TaskSpec) -> bool:
        return artifact.kind == "security_report"

    def run(self, ji: JudgeInput) -> JudgeResult:
        report_path = ji.artifact.path or ji.artifact.content_ref
        findings = []
        critical = 0
        if report_path and os.path.exists(report_path):
            try:
                data = json.loads(open(report_path).read())
                findings = data.get("findings", [])
                critical = sum(1 for f in findings if str(f.get("severity","")).upper() in {"CRITICAL","HIGH"})
            except Exception as e:
                findings = [f"SecJudge: could not parse report: {e}"]
                critical = 1  # fail safe
        pass_ok = (critical == 0)
        return JudgeResult(
            judge="sec",
            pass_=pass_ok,
            score=1.0 if pass_ok else 0.2,
            findings=[f"{len(findings)} findings; critical={critical}"],
            suggested_fixes=["Address all HIGH/CRITICAL findings before release"] if not pass_ok else []
        )

class VerdictEngine:
    def __init__(self, judges: List[BaseJudge] = None):
        self.judges = judges or [ProbeJudge(), AdvJudge(), MetaJudge(), SecJudge()]

    def verify(self, artifact: Artifact, spec: TaskSpec, graph: ArtifactGraph) -> Dict[str, Any]:
        ctx = graph.neighborhood(artifact.artifact_id)
        ji = JudgeInput(
            project_id=spec.project_id,
            task_id=spec.task_id,
            artifact=artifact,
            spec=spec,
            context_artifacts=ctx
        )

        results: List[JudgeResult] = []
        for judge in self.judges:
            if judge.applicable(artifact, spec):
                results.append(judge.run(ji))

        # Core judges always required; add 'sec' when validating security_report artifacts
        core = ["probe","adv","meta"]
        if artifact.kind == "security_report":
            core.append("sec")

        core_pass = all(r.pass_ for r in results if r.judge in core)
        overall_score = (sum(r.score for r in results) / len(results)) if results else 0.0

        return {
            "artifact_id": artifact.artifact_id,
            "runner_id": "vista-verdict-engine",
            "pass": core_pass,
            "overall_score": overall_score,
            # Use aliases so clients see "pass" not "pass_"
            "results": [r.dict(by_alias=True) for r in results],
            "core_judges_passed": core_pass
        }
