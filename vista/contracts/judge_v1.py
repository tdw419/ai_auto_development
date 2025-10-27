from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List
from .artifact_v2 import Artifact
from .task_spec_v2 import TaskSpec

class JudgeInput(BaseModel):
    project_id: str
    task_id: str
    artifact: Artifact
    spec: TaskSpec
    context_artifacts: List[Artifact] = Field(default_factory=list)

class JudgeResult(BaseModel):
    judge: Literal["probe", "adv", "meta", "perf", "sec"]
    pass_: bool = Field(..., alias="pass")
    score: float = Field(..., ge=0, le=1, description="0..1 confidence score")
    findings: List[str] = Field(default_factory=list, description="Failing cases, vulnerabilities, inconsistencies")
    suggested_fixes: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
