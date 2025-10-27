from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from enum import Enum

Role = Literal["data_eng", "api_arch", "frontend", "security", "devops", "qa", "ml", "mobile", "cloud"]
JudgeKind = Literal["probe", "adv", "meta"]

class TaskState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class TaskSpec(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    project_id: str = Field(..., description="Project this task belongs to")
    role: Role = Field(..., description="Specialist role required")
    goal: str = Field(..., description="Human-readable objective")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Upstream artifacts and context")
    deliverables: List[str] = Field(default_factory=list, description="Expected output file patterns")
    acceptance: List[str] = Field(default_factory=list, description="Must-pass assertions")
    risk_flags: List[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5, description="1=critical, 5=background")
    state: TaskState = Field(default=TaskState.PENDING)
    depends_on: List[str] = Field(default_factory=list, description="Task dependencies")

    class Config:
        use_enum_values = True
