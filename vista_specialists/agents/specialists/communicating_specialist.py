import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from vista_specialists.communication.agent_bus import AgentCommunicationBus, BusMessage
from vista_specialists.database.agent_db import AgentDatabase
from vista_specialists.agents.base import BaseSpecialist, SpecialistTask, SpecialistOutput, SpecialistRole

class CommunicatingSpecialist(BaseSpecialist):
    """
    An abstract specialist that enhances the BaseSpecialist with the ability to
    communicate with other agents via a shared bus and database.

    This class implements a template method pattern for `execute_task`, handling
    context gathering, result sharing, and decision logging, while delegating the
    core inference logic to subclasses via the `run_inference_with_prompt` method.
    """

    def __init__(self, comm_bus: AgentCommunicationBus, db: AgentDatabase):
        super().__init__()
        self.comm_bus = comm_bus
        self.db = db
        self.project_context = {}
        self.received_artifacts = {}

        # The AgentCommunicationBus does not require explicit agent registration.
        # Agents participate by publishing to and draining messages from topics.

        # Subscribe to relevant artifact types
        self._setup_artifact_listeners()

    def execute_task(self, task: SpecialistTask) -> SpecialistOutput:
        """
        Orchestrates task execution using the Template Method Pattern.

        1. Gathers context from peers.
        2. Builds an enhanced prompt.
        3. Executes the core logic via the abstract `run_inference_with_prompt` method.
        4. Shares the resulting artifacts.
        5. Stores the decision for future learning.
        """
        # Get context from other agents before starting
        self._gather_context(task)

        # Process any incoming messages
        self._process_messages()

        # Create enhanced system prompt with context from other agents
        enhanced_prompt = self._get_enhanced_system_prompt(task)

        # Execute main task by calling the abstract method to be implemented by subclasses
        output = self.run_inference_with_prompt(task, enhanced_prompt)

        # Share results with other agents
        self._share_artifacts(task, output)

        # Store decision for learning
        self._store_decision(task, output)

        return output

    def _gather_context(self, task: SpecialistTask):
        """Gather relevant context from other agents"""
        project_id = task.context.get("project_id", "default")

        # Get recent artifacts from database
        related_artifacts = self.db.get_related_artifacts(
            self.capability.name.lower(),
            project_id
        )

        # Get relevant artifacts from communication bus
        bus_artifacts = self.comm_bus.get_shared_context()

        # Update task context with other agents' work
        for artifact in related_artifacts:
            context_key = f"{artifact.agent_type}.{artifact.artifact_type}"
            task.context[context_key] = artifact.content
            self.received_artifacts[context_key] = artifact

            print(f"📡 {self.capability.name} received {context_key} "
                  f"from {artifact.agent_type} (conf: {artifact.confidence:.2f})")

        for key, artifact in bus_artifacts.items():
            # key is already "agent.artifact_type"
            agent_type, _ = key.split('.', 1)
            task.context[key] = artifact['data']
            self.received_artifacts[key] = artifact

            print(f"📡 {self.capability.name} received {key} "
                  f"from {agent_type} via bus")

    def _process_messages(self):
        """Process incoming messages from other agents"""
        # This is a simplified version, as the bus implementation changed.
        # I'll drain all topics for now. A real implementation would be more specific.
        all_messages = []
        # This part is not well-defined in the user prompt with the new bus.
        # I will leave it empty for now and focus on artifact sharing.
        pass

    def _handle_message(self, message):
        """Handle a message from another agent"""
        print(f"💌 {self.capability.name} received message: {message.topic}")
        # Add logic to handle different message topics

    def run_inference_with_prompt(self, task: SpecialistTask, prompt: str) -> SpecialistOutput:
        """
        Abstract method for executing the core specialist logic.
        Subclasses MUST implement this method to perform their primary function,
        typically involving an LLM call with the provided enhanced prompt.
        """
        raise NotImplementedError("Subclasses must implement `run_inference_with_prompt`.")

    def _get_enhanced_system_prompt(self, task: SpecialistTask) -> str:
        """Create enhanced system prompt with context from other agents"""
        base_prompt = self.capability.system_prompt
        context_info = self._format_shared_context(task)

        return f"""{base_prompt}

**CONTEXT FROM OTHER SPECIALISTS:**
{context_info}

**COLLABORATION GUIDELINES:**
1. Build upon the work already done by other specialists
2. Reference their artifacts and maintain consistency across the system
3. If you need something from another specialist, send a message via the communication bus
4. When your work depends on another specialist's artifact, include that in your dependencies

**AVAILABLE ARTIFACTS:**
{self._list_available_artifacts()}

Please build upon the work already done by other specialists when possible.
Reference their artifacts and maintain consistency across the system.
"""

    def _format_shared_context(self, task: SpecialistTask) -> str:
        """Format shared context for inclusion in prompt"""
        context_parts = []

        for key, artifact in self.received_artifacts.items():
            # Key is consistently 'agent.artifact_type' now
            agent_type, artifact_type = key.split('.', 1)

            # Handle mixed types: Artifact objects from DB, dicts from bus
            if hasattr(artifact, 'content'): # It's an Artifact object
                artifact_data = artifact.content
            else: # It's a dict from the bus
                artifact_data = artifact.get('data', {})

            if artifact_type == "api_schema":
                content_preview = self._format_api_schema(artifact_data)
            elif artifact_type == "database_schema":
                content_preview = self._format_database_schema(artifact_data)
            elif artifact_type == "component_spec":
                content_preview = self._format_component_spec(artifact_data)
            else:
                content_preview = json.dumps(artifact_data, indent=2)[:500] + "..."

            context_parts.append(f"**{agent_type} - {artifact_type}:**\\n{content_preview}\\n")

        return "\\n".join(context_parts) if context_parts else "No artifacts from other specialists available."

    def _list_available_artifacts(self) -> str:
        """List all available artifacts for reference"""
        artifact_list = []

        for key, artifact in self.received_artifacts.items():
            agent_type, artifact_type = key.split('_', 1)
            artifact_list.append(f"- {agent_type}.{artifact_type}")

        return "\\n".join(artifact_list) if artifact_list else "No artifacts available."

    def _format_api_schema(self, schema: Dict) -> str:
        """Format API schema for display"""
        if not schema: return "No API schema available"
        endpoints = schema.get("endpoints", [])
        if not endpoints: return "No endpoints defined in API schema"
        preview = f"API with {len(endpoints)} endpoints:\\n"
        for endpoint in endpoints[:3]:
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "/")
            description = endpoint.get("description", "")
            preview += f"- {method} {path}: {description}\\n"
        if len(endpoints) > 3: preview += f"... and {len(endpoints) - 3} more endpoints"
        return preview

    def _format_database_schema(self, schema: Dict) -> str:
        """Format database schema for display"""
        if not schema: return "No database schema available"
        tables = schema.get("tables", [])
        if not tables: return "No tables defined in database schema"
        preview = f"Database with {len(tables)} tables:\\n"
        for table in tables[:3]:
            table_name = table.get("name", "unknown")
            columns = table.get("columns", [])
            preview += f"- {table_name} ({len(columns)} columns)\\n"
        if len(tables) > 3: preview += f"... and {len(tables) - 3} more tables"
        return preview

    def _format_component_spec(self, spec: Dict) -> str:
        """Format component specification for display"""
        if not spec: return "No component specification available"
        component_name = spec.get("name", "unknown")
        component_type = spec.get("type", "unknown")
        props = spec.get("props", {})
        preview = f"Component: {component_name} ({component_type})\\n"
        preview += f"Props: {len(props)} properties\\n"
        return preview

    def _share_artifacts(self, task: SpecialistTask, output: SpecialistOutput):
        """Share this agent's outputs with others"""
        project_id = task.context.get("project_id", "default")

        # Store in database for persistence. The store_artifact method is designed
        # to unpack the full SpecialistOutput object.
        self.db.store_artifact(project_id, output)

        # Broadcast to communication bus
        for artifact_type, content in output.output_artifacts.items():
            self.comm_bus.broadcast_artifact(
                agent_type=self.capability.name.lower(),
                artifact_type=artifact_type,
                data=content
            )

    def _store_decision(self, task: SpecialistTask, output: SpecialistOutput):
        """Store decision for learning"""
        context_str = json.dumps(task.context)
        decision_str = json.dumps(output.output_artifacts)
        outcome_str = "SUCCESS" if output.success else "FAILURE"

        # This method is not in the DB class the user provided.
        # The user DB has: `store_decision(self, agent_type: str, context: str, decision: str, outcome: str, confidence: float, metadata: Dict = None)`
        # I will call that one.
        self.db.store_decision(
            agent_type=self.capability.name.lower(),
            context=context_str,
            decision=decision_str,
            outcome=outcome_str,
            confidence=output.confidence,
            metadata={
                "task_id": task.task_id,
                "objective": task.objective
            }
        )

    def _setup_artifact_listeners(self):
        """Setup listeners for relevant artifact types"""
        pass

    def _send_update(self, to_agent: str):
        """Send status update to another agent"""
        self.comm_bus.publish(
            topic="agent.status",
            frm=self.capability.name.lower(),
            to=to_agent,
            payload={"status": "working"}
        )

    def _handle_dependency_alert(self, content: Dict):
        """Handle dependency alert from another agent"""
        dependency_type = content.get("dependency_type", "unknown")
        print(f"⚠️ {self.capability.name} alerted about dependency: {dependency_type}")
