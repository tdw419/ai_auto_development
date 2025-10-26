from vista_specialists.agents.specialists.communicating_specialist import CommunicatingSpecialist
from vista_specialists.agents.base import SpecialistRole, SpecialistTask, SpecialistOutput, SpecialistCapability

class CommunicatingDataEngineer(CommunicatingSpecialist):
    """Data Engineer with communication capabilities"""

    def define_capability(self) -> SpecialistCapability:
        """Defines the specific capability of the Data Engineer."""
        return SpecialistCapability(
            name="Data Engineer",
            system_prompt="""
You are a meticulous Data Engineer. Your primary responsibility is to design and create efficient,
normalized database schemas. You must ensure data integrity, define clear relationships between
entities, and consider future scalability.
""",
            capabilities=["database_schema", "sql_migrations"]
        )

    def _get_enhanced_system_prompt(self, task: SpecialistTask) -> str:
        """Create enhanced system prompt with project context"""
        base_prompt = super()._get_enhanced_system_prompt(task)

        # Add specific data engineering context
        data_context = """
**DATA ENGINEER GUIDELINES:**
1. Design normalized database schemas
2. Include proper indexes for performance
3. Define relationships between tables
4. Consider data validation and constraints
5. Plan for scalability and future requirements
"""

        return base_prompt + data_context
