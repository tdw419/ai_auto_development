# Quick Reference Guide

## Installation (30 seconds)

```bash
# 1. Clone/download the files
# 2. Install dependencies
pip install lancedb requests numpy

# 3. Run setup (optional)
python setup.py

# 4. Try it out!
python examples.py
```

## Minimal Working Example

```python
from orchestrator import MultiAgentOrchestrator

# Initialize (uses mock LLM for instant testing)
orchestrator = MultiAgentOrchestrator()

# Define tasks
roadmap = ["Task 1", "Task 2", "Task 3"]

# Run!
final_state = orchestrator.run_task(
    task_id="my_first_task",
    roadmap=roadmap
)
```

## With LM Studio

```python
from config import SystemConfig, LMStudioConfig

config = SystemConfig(
    use_mock_llm=False,
    llm=LMStudioConfig(
        base_url="http://localhost:1234/v1",
        model="your-model-name"
    )
)

orchestrator = MultiAgentOrchestrator(config)
```

## Custom Integration

```python
from agents import SchedulerAgent, BatonPacket

class MyScheduler(SchedulerAgent):
    def _resubmit_to_app(self, baton: BatonPacket):
        # YOUR INTEGRATION HERE
        my_app.process(baton.response_text)

orchestrator = MultiAgentOrchestrator()
orchestrator.scheduler = MyScheduler(
    builder=orchestrator.builder,
    verifier=orchestrator.verifier,
    db_manager=orchestrator.db_manager
)
```

## Common Patterns

### Pattern 1: Sequential Tasks
```python
roadmap = [
    "Step 1: Setup",
    "Step 2: Implementation", 
    "Step 3: Testing"
]
orchestrator.run_task("sequential", roadmap)
```

### Pattern 2: Iterative Refinement
```python
roadmap = [
    "Initial implementation",
    "Optimize performance",
    "Add error handling",
    "Final polish"
]
orchestrator.run_task("iterative", roadmap)
```

### Pattern 3: Long-Horizon Project
```python
roadmap = [
    "Research and design",
    "Core implementation",
    "Feature set 1",
    "Feature set 2",
    # ... 10+ more items
    "Final integration",
    "Documentation"
]
orchestrator.run_task("long_horizon", roadmap)
```

## Configuration Cheat Sheet

```python
SystemConfig(
    # LLM settings
    llm=LMStudioConfig(
        base_url="http://localhost:1234/v1",
        model="local-model",
        temperature=0.7,      # Creativity (0-1)
        max_tokens=4000       # Response length
    ),
    
    # Agent behavior
    agent=AgentConfig(
        builder_max_duration_minutes=20,  # Sprint length
        verifier_max_duration_minutes=10, # Check time
        max_retries=2,                    # Before escalate
        token_budget=100000               # Total budget
    ),
    
    # Testing
    use_mock_llm=True,   # For fast testing
    use_mock_tests=True  # Skip real tests
)
```

## Debugging

### Check what happened in a task
```python
summary = orchestrator.db_manager.get_task_summary("task_id")
print(summary)
```

### Retrieve specific turn
```python
context = orchestrator.db_manager.retrieve_relevant_context(
    query="authentication implementation",
    n_results=5
)
```

### View recent history
```python
from agents import TaskState
print(task_state.agent_history[-5:])  # Last 5 turns
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Can't connect to LM Studio" | Start LM Studio or use `use_mock_llm=True` |
| "Tests timeout" | Increase `builder_max_duration_minutes` |
| "Token budget exceeded" | Increase `token_budget` in config |
| Verifier always fails | Check `max_retries` and review logs |

## File Structure

```
your-project/
├── agents.py              # Core agent classes
├── db_manager.py          # LanceDB integration  
├── llm_client.py          # LM Studio wrapper
├── test_runner.py         # Test execution
├── config.py              # Configuration
├── orchestrator.py        # Main entry point
├── examples.py            # Usage examples
├── setup.py               # Setup script
├── requirements.txt       # Dependencies
├── README.md              # Full documentation
├── ARCHITECTURE.md        # System design
├── QUICKSTART.md          # This file
├── config.example.json    # Example config
└── data/
    └── lancedb/           # Vector database
```

## API Reference

### MultiAgentOrchestrator

```python
orchestrator = MultiAgentOrchestrator(config=None)

# Main method
final_state = orchestrator.run_task(
    task_id: str,              # Unique identifier
    roadmap: List[str],        # List of tasks
    initial_context: str = None  # Optional context
)
```

### BatonPacket (passed between agents)

```python
baton.turn_id           # Unique turn ID
baton.response_text     # Full LLM response
baton.builder_summary   # Compressed version
baton.files_changed     # List of files
baton.verification_hints  # What to check
baton.metadata          # Additional data
```

### TaskState (persistent state)

```python
state.task_id           # Task identifier
state.current_turn      # Current turn number
state.roadmap_position  # Progress in roadmap
state.agent_history     # Full history
state.checkpoints       # Successful milestones
state.open_issues       # Unresolved problems
state.token_usage       # Tokens used
```

## Environment Variables (optional)

```bash
export LM_STUDIO_URL="http://localhost:1234/v1"
export LM_STUDIO_MODEL="local-model"
export LANCE_DB_PATH="./data/lancedb"
```

## Best Practices

1. **Start Small:** Test with 2-3 roadmap items first
2. **Use Mocks:** Develop/test with `use_mock_llm=True`
3. **Monitor Tokens:** Watch `token_usage` in TaskState
4. **Checkpoint Often:** Successful turns auto-checkpoint
5. **Review Defects:** Check escalations for patterns
6. **Compress History:** Happens automatically, but adjust if needed
7. **Custom Verification:** Add domain checks in Verifier
8. **Integrate Early:** Hook `_resubmit_to_app` early

## Performance Tips

- **Parallel Builds:** Multiple builders → single verifier (future)
- **Cache Embeddings:** Reuse for similar content
- **Batch Context:** Retrieve context once per sprint
- **Prune History:** Use `cleanup_old_data()` regularly
- **Stream LLM:** Set `stream=True` for faster feedback

## Common Use Cases

### 1. Code Generation
```python
roadmap = [
    f"Implement {feature}" for feature in features
]
```

### 2. Documentation
```python
roadmap = [
    "Generate API docs",
    "Write user guide",
    "Create examples"
]
```

### 3. Data Processing
```python
roadmap = [
    "Validate data",
    "Transform data",
    "Generate report"
]
```

### 4. Testing
```python
roadmap = [
    "Generate unit tests",
    "Generate integration tests",
    "Generate edge case tests"
]
```

## Next Steps

1. ✅ Run `python examples.py` 
2. ✅ Configure for your LM Studio
3. ✅ Customize `_resubmit_to_app`
4. ✅ Define your roadmap
5. ✅ Scale to multi-hour tasks!

## Support

- Read full docs: `README.md`
- Study architecture: `ARCHITECTURE.md`
- Check examples: `examples.py`
- Review code: Comments throughout

## Key Insight

The breakthrough is **verification between iterations**. By adding quality gates and compressing history, you maintain coherence for 200+ minutes instead of just 5.

This is the core innovation that makes truly autonomous long-running agents possible. 🚀
