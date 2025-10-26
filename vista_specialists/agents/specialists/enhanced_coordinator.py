import uuid
import time
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from vista_specialists.communication.agent_bus import AgentCommunicationBus
from vista_specialists.database.agent_db import AgentDatabase
from vista_specialists.agents.base import SpecialistRole, SpecialistTask, SpecialistOutput
from vista_specialists.agents.specialists.communicating_api_architect import CommunicatingAPIArchitect
from vista_specialists.agents.specialists.communicating_frontend_artist import CommunicatingFrontendArtist
from vista_specialists.agents.specialists.communicating_data_engineer import CommunicatingDataEngineer

# Mock TaskGenerator as it's not provided yet.
class TaskGenerator:
    def natural_language_to_tasks(self, user_request: str) -> List[Dict]:
        """
        A mock task generator that creates a predefined sequence of tasks.
        """
        print(f"Generating tasks for request: '{user_request}'")
        tasks = [
            {
                "specialist": "data_engineer",
                "objective": "Design and create the database schema based on the user request.",
                "constraints": [],
                "context": {}
            },
            {
                "specialist": "api_architect",
                "objective": "Design the REST API endpoints based on the user request and database schema.",
                "constraints": [],
                "context": {"dependencies": ["database_schema"]}
            },
            {
                "specialist": "frontend_artist",
                "objective": "Design the UI components based on the API specification.",
                "constraints": [],
                "context": {"dependencies": ["api_schema"]}
            }
        ]
        return tasks

class EnhancedCoordinator:
    """Enhanced coordinator with agent communication and database"""

    def __init__(self):
        self.comm_bus = AgentCommunicationBus()
        self.agent_db = AgentDatabase()
        self.specialists = self._create_communicating_specialists()
        self.project_counter = 0
        self.active_projects = {}

    def _create_communicating_specialists(self):
        """Create specialists with communication capabilities"""
        return {
            SpecialistRole.API_ARCHITECT: CommunicatingAPIArchitect(
                self.comm_bus, self.agent_db
            ),
            SpecialistRole.DATA_ENGINEER: CommunicatingDataEngineer(
                self.comm_bus, self.agent_db
            ),
            SpecialistRole.FRONTEND_ARTIST: CommunicatingFrontendArtist(
                self.comm_bus, self.agent_db
            )
        }

    def execute_conversational_plan(self, user_request: str, project_name: str = None) -> Dict:
        """Execute a complete project with enhanced agent communication"""
        if not project_name:
            project_name = f"Project {self.project_counter + 1}"

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        self.agent_db.create_project(
            project_id=project_id,
            name=project_name,
            description=user_request
        )

        self.project_counter += 1
        self.active_projects[project_id] = {
            "name": project_name,
            "request": user_request,
            "started_at": datetime.now(timezone.utc).isoformat()
        }

        print(f"🚀 Starting project: {project_name} (ID: {project_id})")

        task_generator = TaskGenerator()
        tasks = task_generator.natural_language_to_tasks(user_request)

        results = []
        for i, task_spec in enumerate(tasks):
            task = SpecialistTask(
                task_id=str(uuid.uuid4()),
                specialist_type=SpecialistRole(task_spec["specialist"]),
                objective=task_spec["objective"],
                constraints=task_spec["constraints"],
                context={
                    **task_spec["context"],
                    "project_id": project_id,
                    "project_name": project_name,
                    "user_request": user_request,
                    "task_order": i,
                    "total_tasks": len(tasks)
                }
            )

            print(f"📋 Executing task {i+1}/{len(tasks)}: {task.objective}")
            result = self.execute_task(task)
            results.append(result)

            time.sleep(0.1)

        self._update_project_status(project_id, "completed")

        project_artifacts = self.agent_db.get_project_artifacts(project_id)

        return {
            "project_id": project_id,
            "project_name": project_name,
            "user_request": user_request,
            "results": results,
            "artifacts": {f"{a.agent_type}_{a.artifact_type}": a.content for a in project_artifacts},
            "shared_context": self.comm_bus.get_shared_context(),
            "communication_log": [] # Bus does not store a log in the user's version
        }

    def execute_task(self, task: SpecialistTask) -> SpecialistOutput:
        """Execute a single task with the appropriate specialist"""
        specialist_type = task.specialist_type

        if specialist_type not in self.specialists:
            raise ValueError(f"No specialist available for type: {specialist_type}")

        specialist = self.specialists[specialist_type]

        print(f"🎯 Executing {specialist_type.value} task: {task.objective}")

        result = specialist.execute_task(task)

        print(f"✅ {specialist_type.value} completed with confidence: {result.confidence:.2f}")

        return result

    def get_project_summary(self, project_id: str) -> Dict:
        """Get a summary of a project"""
        project = self.agent_db.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        artifacts = self.agent_db.get_project_artifacts(project_id)

        artifacts_by_agent = {}
        for artifact in artifacts:
            if artifact.agent_type not in artifacts_by_agent:
                artifacts_by_agent[artifact.agent_type] = []
            artifacts_by_agent[artifact.agent_type].append(artifact)

        return {
            "project": project,
            "artifacts_by_agent": artifacts_by_agent,
            "total_artifacts": len(artifacts)
        }

    def get_agent_performance(self, agent_type: str) -> Dict:
        """Get performance metrics for an agent"""
        decisions = self.agent_db.get_agent_decisions(agent_type, limit=50)

        if not decisions:
            return {"error": "No decisions found for this agent"}

        successful = sum(1 for d in decisions if d.outcome == "SUCCESS")
        success_rate = successful / len(decisions) * 100

        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)

        return {
            "agent_type": agent_type,
            "total_decisions": len(decisions),
            "success_rate": success_rate,
            "average_confidence": avg_confidence,
            "recent_decisions": decisions[:5]
        }

    def search_artifacts(self, query: str) -> List[Dict]:
        """Search artifacts across all projects"""
        artifacts = self.agent_db.fts_search(query)

        return [
            {
                "id": a.get("id"),
                "project_id": a.get("project_id"),
                "agent_type": a.get("agent"),
                "artifact_type": a.get("type"),
                "content_preview": a.get("snippet", "")[:200] + "...",
            }
            for a in artifacts
        ]

    def _update_project_status(self, project_id: str, status: str):
        """Update project status in database"""
        conn = sqlite3.connect(self.agent_db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE projects SET status = ? WHERE id = ?
        """, (status, project_id))

        conn.commit()
        conn.close()

        if project_id in self.active_projects:
            self.active_projects[project_id]["status"] = status
