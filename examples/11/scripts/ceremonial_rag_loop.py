# pip install lancedb requests pydantic
import os, uuid, time, math, random, hashlib, argparse, yaml
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
import lancedb
from pydantic import BaseModel
from lancedb.pydantic import LanceModel, Vector

# --- CLI + Config ---
def parse_args():
    parser = argparse.ArgumentParser(description="Ceremonial Local RAG Loop for GVPIE")
    # Core
    parser.add_argument("--seed", required=True, help="Initial task seed")
    parser.add_argument("--lm-url", default=os.getenv("LM_URL", "http://127.0.0.1:1234/v1"))
    parser.add_argument("--chat-mdl", default=os.getenv("CHAT_MODEL", "qwen/qwen3-4b-instruct"))
    parser.add_argument("--emb-mdl", default=os.getenv("EMB_MODEL", "text-embedding-qwen3-0.6b"))
    parser.add_argument("--db-path", default=os.getenv("DB_PATH", "./ragdb"))
    parser.add_argument("--manifest-dir", default=os.getenv("MANIFEST_DIR", "./manifests"))
    # Pixel VM
    parser.add_argument("--tile-size", default="8x8", help="Pixel tile dimensions (e.g., 16x16)")
    parser.add_argument("--dtype", default="fp32", help="Data type (fp16/fp32)")
    parser.add_argument("--isa", default="GVPIE_v2", help="Target ISA version")
    parser.add_argument("--ops", nargs="+", default=["sobel"], help="Pixel operations")
    # Resilience
    parser.add_argument("--use-ctx", type=lambda x: x.lower() in ('true', '1'), default=True)
    parser.add_argument("--max-iters", type=int, default=4)
    parser.add_argument("--emb-max-chars", type=int, default=1500)
    parser.add_argument("--emb-cache", type=lambda x: x.lower() in ('true', '1'), default=True)
    parser.add_argument("--rag-max-dist", type=float, default=0.35)
    parser.add_argument("--ctx-window-tok", type=int, default=4096)
    parser.add_argument("--budget-prompt-tok", type=int, default=2800)
    parser.add_argument("--validate", action="store_true", help="Validate generated pixel shaders")
    return parser.parse_args()

args = parse_args()
os.makedirs(args.manifest_dir, exist_ok=True)

# --- Core Config ---
HTTP_TIMEOUT = 120
MAX_RETRIES = 3
BACKOFF_BASE = 0.6
CHUNK_OVERLAP = 120
LM_URL = args.lm_url
CHAT_MDL = args.chat_mdl
EMB_MDL = args.emb_mdl
DB_PATH = args.db_path
MANIFEST_DIR = args.manifest_dir
USE_CTX = args.use_ctx
MAX_ITERS = args.max_iters
EMB_MAX_CHARS = args.emb_max_chars
EMB_CACHE_ON = args.emb_cache
RAG_MAX_DIST = args.rag_max_dist
CTX_WINDOW_TOK = args.ctx_window_tok
BUDGET_PROMPT = args.budget_prompt_tok
PIXEL_META = {
    "tile_size": args.tile_size,
    "dtype": args.dtype,
    "isa": args.isa,
    "ops": args.ops
}
EMB_CACHE_TABLE = "embeddings_cache"

# ----------------------------
# DB & HTTP
# ----------------------------
db = lancedb.connect(DB_PATH)
EMB_CACHE: Dict[str, List[float]] = {}

def _jitter_delay(attempt_idx:int)->float:
    # exponential backoff with jitter
    base = BACKOFF_BASE * (2 ** attempt_idx)
    return base * (0.5 + random.random()) # 0.5x..1.5x

def _post(path: str, payload: Dict[str, Any], timeout=HTTP_TIMEOUT) -> Dict[str, Any]:
    url = f"{LM_URL}{path}"
    last_err = None
    for i in range(MAX_RETRIES):
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            last_err = e
            # LM Studio common transient message
            msg = getattr(getattr(e, "response", None), "text", "") or str(e)
            transient = any(s in msg.lower() for s in [
                "unloaded", "crashed", "connection", "timeout", "temporarily"
            ])
            if i < MAX_RETRIES - 1 and transient:
                time.sleep(_jitter_delay(i))
                continue
            raise
    # should not reach here
    raise last_err or RuntimeError("unknown HTTP failure")

# ----------------------------
# Token-ish counting & pruning
# ----------------------------
def approx_tokens(s: str) -> int:
    # very rough: avg 4 chars/token
    return max(1, math.ceil(len(s) / 4))

def prune_history(messages: List[Dict[str,str]], token_budget=BUDGET_PROMPT, hard_cap=CTX_WINDOW_TOK) -> List[Dict[str,str]]:
    # Keep system + as many tail messages as fit
    if not messages: return messages
    sys = [m for m in messages if m["role"]=="system"]
    rest = [m for m in messages if m["role"]!="system"]

    def total_tokens(ms):
        return sum(approx_tokens(m.get("content","")) for m in ms)

    kept = []
    for m in reversed(rest):
        trial = sys + list(reversed(kept)) + [m]
        if total_tokens(trial) <= min(token_budget, hard_cap):
            kept.append(m)
        else:
            break
    result = sys + list(reversed(kept))
    # As last resort, truncate the longest user content
    while total_tokens(result) > hard_cap and len(result) > 2:
        # drop the oldest non-system
        for idx, m in enumerate(result):
            if m["role"]!="system":
                result.pop(idx)
                break
    return result

