# System Architecture Visualization

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER / APPLICATION                          │
│  "Build me a REST API with authentication and database"         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
                    ┌────────────────┐
                    │  Orchestrator  │
                    │  - Parse task  │
                    │  - Init agents │
                    └────────┬───────┘
                             │
                             ↓
┌────────────────────────────────────────────────────────────────┐
│                       ROADMAP                                   │
│  1. Set up project structure                                   │
│  2. Create database models                                     │
│  3. Implement API endpoints                                    │
│  4. Add authentication                                         │
│  5. Write tests                                                │
└────────────────────────────────────────────────────────────────┘
                             │
                             ↓
                    ┌────────────────┐
                    │   Scheduler    │
                    │  (Relay Race)  │
                    └────────┬───────┘
                             │
                             ↓
╔═══════════════════════════════════════════════════════════════╗
║                     TURN LOOP (Repeats)                        ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                 ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ BUILDER AGENT (15-20 min)                              │  ║
║  │                                                         │  ║
║  │ Input:                                                  │  ║
║  │  • Current roadmap item                                │  ║
║  │  • Retrieved context from LanceDB                      │  ║
║  │  • Previous defect capsule (if retry)                  │  ║
║  │                                                         │  ║
║  │ Process:                                                │  ║
║  │  1. Construct prompt with full context                 │  ║
║  │  2. Call LM Studio API                                 │  ║
║  │  3. Parse response (code, hints, files)                │  ║
║  │  4. Embed response with text-embedding model           │  ║
║  │  5. Store in LanceDB (turn_id, content, embedding)     │  ║
║  │                                                         │  ║
║  │ Output: BatonPacket                                     │  ║
║  │  • response_text                                        │  ║
║  │  • builder_summary (compressed)                        │  ║
║  │  • files_changed []                                     │  ║
║  │  • verification_hints []                                │  ║
║  │  • metadata {}                                          │  ║
║  └────────────────────────┬────────────────────────────────┘  ║
║                           │                                     ║
║                           ↓                                     ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ VERIFIER AGENT (5-10 min)                              │  ║
║  │                                                         │  ║
║  │ Input: BatonPacket                                      │  ║
║  │                                                         │  ║
║  │ Checks:                                                 │  ║
║  │  ✓ Static analysis (pylint/eslint)                     │  ║
║  │  ✓ Test suite (pytest/jest)                            │  ║
║  │  ✓ LLM coherence check                                 │  ║
║  │  ✓ Domain-specific probes                              │  ║
║  │                                                         │  ║
║  │ Output:                                                 │  ║
║  │  • status: PASSED / FAILED / RETRY                     │  ║
║  │  • defect_capsule (if failed)                          │  ║
║  └────────────────────────┬────────────────────────────────┘  ║
║                           │                                     ║
║                           ↓                                     ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ SCHEDULER DECISION                                      │  ║
║  │                                                         │  ║
║  │  IF status == PASSED:                                   │  ║
║  │    • Store checkpoint                                   │  ║
║  │    • Resubmit to application                           │  ║
║  │    • Move to next roadmap item                         │  ║
║  │    • reset_retry_count()                               │  ║
║  │                                                         │  ║
║  │  ELIF status == FAILED/RETRY:                           │  ║
║  │    • increment_retry_count()                           │  ║
║  │    IF retry_count <= max_retries:                      │  ║
║  │      • Create new builder prompt with defect           │  ║
║  │      • Loop back to BUILDER                            │  ║
║  │    ELSE:                                                │  ║
║  │      • ESCALATE to human                               │  ║
║  │      • Log issue                                        │  ║
║  │      • Move to next item                               │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                 ║
╚═══════════════════════════════════════════════════════════════╝
                             │
                             ↓
                   Continue until roadmap
                      complete
```

## Data Flow: Turn Lifecycle

```
Turn N Start
     │
     ├──→ [1] Scheduler selects roadmap[N]
     │
     ├──→ [2] Builder retrieves context:
     │         LanceDB.search(roadmap[N]) → [similar past turns]
     │
     ├──→ [3] Builder constructs prompt:
     │         prompt = roadmap[N] + context + defect_capsule
     │
     ├──→ [4] LM Studio generates response
     │         POST /v1/chat/completions
     │
     ├──→ [5] Embedder creates vector:
     │         embedding = embed(response)
     │
     ├──→ [6] Store in LanceDB:
     │         turn_id → (content, embedding, metadata)
     │
     ├──→ [7] Verifier runs checks:
     │         • pytest → pass/fail
     │         • pylint → errors []
     │         • LLM coherence → boolean
     │
     ├──→ [8] Decision branch:
     │         ├─→ PASS: checkpoint, resubmit, continue
     │         └─→ FAIL: create defect, retry or escalate
     │
     └──→ Turn N+1 Start (loop)
```

## LanceDB Schema

```
┌──────────────────┐
│  agent_turns     │
├──────────────────┤
│ turn_id          │ PK
│ agent_role       │ builder/verifier
│ content          │ full text
│ vector           │ [768 floats]
│ task_id          │ FK
│ turn_number      │ int
│ status           │ passed/failed/pending
│ timestamp        │ ISO8601
│ files_changed    │ JSON
│ roadmap_chunk    │ text
│ metadata         │ JSON
└──────────────────┘

