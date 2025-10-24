"""
Quick Start Example - Multi-Agent Verification Loop

This demonstrates how to replace your MCP loop with the agent system.
"""

from orchestrator import MultiAgentOrchestrator
from config import SystemConfig, LMStudioConfig, AgentConfig
from datetime import datetime


def example_1_simple_usage():
    """
    Example 1: Simple usage with defaults
    Perfect for getting started quickly
    """
    
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Usage")
    print("="*80 + "\n")
    
    # Create orchestrator with defaults (uses mock LLM for testing)
    config = SystemConfig(use_mock_llm=True, use_mock_tests=True)
    orchestrator = MultiAgentOrchestrator(config)
    
    # Define your roadmap (what you want to accomplish)
    roadmap = [
        "Create user authentication module",
        "Add password hashing",
        "Implement login endpoint"
    ]
    
    # Run it!
    task_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    final_state = orchestrator.run_task(
        task_id=task_id,
        roadmap=roadmap,
        initial_context="Building a secure user authentication system"
    )
    
    print(f"\n✅ Completed {final_state.roadmap_position}/{final_state.total_roadmap_items} items")
    print(f"Total turns: {final_state.current_turn}")


def example_2_with_lm_studio():
    """
    Example 2: Using actual LM Studio
    For production use with real LLM
    """
    
    print("\n" + "="*80)
    print("EXAMPLE 2: With LM Studio")
    print("="*80 + "\n")
    
    # Configure for LM Studio (make sure it's running on localhost:1234)
    config = SystemConfig(
        use_mock_llm=False,  # Use real LM Studio
        use_mock_tests=True,  # But keep mock tests for demo
        llm=LMStudioConfig(
            base_url="http://localhost:1234/v1",
            model="local-model",
            temperature=0.7
        )
    )
    
    orchestrator = MultiAgentOrchestrator(config)
    
    roadmap = [
        "Set up FastAPI project structure",
        "Create database models with SQLAlchemy",
        "Implement CRUD operations for users"
    ]
    
    task_id = f"lmstudio_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    final_state = orchestrator.run_task(
        task_id=task_id,
        roadmap=roadmap,
        initial_context="Building a FastAPI backend with PostgreSQL"
    )
    
    print(f"\n✅ Done! Check the logs for details.")


def example_3_custom_integration():
    """
    Example 3: Custom integration with your app
    Shows how to hook into the resubmit mechanism
    """
    
    print("\n" + "="*80)
    print("EXAMPLE 3: Custom Integration")
    print("="*80 + "\n")
    
    from agents import SchedulerAgent, BatonPacket
    
    # Create a custom scheduler that integrates with your app
    class CustomScheduler(SchedulerAgent):
        
        def _resubmit_to_app(self, baton: BatonPacket):
            """
            THIS IS WHERE YOUR ORIGINAL LOOP HAPPENS!
            
            Original flow:
            1. LLM generates response
            2. Embed it
            3. Store in LanceDB
            4. Resubmit to your app
            
            All of that now happens automatically in the agent loop,
            and you just need to handle the "resubmit" part here.
            """
            
            print(f"\n📤 RESUBMITTING TO YOUR APP:")
            print(f"   Turn ID: {baton.turn_id}")
            print(f"   Summary: {baton.builder_summary}")
            print(f"   Files changed: {len(baton.files_changed)}")
            
            # YOUR CUSTOM INTEGRATION CODE HERE:
            # 
            # Option A: Post to your API
            # requests.post("http://your-app/api/update", json=baton.to_dict())
            #
            # Option B: Update UI state
            # your_ui_manager.update(baton.response_text)
            #
            # Option C: Trigger workflow
            # your_workflow.process_turn(baton)
            #
            # Option D: Store in your database
            # your_db.insert_turn(baton.to_dict())
            
            print(f"   ✓ Submitted to app successfully!\n")
    
    # Use your custom scheduler
    config = SystemConfig(use_mock_llm=True, use_mock_tests=True)
    orchestrator = MultiAgentOrchestrator(config)
    
    # Replace the scheduler with your custom one
    orchestrator.scheduler = CustomScheduler(
        builder=orchestrator.builder,
        verifier=orchestrator.verifier,
        db_manager=orchestrator.db_manager
    )
    
    roadmap = ["Implement feature A", "Add tests", "Deploy to staging"]
    
    task_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    orchestrator.run_task(task_id, roadmap)