# ----------------------------
# Embeddings (chunk → mean pool)
# ----------------------------
def _chunk_text(s: str, max_chars=EMB_MAX_CHARS, overlap=CHUNK_OVERLAP) -> List[str]:
    s = s.strip()
    if len(s) <= max_chars: return [s]
    chunks = []
    start = 0
    while start < len(s):
        end = min(len(s), start + max_chars)
        chunk = s[start:end]
        chunks.append(chunk)
        if end == len(s): break
        start = max(0, end - overlap)
    return chunks

def _mean(vectors: List[List[float]]) -> List[float]:
    n = len(vectors)
    if n == 1: return vectors[0]
    d = len(vectors[0])
    out = [0.0]*d
    for v in vectors:
        for i,x in enumerate(v):
            out[i]+=x
    return [x/n for x in out]

def embed_once(text: str) -> List[float]:
    j = _post("/embeddings", {"model": EMB_MDL, "input": text})
    return j["data"][0]["embedding"]

def _cache_vec_dim() -> Optional[int]:
    """Infer cache vector dim from the first row, if the cache exists & is non-empty."""
    if EMB_CACHE_TABLE not in db.table_names():
        return None
    t = db.open_table(EMB_CACHE_TABLE)
    try:
        row = next(iter(t.to_reader().take(1)), None)
        if row and "vector" in row and isinstance(row["vector"], list):
            return len(row["vector"])
    except Exception:
        pass
    return None

def _ensure_cache_table(vec_dim: int):
    """Create the cache table with locked dimension if it doesn’t exist."""
    if EMB_CACHE_TABLE in db.table_names():
        # If the table exists, ensure its dimension matches.
        existing = _cache_vec_dim()
        if existing is not None and existing != vec_dim:
            raise RuntimeError(
                f"[{EMB_CACHE_TABLE}] dim mismatch: table={existing}, runtime={vec_dim}. "
                f"Delete the cache table or point EMB_CACHE_TABLE to a new name."
            )
        return db.open_table(EMB_CACHE_TABLE)

    # Define schema with locked vector dim
    class EmbCache(LanceModel):
        key: str
        vector: Vector(vec_dim)

    print(f"[cache] Creating LanceDB cache table '{EMB_CACHE_TABLE}' (dim={vec_dim})")
    return db.create_table(EMB_CACHE_TABLE, schema=EmbCache.to_arrow_schema())

def _cache_lookup(key: str) -> Optional[list]:
    """Return cached vector if present; otherwise None."""
    if EMB_CACHE_TABLE not in db.table_names():
        return None
    dim = _cache_vec_dim()
    if dim is None:
        return None
    t = db.open_table(EMB_CACHE_TABLE)
    # Use a zero-vector and filter on the primary key; avoids computing a fresh embedding.
    zeros = [0.0] * dim
    try:
        rows = t.search(zeros).where(f"key = '{key}'").limit(1).to_list()
        if rows:
            return rows[0].get("vector")
    except Exception:
        # Older LanceDB versions: fall back to scanning if needed
        for row in t.to_reader().to_dict_iter():
            if row.get("key") == key:
                return row.get("vector")
    return None

def _cache_add(key: str, vector: list):
    """Insert a new cached vector (no upsert race-handling for simplicity)."""
    t = _ensure_cache_table(len(vector))
    try:
        t.add([{"key": key, "vector": vector}])
    except Exception as e:
        print(f"[warn] cache add failed for key={key[:8]}…: {e}")

def embed(text: str) -> List[float]:
    # Stable key across runs and models
    key = hashlib.sha256((EMB_MDL + "\n" + text).encode("utf-8")).hexdigest()

    # 1) Persistent cache
    if EMB_CACHE_ON:
        v = _cache_lookup(key)
        if v:
            return v

    # 2) Compute (chunk -> embed_once -> mean-pool)
    vecs = [embed_once(c) for c in _chunk_text(text)]
    v = _mean(vecs)

    # 3) Persist + in-memory (optional)
    if EMB_CACHE_ON:
        _cache_add(key, v)

    return v

# ----------------------------
# LanceDB: explicit schema & validation
# ----------------------------
def _fetch_table_vec_dim(name: str) -> Optional[int]:
    t = db.open_table(name)
    try:
        row = next(iter(t.to_reader().take(1)), None)
        if row and "embedding" in row and isinstance(row["embedding"], list):
            return len(row["embedding"])
    except Exception:
        pass
    return None # unknown (empty table)