┌──────────────────┐
│  checkpoints     │
├──────────────────┤
│ checkpoint_id    │ PK
│ turn_id          │ FK
│ checkpoint_type  │ verification_success
│ vector           │ [768 floats]
│ timestamp        │ ISO8601
│ files            │ JSON
│ metadata         │ JSON
└──────────────────┘

┌──────────────────┐
│  defects         │
├──────────────────┤
│ defect_id        │ PK
│ turn_id          │ FK
│ defect_type      │ lint/test/coherence
│ vector           │ [768 floats]
│ severity         │ critical/high/medium/low
│ description      │ text
│ resolved         │ boolean
│ timestamp        │ ISO8601
│ metadata         │ JSON (includes suggested_fix)
└──────────────────┘

┌──────────────────┐
│  escalations     │
├──────────────────┤
│ escalation_id    │ PK
│ task_id          │ FK
│ turn             │ int
│ defect_id        │ FK
│ timestamp        │ ISO8601
│ resolved         │ boolean
│ metadata         │ JSON
└──────────────────┘
```

## Component Communication

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Builder   │       │  Verifier   │       │  Scheduler  │
│             │       │             │       │             │
│ - llm_client├──────▶│- llm_client ├──────▶│ - builder   │
│ - embedder  │       │- embedder   │       │ - verifier  │
│ - db_manager│◀──────┤- db_manager │◀──────┤- db_manager │
│             │       │- test_runner│       │             │
└──────┬──────┘       └──────┬──────┘       └──────┬──────┘
       │                     │                     │
       │    BatonPacket      │                     │
       ├────────────────────▶│                     │
       │                     │  (status, defect)   │
       │                     ├────────────────────▶│
       │                     │                     │
       │◀──────────────────────────────────────────┤
       │           (new prompt with defect)        │
       │                                           │
       └───────────────────────┬───────────────────┘
                               │
                               ↓
                          LanceDB
                      (persistent memory)
```

## Comparison: MCP vs Agent Loop

### Original MCP Loop
```
User Input
    ↓
LLM Generate
    ↓
Embed
    ↓
Store in LanceDB
    ↓
Resubmit to App
    ↓
(no quality check!)
    ↓
Repeat
    ↓
Drift after ~5 min ❌
```

### New Agent Loop
```
User Input + RAG Context
    ↓
Builder Generate
    ↓
Embed & Store
    ↓
Verifier Check ✅
    ├─→ Pass: Resubmit + Continue
    └─→ Fail: Retry with Feedback
    ↓
Coherence maintained 200+ min ✅
```

## Key Architectural Decisions

### 1. Why Separate Builder/Verifier?
- **Single Responsibility:** Builder focuses on generation, Verifier on validation
- **Quality Gates:** Prevents drift by catching issues before they compound
- **Parallel Potential:** Can run multiple builders with single verifier

### 2. Why LanceDB?
- **Vector Search:** Retrieve relevant past context semantically
- **Embedded History:** Natural memory without complex state management
- **Scalable:** Handles thousands of turns efficiently

### 3. Why Baton Pattern?
- **Compression:** Each turn summarized, preventing token explosion
- **Statefulness:** Full context available but condensed
- **Debugging:** Complete audit trail of decisions

### 4. Why Scheduler?
- **Orchestration:** Single source of truth for task state
- **Retry Logic:** Intelligent backoff and escalation
- **Token Management:** Prevents budget overruns

## Performance Characteristics

```
Metric                 | MCP Loop      | Agent Loop
-----------------------|---------------|------------------
Max coherent runtime   | ~5 minutes    | 200+ minutes
Quality assurance      | None          | Multi-layer
Error recovery         | Manual        | Automatic
Context window         | Limited       | Compressed+RAG
Debugging              | Difficult     | Full history
Token efficiency       | Poor          | Optimized
```

## Memory Management Strategy

```
Time: 0 min          60 min         120 min        180 min
      │               │               │               │
      ↓               ↓               ↓               ↓
┌─────────┬───────────┬───────────┬───────────┬─────────┐
│ Full    │ Full      │ Compress  │ Summary   │ Vector  │
│ History │ History   │ Old Turns │ Only      │ Search  │
│ (12     │ (24       │ (36       │ (48       │ (Infinite│
│ turns)  │ turns)    │ turns)    │ turns)    │ turns)  │
└─────────┴───────────┴───────────┴───────────┴─────────┘
          Token Usage Remains Constant
          Quality Maintained Through Embeddings
```

## Integration Points

### 1. Your App ← Scheduler
```python
def _resubmit_to_app(self, baton: BatonPacket):
    # YOUR CODE HERE
    your_app.process(baton)
```

### 2. LM Studio ← Builder/Verifier
```python
POST http://localhost:1234/v1/chat/completions
{
  "model": "local-model",
  "messages": [...],
  "temperature": 0.7
}
```

### 3. Tests ← Verifier
```bash
pytest --json-report
eslint --format json
```

### 4. LanceDB ← All Agents
```python
db.search(embedding).limit(5)
db.add([{turn_data}])
```

This architecture enables your agents to work coherently for hours,
maintaining quality through verification while preserving context
through vector embeddings. 🚀
