import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vista_specialists.communication.agent_bus import AgentCommunicationBus
from vista_specialists.database.agent_db import AgentDatabase
from vista_specialists.agents.specialists.enhanced_coordinator import EnhancedCoordinator
from unittest.mock import MagicMock, patch

# Mock base classes and enums as they are not provided in full.
# This allows testing the integration logic.
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
    timestamp: str = "2023-10-27T10:00:00Z" # Add timestamp for db compatibility

# Mock the base specialist to avoid LLM calls
@patch('vista_specialists.agents.base.BaseSpecialist', new=MagicMock())
def test_agent_communication():
    """Test that agents can communicate and share artifacts"""
    # We need to import the communicating specialists after patching BaseSpecialist
    from vista_specialists.agents.specialists.communicating_data_engineer import CommunicatingDataEngineer
    from vista_specialists.agents.specialists.communicating_api_architect import CommunicatingAPIArchitect

    comm_bus = AgentCommunicationBus()
    db = AgentDatabase(":memory:")

    data_engineer = CommunicatingDataEngineer(comm_bus, db)
    api_architect = CommunicatingAPIArchitect(comm_bus, db)

    # Implement the abstract `run_inference_with_prompt` method for the test
    def de_run_inference(task, prompt):
        return SpecialistOutput(
            task_id=task.task_id, specialist_type=SpecialistRole.DATA_ENGINEER,
            output_artifacts={"database_schema": {"users": ["id", "name"]}},
            confidence=0.9, success=True
        )
    data_engineer.run_inference_with_prompt = de_run_inference

    def aa_run_inference(task, prompt):
        return SpecialistOutput(
            task_id=task.task_id, specialist_type=SpecialistRole.API_ARCHITECT,
            output_artifacts={"api_schema": {"endpoints": ["/users"]}},
            confidence=0.9, success=True
        )
    api_architect.run_inference_with_prompt = aa_run_inference


    project_id = "test_project_001"
    db.create_project(project_id=project_id, name="Test Project", description="Testing agent communication")

    schema_task = SpecialistTask(
        task_id="test-schema-1",
        specialist_type=SpecialistRole.DATA_ENGINEER,
        objective="Create a user table schema",
        constraints={},
        context={"project_id": project_id}
    )

    schema_result = data_engineer.execute_task(schema_task)

    api_task = SpecialistTask(
        task_id="test-api-1",
        specialist_type=SpecialistRole.API_ARCHITECT,
        objective="Create API endpoints for user management",
        constraints={},
        context={"project_id": project_id}
    )

    # Manually call _gather_context to simulate the flow for api_architect
    api_architect._gather_context(api_task)

    assert "data_engineer.database_schema" in api_task.context
    assert api_task.context["data_engineer.database_schema"] == {"users": ["id", "name"]}

    # Now execute the task which will use the gathered context
    api_result = api_architect.execute_task(api_task)
    assert api_result.success

    artifacts = db.get_project_artifacts(project_id)
    assert len(artifacts) >= 2

    print("✅ Agent communication test passed")

@patch('vista_specialists.agents.base.BaseSpecialist', new=MagicMock())
def test_enhanced_coordinator():
    """Test the enhanced coordinator with a full project"""
    # We need this import to happen after the patch
    from vista_specialists.agents.specialists.enhanced_coordinator import EnhancedCoordinator

    coordinator = EnhancedCoordinator()

    # Implement the abstract `run_inference_with_prompt` method for each specialist
    for role, specialist in coordinator.specialists.items():
        def specialist_run_inference(task, prompt, r=role, s=specialist):
            return SpecialistOutput(
                task_id=task.task_id,
                specialist_type=r,
                output_artifacts={f"mock_{s.capability.name}_artifact": {}},
                confidence=0.9,
                success=True
            )
        specialist.run_inference_with_prompt = specialist_run_inference


    result = coordinator.execute_conversational_plan(
        "Create a simple blog with users, posts, and comments",
        "Test Blog Project"
    )

    assert "project_id" in result
    assert "artifacts" in result
    assert len(result["artifacts"]) > 0

    project_summary = coordinator.get_project_summary(result["project_id"])
    assert project_summary["project"].name == "Test Blog Project"
    assert len(project_summary["artifacts_by_agent"]) > 0

    print("✅ Enhanced coordinator test passed")

if __name__ == "__main__":
    # This setup is needed to run tests directly because of the patching.
    # A proper conftest.py would be better in a real project.

    # Mock the base module before imports
    import sys
    from unittest.mock import MagicMock

    # Create a mock for the entire base module
    mock_base = MagicMock()
    mock_base.SpecialistRole = SpecialistRole
    mock_base.SpecialistTask = SpecialistTask
    mock_base.SpecialistOutput = SpecialistOutput
    mock_base.BaseSpecialist = MagicMock()
    mock_base.SpecialistCapability = SpecialistCapability

    sys.modules['vista_specialists.agents.base'] = mock_base

    test_agent_communication()
    test_enhanced_coordinator()
    print("🎉 All communication tests passed!")
