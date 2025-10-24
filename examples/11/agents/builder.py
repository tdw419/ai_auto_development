#!/usr/bin/env python3
import os
import sys
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple

import lancedb  # pip install lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer  # or your qwen3 embedding wrapper
from utils.llm_client import LLMClient

# Ensure project root is on import path for schemas/utils
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from schemas.task_models import (
    TaskObject,
    create_default_task,
    create_remediation_task,
)
from utils.validators import (
    task_validator,
    validate_output_against_contract,
    validate_constraints,
)

DB_PATH = os.environ.get("LANCEDB_PATH", "./data/lancedb")
EMBED_MODEL = os.environ.get("EMB_MODEL", "all-MiniLM-L6-v2")  # swap to qwen3-0.6B wrapper

def lance():
    return lancedb.connect(DB_PATH)

def retrieve(keys, k=6):
    db = lance()
    if "memory" not in db.table_names():
        return []
    tbl = db.open_table("memory")
    if not keys:
        return []
    q = " ".join(keys)
    return [r["text"] for r in tbl.search(q).limit(k).to_list()]

def embed_texts(texts):
    model = SentenceTransformer(EMBED_MODEL)
    return model.encode(texts, normalize_embeddings=True)

def upsert(kind, text, meta):
    db = lance()
    if "memory" in db.table_names():
        tbl = db.open_table("memory")
    else:
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("kind", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 384)),
            pa.field("meta", pa.string())
        ])
        tbl = db.create_table("memory", schema=schema)
    vec = embed_texts([text])[0].tolist()
    tbl.add([{"id": str(uuid.uuid4()), "kind": kind, "text": text, "vector": vec, "meta": json.dumps(meta)}])

DEFAULT_BATON = {
    "synopsis": "Fresh start.",
    "next_goal": "Define the first development goal before running builder.",
    "open_issues": [],
    "retrieval_keys": [],
}

def ensure_baton():
    baton_path = Path("runtime/baton.json")
    baton_path.parent.mkdir(parents=True, exist_ok=True)
    if not baton_path.exists():
        baton_path.write_text(json.dumps(DEFAULT_BATON, indent=2))
    return baton_path

def load_task_from_baton(baton: Dict[str, Any]) -> Tuple[TaskObject, str]:
    """Extract and validate task object from baton data."""
    is_valid, task_object, message = task_validator.validate_baton(baton)
    if is_valid and task_object:
        return task_object, message

    # Fall back to default task if validation fails
    fallback_goal = baton.get("next_goal") or baton.get("task", {}).get("goal") or "Complete the assigned task"
    if task_object and task_object.agent_context:
        fallback_task = create_default_task(
            fallback_goal,
            agent_context=task_object.agent_context,
        )
    else:
        fallback_task = create_default_task(fallback_goal)
    return fallback_task, f"Fell back to default task: {message}"


def format_task_for_prompt(task: TaskObject) -> str:
    """Serialize task object safely for inclusion in prompt."""
    task_dict = task.dict()
    task_dict["created_at"] = task_dict["created_at"].isoformat()
    return json.dumps(task_dict, indent=2)


def run_builder(model="qwen2.5-7b-instruct", temperature=0.4):
    baton_path = ensure_baton()
    baton = json.loads(baton_path.read_text())
    client = LLMClient(model=model)

    task_object, validation_message = load_task_from_baton(baton)

    state_synopsis = task_object.agent_context.previous_synopsis or baton.get("synopsis", "")
    open_issues = task_object.agent_context.open_issues or baton.get("open_issues", [])
    retrieval_keys = task_object.agent_context.retrieval_keys or baton.get("retrieval_keys", [])
    retrieved = retrieve(retrieval_keys)
    next_goal = task_object.goal

    system = Path("examples/11/prompts/builder.system.txt").read_text()
    user = (
        Path("examples/11/prompts/builder.user.txt").read_text()
        .replace("{{next_goal}}", next_goal)
        .replace("{{state_synopsis}}", state_synopsis)
        .replace("{{open_issues_json}}", json.dumps(open_issues))
        .replace("{{retrieved_snippets}}", "\n\n---\n".join(retrieved))
        .replace("{{task_json}}", format_task_for_prompt(task_object))
    )

    t0 = time.time()
    out = client.generate_text_response(
        prompt=user,
        system_message=system,
        temperature=temperature,
    )
    Path("runtime/builder_raw.json").write_text(out)
    try:
        baton_next = json.loads(out)
    except:
        # fallback: wrap non-json into synopsis
        baton_next = {"synopsis": out[:800], "patch_bundle": [], "verification_hints": [], "open_issues": open_issues}

    # Validate output against task contract/constraints
    is_valid_output, missing_fields = validate_output_against_contract(baton_next, task_object)
    if not is_valid_output:
        baton_next.setdefault("_validation_errors", {})
        baton_next["_validation_errors"]["missing_fields"] = missing_fields
        raise ValueError(f"Builder output missing required fields: {missing_fields}")

    constraints_ok, constraint_violations = validate_constraints(baton_next, task_object)
    if not constraints_ok:
        baton_next.setdefault("_validation_errors", {})
        baton_next["_validation_errors"]["constraints"] = constraint_violations
        raise ValueError(f"Builder output violated constraints: {constraint_violations}")

    # Persist to LanceDB with task metadata
    upsert(
        "builder_output",
        baton_next.get("synopsis", ""),
        {
            "goal": next_goal,
            "task_id": task_object.id,
            "validation": validation_message,
        },
    )

    # Persist baton for verifier
    baton_payload = {
        "builder_output": baton_next,
        **baton_next,
        "retrieved_snippets": retrieved,
        "task": task_object.dict(),
        "agent_context": task_object.agent_context.dict(),
        "validation_message": validation_message,
    }
    Path("runtime/baton.next.json").write_text(json.dumps(baton_payload, indent=2))
    print(f"Builder done in {time.time()-t0:.1f}s (task_id={task_object.id})")
    return baton_payload

if __name__ == "__main__":
    run_builder()