def example_4_continuous_feedback():
    """
    Example 4: Continuous feedback loop (closest to your original MCP idea)
    
    This shows how the agent system maintains the same feedback pattern
    as your original: output → embed → store → resubmit → repeat
    """
    
    print("\n" + "="*80)
    print("EXAMPLE 4: Continuous Feedback Loop")
    print("="*80 + "\n")
    
    config = SystemConfig(use_mock_llm=True, use_mock_tests=True)
    orchestrator = MultiAgentOrchestrator(config)
    
    # Simulate a continuous improvement loop
    roadmap = [
        "Generate initial solution",
        "Analyze solution quality",
        "Refine based on analysis",
        "Optimize performance",
        "Add error handling",
        "Final polish"
    ]
    
    # Each of these will:
    # 1. Builder generates code
    # 2. Response gets embedded and stored in LanceDB
    # 3. Verifier checks quality
    # 4. If good: move forward (and resubmit to app)
    # 5. If bad: builder tries again with feedback
    # 6. Repeat until roadmap complete
    
    task_id = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    final_state = orchestrator.run_task(
        task_id=task_id,
        roadmap=roadmap,
        initial_context="Building a data processing pipeline"
    )
    
    print(f"\n📊 FEEDBACK LOOP STATS:")
    print(f"   Total iterations: {final_state.current_turn}")
    print(f"   Successful turns: {len([h for h in final_state.agent_history if h.get('agent') == 'verifier' and h.get('status') == 'passed'])}")
    print(f"   Checkpoints saved: {len(final_state.checkpoints)}")
    print(f"   All work embedded in LanceDB for future retrieval!")


def example_5_long_horizon():
    """
    Example 5: Long-horizon task (200+ minutes like in the video)
    
    This demonstrates the core benefit: maintaining coherence over many turns
    """
    
    print("\n" + "="*80)
    print("EXAMPLE 5: Long-Horizon Task (Multi-Hour)")
    print("="*80 + "\n")
    
    # Configure for longer runs
    config = SystemConfig(
        use_mock_llm=True,
        use_mock_tests=True,
        agent=AgentConfig(
            builder_max_duration_minutes=20,  # 20 min sprints
            verifier_max_duration_minutes=10,  # 10 min verification
            max_retries=3,  # Allow more retries
            token_budget=200000  # Higher budget for long tasks
        )
    )
    
    orchestrator = MultiAgentOrchestrator(config)
    
    # A complex, multi-hour roadmap
    roadmap = [
        "Research and design system architecture",
        "Implement core data models",
        "Build API layer with authentication",
        "Create frontend components",
        "Integrate frontend with backend",
        "Implement caching layer",
        "Add comprehensive error handling",
        "Write unit tests for all modules",
        "Create integration tests",
        "Performance optimization",
        "Security audit and fixes",
        "Documentation",
        "Deployment scripts",
        "Monitoring and logging",
        "Final QA and polish"
    ]
    
    # With 15 items * ~30 min per cycle = ~7.5 hours of coherent work!
    
    task_id = f"long_horizon_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Starting long-horizon task with {len(roadmap)} items...")
    print("This would run for several hours with a real LLM.")
    print("The verification loop ensures coherence throughout!\n")
    
    final_state = orchestrator.run_task(
        task_id=task_id,
        roadmap=roadmap,
        initial_context="Building a complete full-stack application from scratch"
    )
    
    print(f"\n🎉 LONG-HORIZON TASK COMPLETE!")
    print(f"   Completed {final_state.roadmap_position} major milestones")
    print(f"   Total agent turns: {final_state.current_turn}")
    print(f"   Quality checkpoints: {len(final_state.checkpoints)}")
    print(f"   Every step verified and stored in vector DB!")


def main():
    """Run all examples"""
    
    print("\n" + "🤖 " * 20)
    print("MULTI-AGENT VERIFICATION LOOP - QUICK START EXAMPLES")
    print("🤖 " * 20)
    
    examples = [
        ("Simple Usage (5 sec)", example_1_simple_usage),
        ("With LM Studio (requires LM Studio running)", example_2_with_lm_studio),
        ("Custom Integration", example_3_custom_integration),
        ("Continuous Feedback Loop", example_4_continuous_feedback),
        ("Long-Horizon Task", example_5_long_horizon)
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    choice = input("\nRun which example? (1-5, or 'all'): ").strip()
    
    if choice.lower() == 'all':
        for name, func in examples:
            print(f"\n{'='*80}")
            print(f"Running: {name}")
            print('='*80)
            try:
                func()
            except Exception as e:
                print(f"❌ Error: {e}")
    
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        name, func = examples[int(choice) - 1]
        print(f"\nRunning: {name}\n")
        func()
    
    else:
        print("Invalid choice. Running Example 1...")
        example_1_simple_usage()


if __name__ == "__main__":
    main()
