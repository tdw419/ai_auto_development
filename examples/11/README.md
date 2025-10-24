# Relay Agents Starter (Builder → Verifier → Scheduler)

This is a tiny, drop-in starter to replace a monolithic MCP loop with a relay-style multi-agent
verification loop while keeping your original RAG + LanceDB + LM Studio flow.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # edit if needed (LM_STUDIO_URL, etc.)

git init && git add -A && git commit -m "init agents relay"

# seed baton (optional; schedule.py will do this if missing)
mkdir -p runtime data

python3 agents/schedule.py
```
