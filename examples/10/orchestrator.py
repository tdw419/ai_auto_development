"""
Main Orchestrator for Multi-Agent Verification Loop System
This is the entry point that brings all components together
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

try:
    from .path_shim import get_current_utc_time, to_iso_format
except ImportError:  # pragma: no cover - direct execution fallback
    sys.path.insert(0, str(Path(__file__).parent))
    from path_shim import get_current_utc_time, to_iso_format

from agents import BuilderAgent, VerifierAgent, SchedulerAgent, TaskState
from db_manager import LanceDBManager
from llm_client import LMStudioClient, Embedder, MockLLMClient, MockEmbedder
from test_runner import TestRunner, MockTestRunner
from config import SystemConfig, get_default_config


def setup_logging(config: SystemConfig):
    """Configure logging"""
    
    log_level = getattr(logging, config.log_level.upper())
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if config.log_file:
        log_dir = Path(config.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.log_file))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )


class MultiAgentOrchestrator:
    """
    Main orchestrator that coordinates Builder, Verifier, and Scheduler
    This replaces your original MCP loop with agent-based coordination
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize the multi-agent system
        
        Args:
            config: System configuration (uses defaults if None)
        """
        
        self.config = config or get_default_config()
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Initializing Multi-Agent Verification Loop System...")
        
        # Initialize components
        self.db_manager = self._init_database()
        self.llm_client = self._init_llm()
        self.embedder = self._init_embedder()
        self.test_runner = self._init_test_runner()
        
        # Initialize agents
        self.builder = BuilderAgent(
            llm_client=self.llm_client,
            embedder=self.embedder,
            db_manager=self.db_manager,
            max_duration_minutes=self.config.agent.builder_max_duration_minutes
        )
        
        self.verifier = VerifierAgent(
            llm_client=self.llm_client,
            embedder=self.embedder,
            db_manager=self.db_manager,
            test_runner=self.test_runner,
            max_duration_minutes=self.config.agent.verifier_max_duration_minutes
        )
        
        self.scheduler = SchedulerAgent(
            builder=self.builder,
            verifier=self.verifier,
            db_manager=self.db_manager
        )
        
        self.logger.info("✓ Multi-Agent System initialized successfully")
    
    def _init_database(self) -> LanceDBManager:
        """Initialize LanceDB"""
        self.logger.info(f"Initializing LanceDB at {self.config.database.db_path}")
        return LanceDBManager(db_path=self.config.database.db_path)
    
    def _init_llm(self):
        """Initialize LLM client"""
        if self.config.use_mock_llm:
            self.logger.info("Using Mock LLM (testing mode)")
            return MockLLMClient()
        
        self.logger.info(f"Connecting to LM Studio at {self.config.llm.base_url}")
        client = LMStudioClient(
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            timeout=self.config.llm.timeout
        )
        
        # Test connection
        if client.check_connection():
            self.logger.info("✓ Connected to LM Studio")
        else:
            self.logger.warning("⚠ Could not connect to LM Studio - check if server is running")
        
        return client
    
    def _init_embedder(self):
        """Initialize embedding model"""
        if self.config.use_mock_llm:
            self.logger.info("Using Mock Embedder (testing mode)")
            return MockEmbedder(embedding_dim=self.config.embedder.embedding_dim)
        
        self.logger.info(f"Initializing embedder: {self.config.embedder.model_name}")
        return Embedder(
            model_name=self.config.embedder.model_name,
            base_url=self.config.embedder.base_url,
            embedding_dim=self.config.embedder.embedding_dim
        )
    
    def _init_test_runner(self):
        """Initialize test runner"""
        if self.config.use_mock_tests:
            self.logger.info("Using Mock Test Runner (testing mode)")
            return MockTestRunner(self.config.repo_path)
        
        self.logger.info(f"Initializing test runner for {self.config.repo_path}")
        return TestRunner(self.config.repo_path)
    
    def run_task(
        self,
        task_id: str,
        roadmap: List[str],
        initial_context: Optional[str] = None
    ) -> TaskState:
        """
        Execute a complete task using the multi-agent relay system
        
        This is your new main loop that replaces the MCP approach.
        Each roadmap item triggers a Builder -> Verifier cycle.
        
        Args:
            task_id: Unique identifier for this task
            roadmap: List of subtasks to complete sequentially
            initial_context: Optional starting context
            
        Returns:
            Final TaskState with complete history
        """
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"STARTING TASK: {task_id}")
        self.logger.info(f"Roadmap items: {len(roadmap)}")
        self.logger.info(f"{'='*80}\n")
        
        # Initialize task state
        task_state = TaskState(
            task_id=task_id,
            current_turn=0,
            agent_history=[],
            roadmap_position=0,
            total_roadmap_items=len(roadmap),
            open_issues=[],
            resolved_issues=[],
            checkpoints=[],
            token_usage=0
        )
        
        # Store initial context if provided
        if initial_context:
            self.logger.info("Storing initial context...")
            embedding = self.embedder.embed(initial_context)
            self.db_manager.store_turn(
                turn_id=f"{task_id}_context",
                agent_role="system",
                content=initial_context,
                embedding=embedding,
                metadata={
                    'task_id': task_id,
                    'turn_number': -1,
                    'status': 'context',
                    'timestamp': to_iso_format(get_current_utc_time())
                }
            )
        
        # Run the scheduler (this executes the full relay race)
        final_state = self.scheduler.run_task(
            task_state=task_state,
            roadmap=roadmap,
            repo_path=self.config.repo_path
        )
        
        # Log summary
        self._log_task_summary(final_state)
        
        return final_state
    
    def continue_from_checkpoint(self, task_id: str, checkpoint_turn: int) -> TaskState:
        """
        Resume a task from a previous checkpoint
        
        Args:
            task_id: Task to resume
            checkpoint_turn: Turn number to resume from
            
        Returns:
            Resumed task state
        """
        
        self.logger.info(f"Resuming task {task_id} from turn {checkpoint_turn}")
        
        # Load task history from DB
        # This is a placeholder - you'd implement full state reconstruction
        
        raise NotImplementedError("Checkpoint resume not yet implemented")
    
    def _log_task_summary(self, task_state: TaskState):
        """Log task completion summary"""
        
        summary = self.db_manager.get_task_summary(task_state.task_id)
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info("TASK SUMMARY")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Task ID: {summary['task_id']}")
        self.logger.info(f"Total Turns: {summary['total_turns']}")
        self.logger.info(f"Passed Turns: {summary['passed_turns']}")
        self.logger.info(f"Failed Turns: {summary['failed_turns']}")
        self.logger.info(f"Builder Turns: {summary['builder_turns']}")
        self.logger.info(f"Verifier Turns: {summary['verifier_turns']}")
        self.logger.info(f"Roadmap Progress: {task_state.roadmap_position}/{task_state.total_roadmap_items}")
        self.logger.info(f"Open Issues: {len(task_state.open_issues)}")
        self.logger.info(f"Checkpoints: {len(task_state.checkpoints)}")
        self.logger.info(f"Token Usage: {task_state.token_usage}")
        self.logger.info(f"{'='*80}\n")


def create_sample_roadmap() -> List[str]:
    """
    Create a sample roadmap for testing
    Replace this with your actual task breakdown
    """
    return [
        "Set up project structure with proper directories and configuration files",
        "Implement core data validation logic with error handling",
        "Create unit tests for validation functions",
        "Add API endpoint for data submission",
        "Implement authentication middleware",
        "Write integration tests for API endpoints",
        "Add logging and monitoring instrumentation",
        "Create documentation for API usage"
    ]


def main():
    """
    Example usage of the multi-agent system
    """
    
    # Option 1: Use default configuration
    orchestrator = MultiAgentOrchestrator()
    
    # Option 2: Load from config file (if you create config.json)
    # from config import load_config_from_file
    # config = load_config_from_file("config.json")
    # orchestrator = MultiAgentOrchestrator(config)
    
    # Define your roadmap (list of tasks to complete)
    roadmap = create_sample_roadmap()
    
    # Run the task
    task_id = f"task_{utc_now().strftime('%Y%m%d_%H%M%S')}"
    
    initial_context = """
    This is a Python project for building a data validation API.
    We need to follow PEP 8 style guidelines and maintain >90% test coverage.
    The API should be RESTful and use FastAPI framework.
    """
    
    final_state = orchestrator.run_task(
        task_id=task_id,
        roadmap=roadmap,
        initial_context=initial_context
    )
    
    # At this point, your agents have worked through the entire roadmap
    # Each turn has been:
    # 1. Built by the Builder agent
    # 2. Embedded and stored in LanceDB
    # 3. Verified by the Verifier agent
    # 4. Fed back into your app (via scheduler's _resubmit_to_app method)
    
    print("\n✅ Task completed!")
    print(f"Completed {final_state.roadmap_position} of {final_state.total_roadmap_items} roadmap items")
    print(f"Total turns: {final_state.current_turn}")
    print(f"Open issues: {len(final_state.open_issues)}")
    
    # YOUR ORIGINAL LOOP INTEGRATION:
    # The scheduler's _resubmit_to_app method is where you'd integrate
    # your "LLM output → embed → resubmit to app" pattern.
    # Every successful turn gets fed back to your application automatically!


if __name__ == "__main__":
    main()