def ensure_table(vec_dim: int):
    name = "docs"
    if name in db.table_names():
        # validate dimension if we can detect it
        existing = _fetch_table_vec_dim(name)
        if existing is not None and existing != vec_dim:
            raise RuntimeError(f"[docs] embedding dim mismatch: table={existing}, runtime={vec_dim}. "
                               f"Recreate table or point DB_PATH to a fresh dir.")
        return db.open_table(name)
    # dynamic LanceModel with locked dimension
    class Doc(LanceModel):
        text: str
        embedding: Vector(vec_dim) # locks schema
        meta: dict = {}
    return db.create_table(name, schema=Doc.to_arrow_schema())

def upsert(text: str, meta: dict | None = None):
    e = embed(text)
    t = ensure_table(len(e))
    t.add([{"text": text, "embedding": e, "meta": meta or {}}])

def search_with_scores(q: str, k=3):
    if "docs" not in db.table_names(): return []
    e = embed(q)
    t = db.open_table("docs")
    # Try to surface score/distance if available
    try:
        rows = t.search(e).limit(k).to_list()
    except TypeError:
        rows = t.search(e).limit(k).to_dict() # older API fallback
    hits = []
    for r in rows:
        score = None
        for key in ("score", "vector_distance", "_distance", "_score", "distance"):
            if key in r:
                score = r[key]
                break
        hits.append({"text": r.get("text",""), "score": score})
    return hits

# ----------------------------
# Chat wrapper
# ----------------------------
def chat(messages: List[Dict[str,str]]) -> str:
    payload = {
        "model": CHAT_MDL,
        "messages": prune_history(messages),
        "max_tokens": 512,
    }
    j = _post("/chat/completions", payload)
    return j["choices"][0]["message"]["content"].strip()

# ----------------------------
# Orchestrator loop
# ----------------------------
def run(seed: str):
    check_server_and_models()
    session = str(uuid.uuid4())
    history = [{"role": "system", "content": "Be concise and precise."}]
    manifest = {"run_id": f"{datetime.now():%Y%m%d-%H%M%S}-{session[:8]}", "seed": seed, "iterations": []}

    for i in range(MAX_ITERS):
        ctx_block, mode = "", "GEN-only"
        if USE_CTX:
            hits = search_with_scores(seed, k=3)
            if hits and hits[0] and hits[0].get("score") and hits[0]["score"] <= RAG_MAX_DIST:
                ctx_block = "CONTEXT:\n" + "\n---\n".join(h["text"] for h in hits) + "\n\n"
                mode = f"RAG (dist={hits[0]['score']:.2f})"

        prompt = (f"{ctx_block}You must answer ONLY using the provided CONTEXT.\n"
                  if ctx_block else "") + f"TASK:\n{seed}"
        history.append({"role": "user", "content": prompt})
        reply = chat(history)
        history.append({"role": "assistant", "content": reply})

        validation_result = None
        if args.validate:
            success, summary = validate_pixel_shader(reply)
            validation_result = {"success": success, "summary": summary}
            print(f"[validation] {summary}")

        manifest["iterations"].append({
            "iter": i,
            "mode": mode,
            "prompt": prompt,
            "reply": reply,
            "context_hits": [h["text"] for h in hits] if hits else None,
            "validation": validation_result
        })

        upsert(reply, {"iter": i, "session": session, "mode": mode, "validation": validation_result})
        print(f"\n--- Iter {i} | {mode} ---\n{reply}\n")

        if "status:done" in reply.lower():
            break
        seed = reply

    # Write manifest
    with open(f"{MANIFEST_DIR}/{manifest['run_id']}.yaml", "w") as f:
        yaml.dump(manifest, f)
    print(f"[manifest] Written to {MANIFEST_DIR}/{manifest['run_id']}.yaml")

# ----------------------------
# Validation
# ----------------------------
def validate_pixel_shader(shader_code: str) -> (bool, str):
    """
    Simulates running a test suite on the generated pixel shader code.
    Returns a tuple of (success, summary).
    """
    # In a real implementation, this would invoke a compiler and a test harness.
    # For this simulation, we'll just check for some keywords.
    if "error" in shader_code.lower():
        return False, "Validation failed: Shader contains 'error' keyword."
    if "v_color" not in shader_code:
        return False, "Validation failed: Shader does not contain 'v_color' attribute."
    if "gl_FragColor" not in shader_code:
        return False, "Validation failed: Shader does not set 'gl_FragColor'."

    return True, "Validation successful: All checks passed."

# ----------------------------
# Demo
# ----------------------------
def check_server_and_models():
    """Fail fast if LM Studio isn’t ready and the models aren’t loaded."""
    url = f"{LM_URL}/models"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        have = {m.get("id") for m in data}
        if CHAT_MDL not in have:
            raise RuntimeError(f"Chat model '{CHAT_MDL}' not loaded. Loaded: {sorted(have)}")
        if EMB_MDL not in have:
            raise RuntimeError(f"Embedding model '{EMB_MDL}' not loaded. Loaded: {sorted(have)}")
        # Smoke test the embeddings endpoint with a tiny call
        _ = _post("/embeddings", {"model": EMB_MDL, "input": "health check"})
        print("[health] ✅ Models ready")
    except Exception as e:
        raise RuntimeError(f"[health] ❌ LM Studio check failed: {e}")


if __name__ == "__main__":
    run(args.seed)