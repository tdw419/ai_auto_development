from vista_specialists.agents.specialists.communicating_specialist import CommunicatingSpecialist
from vista_specialists.agents.base import SpecialistRole, SpecialistTask, SpecialistOutput, SpecialistCapability

class CommunicatingFrontendArtist(CommunicatingSpecialist):
    """Frontend Artist with communication capabilities"""

    def define_capability(self) -> SpecialistCapability:
        """Defines the specific capability of the Frontend Artist."""
        return SpecialistCapability(
            name="Frontend Artist",
            system_prompt="""
You are a creative Frontend Artist. You specialize in building beautiful, responsive, and intuitive
user interfaces based on API specifications and component designs. Your work must be both aesthetically
pleasing and highly functional.
""",
            capabilities=["ui_component", "stylesheet"]
        )

    def _setup_artifact_listeners(self):
        """Listen for API schema and component updates"""
        # The `subscribe_to_artifacts` method was not in the user-provided bus implementation.
        # I will comment this out for now.
        # self.comm_bus.subscribe_to_artifacts(
        #     self.capability.name.lower(),
        #     self._on_api_schema_update
        # )
        pass

    def _on_api_schema_update(self, artifact):
        """Handle API schema updates"""
        if artifact.artifact_type == "api_schema":
            print(f"🔔 Frontend Artist notified of API schema update")
            # Could trigger automatic component updates here

    def _get_enhanced_system_prompt(self, task: SpecialistTask) -> str:
        """Create enhanced system prompt with API context"""
        base_prompt = super()._get_enhanced_system_prompt(task)

        # Add specific frontend context
        frontend_context = """
**FRONTEND ARTIST GUIDELINES:**
1. Create components that match the API endpoints
2. Use consistent naming with API resources
3. Include proper error handling and loading states
4. Design responsive and accessible UI components
5. Consider user experience and interaction patterns
"""

        return base_prompt + frontend_context
