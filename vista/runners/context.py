from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ExecutionContext:
    runner_id: str
    env: Dict[str, Any] = None

    def __post_init__(self):
        if self.env is None:
            self.env = {}

class RunnerRegistry:
    _runners: Dict[str, object] = {}

    @classmethod
    def register(cls, runner_id: str, runner: object):
        cls._runners[runner_id] = runner
        print(f"✅ Registered runner: {runner_id}")

    @classmethod
    def get(cls, runner_id: str) -> Optional[object]:
        return cls._runners.get(runner_id)

    @classmethod
    def list_runners(cls) -> Dict[str, str]:
        return {rid: str(type(runner)) for rid, runner in cls._runners.items()}
