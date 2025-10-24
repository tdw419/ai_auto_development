# Multi-Agent Verification Loop System

A production-ready implementation of the "agent prompting the next agent" pattern for achieving long-horizon coherence in AI systems. Based on the verification loop concept that enables 200+ minute runtimes with maintained quality.

## 🎯 Core Concept

Replace your MCP (Model Context Protocol) tool chain with a **relay race** of specialized agents:

```
User Input
    ↓
┌─────────────────────────────────────────┐
│  Builder Agent (15-20 min sprint)      │
│  • Takes task + context from LanceDB    │
│  • Generates solution via LM Studio     │
│  • Embeds & stores output               │
│  • Produces baton packet                │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Verifier Agent (5-10 min check)       │
│  • Runs tests & linting                 │
│  • LLM coherence check                  │
│  • Creates defect capsule if issues     │
└──────────────┬──────────────────────────┘
               ↓
        ┌──────┴──────┐
        │  Scheduler   │
        └──────┬───────┘
               ↓
    ┌──────────┴────────────┐
    │                       │
✅ Pass                  ❌ Fail
    │                       │
    ↓                       ↓
Resubmit to App      Retry with Feedback
Move to Next         (Builder + Defect Capsule)
```

## 🚀 Quick Start

### 1. Installation

```bash
pip install lancedb requests numpy
```

### 1b. Legacy timezone utilities (optional)

```bash
cd examples/10
python install_utils.py
```

This installs the shared `utils.time_utils` helpers so legacy scripts can locate them without manual `PYTHONPATH` tweaks. Alternatively, rely on the built-in path shim and run the scripts directly.

### 2. Start LM Studio

Make sure LM Studio is running on `http://localhost:1234` with your preferred model loaded.

### 3. Run Your First Task

```python
from orchestrator import MultiAgentOrchestrator
from datetime import datetime

# Initialize with defaults
orchestrator = MultiAgentOrchestrator()

# Define what you want to accomplish
roadmap = [
    "Create database schema",
    "Build API endpoints",
    "Add authentication",
    "Write tests"
]

# Run it!
task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
final_state = orchestrator.run_task(
    task_id=task_id,
    roadmap=roadmap,
    initial_context="Building a REST API with FastAPI"
)

print(f"✅ Completed {final_state.roadmap_position}/{final_state.total_roadmap_items} items!")
```

### 4. Legacy CLI smoke test

```bash
cd examples/10
python cli.py
```

This uses the timezone-aware path shim and prints ISO 8601 timestamps even when launched outside the repository root.

## 📁 Project Structure

```
.
├── agents.py           # Builder, Verifier, Scheduler agents
├── db_manager.py       # LanceDB integration for embeddings
├── llm_client.py       # LM Studio API wrapper + Embedder
├── test_runner.py      # Test execution (pytest, jest, etc)
├── config.py           # Configuration management
├── orchestrator.py     # Main entry point
├── examples.py         # Usage examples
└── README.md          # This file
```

## 🔧 How It Works

### Your Original MCP Loop

```
LLM input → Embedding → LanceDB → LM Studio response → 
Save & embed → Resubmit to app → Repeat
```

### New Agent-Based Flow

```
User input + LanceDB context → Builder (LM Studio) → 
Embed & store → Verifier (tests + LLM check) → 
Scheduler decision → Resubmit to app → Next iteration
```

**Key difference:** Quality gates between iterations prevent drift!

## 📊 Agent Roles

### Builder Agent

**Duration:** 15-20 minutes  
**Responsibility:** Generate solutions

- Retrieves relevant context from LanceDB (RAG)
- Constructs prompt with task + history + defects
- Calls LM Studio for solution
- Embeds and stores output
- Packages result into baton

### Verifier Agent

**Duration:** 5-10 minutes  
**Responsibility:** Validate quality

- Runs test suite (pytest/jest/unittest)
- Executes linting (pylint/eslint)
- LLM-based coherence check
- Creates defect capsule on failure
- Signs checkpoint on success

### Scheduler Agent

**Responsibility:** Orchestrate the relay

- Manages task queue and state
- Decides: continue, retry, or escalate
- Maintains compressed history
- Handles token budgets
- Resubmits to your app

## 🎛️ Configuration

### Basic Config

```python
from config import SystemConfig, LMStudioConfig, AgentConfig

config = SystemConfig(
    llm=LMStudioConfig(
        base_url="http://localhost:1234/v1",
        model="local-model",
        temperature=0.7
    ),
    agent=AgentConfig(
        builder_max_duration_minutes=20,
        verifier_max_duration_minutes=10,
        max_retries=2
    ),
    repo_path="./my-project"
)

orchestrator = MultiAgentOrchestrator(config)
```

### From Config File

```json
{
  "llm": {
    "base_url": "http://localhost:1234/v1",
    "model": "local-model",
    "temperature": 0.7
  },
  "agent": {
    "builder_max_duration_minutes": 20,
    "max_retries": 2,
    "token_budget": 100000
  },
  "database": {
    "db_path": "./data/lancedb"
  },
  "repo_path": "./my-project"
}
```

```python
from config import load_config_from_file

config = load_config_from_file("config.json")
orchestrator = MultiAgentOrchestrator(config)
```

## 🔄 Integrating With Your App

The key integration point is the `_resubmit_to_app` method in the Scheduler:

