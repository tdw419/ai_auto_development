#!/usr/bin/env python3
import json, time, subprocess, pathlib, sys, sqlite3, os

from agents.remediation.orchestrator import RemediationOrchestrator
from utils.time_utils import to_iso, utc_now

RUN = lambda cmd: subprocess.run(cmd, check=False)

LEDGER = os.environ.get("LEDGER_DB","./data/ledger.db")
pathlib.Path("runtime").mkdir(exist_ok=True, parents=True)
pathlib.Path("data").mkdir(exist_ok=True, parents=True)

def db():
    c = sqlite3.connect(LEDGER)
    c.execute("""create table if not exists ledger(
        id text primary key, ts text, phase text, roadmap_key text,
        synopsis text, pass int, sha text, defects text
    )""")
    return c

def log_row(phase, roadmap_key, synopsis, passed=None, sha=None, defects=None):
    c = db()
    now = to_iso(utc_now())
    row_id = f"{now}-{phase}"
    c.execute("insert into ledger values(?,?,?,?,?,?,?,?)",
              (row_id, now, phase, roadmap_key,
               synopsis[:500], None if passed is None else int(passed),
               sha, json.dumps(defects or [])))
    c.commit()

if __name__ == "__main__":
    # seed a baton if none
    baton_path = pathlib.Path("runtime/baton.json")
    if not baton_path.exists():
        baton_path.write_text(json.dumps({
            "synopsis": "Fresh start.",
            "next_goal": "Implement bounded, inertial zoom on 2D map.",
            "open_issues": [],
            "retrieval_keys": ["map pan", "zoom", "wgsl transform"]
        }, indent=2))

    # === Builder ===
    RUN(["python3","examples/11/agents/builder.py"])
    baton_next = json.loads(open("runtime/baton.next.json").read())
    log_row("builder", "map/02-panzoom", baton_next.get("synopsis",""))

    # === Verifier ===
    v = subprocess.run(["python3","examples/11/agents/verifier.py"], capture_output=True, text=True)
    ok = v.returncode == 0
    out = {}
    try: out = json.loads(v.stdout.strip() or "{}")
    except: pass

    if ok:
        sha = json.loads(open("runtime/checkpoint.json").read())["sha"]
        log_row("verifier", "map/02-panzoom", baton_next.get("synopsis",""), True, sha, [])
        # advance baton goal or keep iterating
        open("runtime/baton.json","w").write(json.dumps({
            "synopsis": baton_next.get("synopsis",""),
            "next_goal": "Tighten zoom damping constant and add unit tests.",
            "open_issues": baton_next.get("open_issues",[]),
            "retrieval_keys": baton_next.get("retrieval_keys",[])
        }, indent=2))
        sys.exit(0)

    defect = out.get("defect", {"title": "unknown", "repro_steps": [], "observations": ""})
    log_row("verifier", "map/02-panzoom", baton_next.get("synopsis", ""), False, None, [defect])

    # Prepare remediation baton
    remediator = RemediationOrchestrator(pathlib.Path("."))
    out["attempt"] = baton_next.get("task", {}).get("remediation_attempt", 0) + 1
    remediation_baton = remediator.generate_remediation_baton(out, baton_next)
    open("runtime/baton.json", "w").write(json.dumps(remediation_baton, indent=2))
    sys.exit(1)
