from vista_specialists.agents.specialists.communicating_specialist import CommunicatingSpecialist
from vista_specialists.agents.base import SpecialistRole, SpecialistTask, SpecialistOutput, SpecialistCapability

class CommunicatingAPIArchitect(CommunicatingSpecialist):
    """API Architect with communication capabilities"""

    def define_capability(self) -> SpecialistCapability:
        """Defines the specific capability of the API Architect."""
        return SpecialistCapability(
            name="API Architect",
            system_prompt="""
You are an expert API Architect. Your role is to design robust, scalable, and secure API endpoints
based on the provided database schema and project requirements. You must produce clear, well-documented
API specifications.
""",
            capabilities=["api_schema", "openapi_spec"]
        )

    def _setup_artifact_listeners(self):
        """Listen for database schema changes"""
        # The `subscribe_to_artifacts` method was not in the user-provided bus implementation.
        # I will comment this out for now.
        # self.comm_bus.subscribe_to_artifacts(
        #     self.capability.name.lower(),
        #     self._on_database_schema_update
        # )
        pass

    def _on_database_schema_update(self, artifact):
        """Handle database schema updates"""
        if artifact.artifact_type == "database_schema":
            print(f"🔔 API Architect notified of database schema update")
            # Could trigger automatic API endpoint updates here

    def _get_enhanced_system_prompt(self, task: SpecialistTask) -> str:
        """Create enhanced system prompt with database schema context"""
        base_prompt = super()._get_enhanced_system_prompt(task)

        # Add specific API architect context
        api_context = """
**API ARCHITECT GUIDELINES:**
1. Design RESTful endpoints that match the database schema
2. Use consistent naming conventions with database tables
3. Include proper error handling and validation
4. Document all endpoints with OpenAPI/Swagger specifications
5. Consider authentication and authorization requirements
"""

        return base_prompt + api_context