```python
from agents import SchedulerAgent, BatonPacket

class CustomScheduler(SchedulerAgent):
    def _resubmit_to_app(self, baton: BatonPacket):
        """
        YOUR ORIGINAL FEEDBACK LOOP GOES HERE
        
        The baton contains:
        - response_text: LLM's output
        - builder_summary: Compressed version
        - files_changed: Modified files
        - metadata: Additional context
        """
        
        # Option 1: HTTP API
        requests.post("http://your-app/api/process", 
                     json=baton.to_dict())
        
        # Option 2: Database
        your_db.insert({
            'turn_id': baton.turn_id,
            'content': baton.response_text,
            'timestamp': baton.timestamp
        })
        
        # Option 3: Message queue
        your_queue.publish('agent-output', baton.to_dict())
        
        # Option 4: Direct function call
        your_app_handler.process_turn(baton)
```

## ✅ Legacy Timezone Tests

Run the targeted regression suite to confirm the shim and timestamps:

```bash
cd examples/10
python test_legacy_timezone.py
```

Then use your custom scheduler:

```python
orchestrator = MultiAgentOrchestrator(config)
orchestrator.scheduler = CustomScheduler(
    builder=orchestrator.builder,
    verifier=orchestrator.verifier,
    db_manager=orchestrator.db_manager
)
```

## 🎓 Examples

See `examples.py` for complete examples:

```bash
python examples.py
```

### Example 1: Simple Usage
Basic demonstration with mock LLM (no LM Studio required)

### Example 2: With LM Studio
Real LLM integration for production use

### Example 3: Custom Integration
Shows how to hook into your existing app

### Example 4: Continuous Feedback
Replicates your original MCP loop pattern

### Example 5: Long-Horizon Task
Multi-hour coherent execution (200+ minutes)

## 🗄️ Database Schema

LanceDB stores four tables:

### `agent_turns`
- Every builder/verifier iteration
- Full content + embedding
- Status tracking
- Metadata

### `checkpoints`
- Successful milestones
- Commit hashes
- Verified states

### `defects`
- Bug reports
- Similar defect retrieval
- Resolution tracking

### `escalations`
- Human intervention requests
- Persistent failures
- Context trails

## 🧪 Testing

Run with mock components (no LM Studio needed):

```python
config = SystemConfig(
    use_mock_llm=True,
    use_mock_tests=True
)
orchestrator = MultiAgentOrchestrator(config)
```

## 🎯 Benefits Over MCP Loop

| Feature | MCP Loop | Agent Loop |
|---------|----------|------------|
| Quality gates | ❌ None | ✅ Verifier between iterations |
| Coherence | ~5 min before drift | 200+ min verified |
| Error recovery | Manual | Automatic retry with feedback |
| Context management | Token window limit | Compressed + embedded history |
| Scalability | Single chain | Parallel agents possible |
| Debugging | Opaque | Full turn history in DB |

## 🔍 Monitoring

Each task generates detailed logs and DB records:

```python
# Get task summary
summary = orchestrator.db_manager.get_task_summary(task_id)

print(f"Total turns: {summary['total_turns']}")
print(f"Passed: {summary['passed_turns']}")
print(f"Failed: {summary['failed_turns']}")

# Retrieve specific turn
turns = orchestrator.db_manager.retrieve_relevant_context(
    query="authentication implementation",
    n_results=5
)
```

## ⚙️ Advanced Features

### Checkpoint Resume

```python
# Resume from previous checkpoint
final_state = orchestrator.continue_from_checkpoint(
    task_id="task_20250101_120000",
    checkpoint_turn=5
)
```

### Custom Verifier Logic

```python
from agents import VerifierAgent

class CustomVerifier(VerifierAgent):
    def _run_domain_probes(self, baton):
        # Add your custom validation
        if 'security' in baton.response_text.lower():
            # Run security scan
            pass
        return []
```

### Multi-Model Support

```python
# Different models for different agents
builder_llm = LMStudioClient(model="codellama-34b")
verifier_llm = LMStudioClient(model="mistral-7b")

builder = BuilderAgent(llm_client=builder_llm, ...)
verifier = VerifierAgent(llm_client=verifier_llm, ...)
```

## 🐛 Troubleshooting

### "Could not connect to LM Studio"
- Ensure LM Studio is running on localhost:1234
- Check that a model is loaded
- Try `use_mock_llm=True` for testing

### "Tests timed out"
- Increase `builder_max_duration_minutes`
- Check test suite runs independently
- Use `use_mock_tests=True` for testing

### "Token budget exceeded"
- Increase `agent.token_budget` in config
- History auto-compresses but adjust if needed
- Consider splitting into smaller tasks

### Verifier always fails
- Check test suite is working
- Review defect capsules in logs
- Adjust `max_retries` higher

## 📚 References

This implementation is based on the "verification loop" concept discussed in [the video reference at 01:50:00 - 02:05:00] for achieving long-horizon coherence through multi-agent relay systems.

## 🤝 Contributing

This is a reference implementation. Key areas for extension:

- [ ] Parallel agent execution
- [ ] Human-in-the-loop UI
- [ ] Multi-modal support
- [ ] Distributed agent coordination
- [ ] Enhanced compression strategies

## 📄 License

[Your license here]

## 🎉 Next Steps

1. Run `python examples.py` to see it in action
2. Configure for your LM Studio setup
3. Customize the `_resubmit_to_app` method
4. Define your roadmap
5. Scale to multi-hour tasks!

**The key insight:** By adding verification between iterations and compressing history, you maintain coherence over hundreds of minutes instead of just a few. This is the core innovation that enables truly autonomous long-running AI agents.
