from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List

class SpecialistRole(Enum):
    API_ARCHITECT = "api_architect"
    DATA_ENGINEER = "data_engineer"
    FRONTEND_ARTIST = "frontend_artist"

@dataclass
class SpecialistCapability:
    name: str
    system_prompt: str = "You are a helpful assistant."
    capabilities: List[str] = field(default_factory=list)

@dataclass
class SpecialistTask:
    task_id: str
    specialist_type: SpecialistRole
    objective: str
    constraints: Dict[str, Any]
    context: Dict[str, Any]

@dataclass
class SpecialistOutput:
    task_id: str
    specialist_type: SpecialistRole
    output_artifacts: Dict[str, Any]
    confidence: float
    success: bool
    timestamp: str = "2023-10-27T10:00:00Z"

class BaseSpecialist:
    def __init__(self):
        self.capability = self.define_capability()

    def define_capability(self) -> SpecialistCapability:
        raise NotImplementedError("Specialists must define their capability.")

    def execute_task(self, task: SpecialistTask) -> SpecialistOutput:
        raise NotImplementedError("Specialists must implement execute_task.")
