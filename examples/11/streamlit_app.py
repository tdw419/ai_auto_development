import json
import os
from pathlib import Path
import streamlit as st
import sqlite3
import pandas as pd
import uuid
import shutil
from datetime import datetime

# Adjust agents import path if necessary
from agents.builder import run_builder
from agents.verifier import run_verifier

# --- Helper Functions ---

def snapshot_run(run_id: str, files: list[str]):
    """Saves a snapshot of runtime artifacts for a specific run."""
    out = Path("runtime/history") / run_id
    out.mkdir(parents=True, exist_ok=True)
    for f in files:
        p = Path(f)
        if p.exists():
            shutil.copy2(p, out / p.name)
    # also capture settings
    settings = {
        "model": st.session_state.get("model", "default"),
        "temperature": st.session_state.get("temperature", 0.7)
    }
    Path(out/"settings.json").write_text(json.dumps(settings, indent=2))

def log_run(run_id: str, phase: str, synopsis: str, pass_flag: bool, git_sha: str = None, defects: dict = None):
    """Logs a builder or verifier run to the SQLite ledger."""
    try:
        conn = sqlite3.connect("data/ledger.db")
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id TEXT PRIMARY KEY,
            ts TEXT,
            phase TEXT,
            roadmap_key TEXT,
            pass INTEGER,
            sha TEXT,
            synopsis TEXT,
            defects TEXT
        )
        """)
        ts = datetime.utcnow().isoformat()
        c.execute(
            "INSERT INTO ledger (id, ts, phase, roadmap_key, pass, sha, synopsis, defects) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, ts, phase, "map/01-test", int(pass_flag) if pass_flag is not None else None, git_sha, synopsis, json.dumps(defects) if defects else None)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Failed to log run: {e}")

# --- Main App ---

st.set_page_config(layout="wide")

# This is important to ensure relative paths work correctly
# when running streamlit from the project root.
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)

Path("runtime").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
baton_path = Path("runtime/baton.json")

st.title("Relay Agents Control Panel")

# --- Sidebar ---
with st.sidebar:
    st.title("LLM Parameters")
    st.selectbox("Model", ["qwen2.5-7b-instruct", "chatgpt-5", "claude-3-opus"], key="model", index=0)
    st.slider("Temperature", 0.0, 1.0, 0.7, 0.1, key="temperature")

# --- Baton Control ---
with st.expander("Baton Control", expanded=True):
    st.subheader("Current Baton")
    if not baton_path.exists():
        st.info("No baton yet. Run a builder cycle to create one.")
    else:
        try:
            baton = json.loads(baton_path.read_text())
            baton_synopsis = st.text_area("Synopsis", value=baton.get("synopsis", ""), height=100)
            baton_next_goal = st.text_area("Next Goal", value=baton.get("next_goal", ""), height=100)
            baton_open_issues = st.text_area("Open Issues (JSON)", value=json.dumps(baton.get("open_issues", []), indent=2), height=100)
            baton_retrieval_keys = st.text_area("Retrieval Keys (JSON)", value=json.dumps(baton.get("retrieval_keys", []), indent=2), height=100)

            if st.button("Save Baton"):
                try:
                    new_baton = {
                        "synopsis": baton_synopsis,
                        "next_goal": baton_next_goal,
                        "open_issues": json.loads(baton_open_issues),
                        "retrieval_keys": json.loads(baton_retrieval_keys)
                    }
                    baton_path.write_text(json.dumps(new_baton, indent=2))
                    st.success("Baton saved!")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Invalid JSON in Open Issues or Retrieval Keys")
        except Exception as e:
            st.error(f"Error loading baton: {e}")

# --- Actions ---
st.subheader("Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Run Builder", use_container_width=True):
        run_id = f"builder_{uuid.uuid4()}"
        with st.spinner("Builder agent is running..."):
            result = run_builder(st.session_state.model, st.session_state.temperature)
            snapshot_run(run_id, ["runtime/baton.json", "runtime/baton.next.json", "runtime/builder_raw.json"])
            log_run(run_id, "builder", result.get("synopsis", "N/A"), None)
        st.success("Builder finished.")
        st.rerun()

with col2:
    if st.button("Run Verifier", use_container_width=True):
        run_id = f"verifier_{uuid.uuid4()}"
        with st.spinner("Verifier agent is running..."):
            outcome = run_verifier()
            snapshot_run(run_id, ["runtime/baton.next.json", "runtime/checkpoint.json", "runtime/defect.json"])
            log_run(run_id, "verifier", "Verification complete.", outcome["pass"], outcome.get("sha"), outcome.get("defect"))
        if outcome["pass"]:
            st.success("Verifier passed.")
        else:
            st.error("Verifier failed.")
        st.rerun()

with col3:
    if st.button("Run Full Cycle", use_container_width=True):
        builder_run_id = f"builder_{uuid.uuid4()}"
        with st.spinner("Builder agent is running..."):
            builder_out = run_builder(st.session_state.model, st.session_state.temperature)
            snapshot_run(builder_run_id, ["runtime/baton.json", "runtime/baton.next.json", "runtime/builder_raw.json"])
            log_run(builder_run_id, "builder", builder_out.get("synopsis", "N/A"), None)
        st.success("Builder finished.")

        verifier_run_id = f"verifier_{uuid.uuid4()}"
        with st.spinner("Verifier agent is running..."):
            outcome = run_verifier()
            snapshot_run(verifier_run_id, ["runtime/baton.next.json", "runtime/checkpoint.json", "runtime/defect.json"])
            log_run(verifier_run_id, "verifier", "Verification complete.", outcome["pass"], outcome.get("sha"), outcome.get("defect"))
        if outcome["pass"]:
            st.success("Verifier passed.")
        else:
            st.error("Verifier failed.")
        st.rerun()

# --- Defect Replay ---
defect_path = Path("runtime/defect.json")
if defect_path.exists():
    with st.expander("Defect Found", expanded=True):
        try:
            defect = json.loads(defect_path.read_text())
            st.error("Last verification failed. Review defect below.")
            st.json(defect)
            if st.button("Replay Last Defect"):
                if baton_path.exists():
                    baton = json.loads(baton_path.read_text())
                    baton["next_goal"] = f"Fix defect: {defect.get('title', 'Unknown defect')}"
                    baton["open_issues"].append(defect)
                    baton_path.write_text(json.dumps(baton, indent=2))
                    st.success("Baton updated for remediation.")
                    st.rerun()
                else:
                    st.error("Cannot replay defect, baton.json not found.")
        except Exception as e:
            st.warning(f"Could not load defect file: {e}")

# --- Ledger ---
st.subheader("Ledger")

ledger_path = "data/ledger.db"
if not os.path.exists(ledger_path):
    st.info("No ledger yet — run a cycle first.")
else:
    conn = sqlite3.connect(ledger_path)
    try:
        df = pd.read_sql_query("SELECT id, ts, phase, roadmap_key, pass, sha, synopsis FROM ledger ORDER BY ts DESC", conn)
    except (pd.errors.DatabaseError, sqlite3.OperationalError):
        st.warning("Ledger is empty or schema is incorrect.")
        df = pd.DataFrame()
    finally:
        conn.close()

    if not df.empty:
        # Filters
        all_phases = sorted(df["phase"].dropna().unique().tolist())
        phase_pick = st.multiselect("Phase", all_phases, default=all_phases)

        status_map = {"pass": 1, "fail": 0, "unknown": None}
        chosen_status_str = st.multiselect("Status", ["pass", "fail", "unknown"], default=["pass", "fail", "unknown"])
        choose_vals = [status_map[s] for s in chosen_status_str]

        # Apply filters
        fdf = df[df["phase"].isin(phase_pick)].copy()
        pass_series = fdf["pass"].apply(lambda x: None if pd.isna(x) else int(x))
        fdf = fdf[pass_series.isin(choose_vals)]

        st.dataframe(fdf, use_container_width=True, height=300)

        # Export / Cleanup
        st.markdown("### Export / Cleanup")
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            st.download_button(
                "Export CSV", data=fdf.to_csv(index=False).encode("utf-8"),
                file_name="ledger.csv", mime="text/csv", use_container_width=True
            )
        with c2:
            st.download_button(
                "Export JSON", data=fdf.to_json(orient="records", indent=2).encode("utf-8"),
                file_name="ledger.json", mime="application/json", use_container_width=True
            )
        with c3:
            with st.popover("Danger zone"):
                st.caption("Delete selected runs and their artifacts.")
                run_ids_to_show = fdf["id"].tolist()
                to_delete = st.multiselect("Choose run ids to delete", run_ids_to_show, default=[])
                if st.button("Delete selected", type="primary", disabled=not to_delete):
                    # Delete artifact folders
                    for rid in to_delete:
                        adir = Path("runtime/history") / rid
                        if adir.exists():
                            shutil.rmtree(adir, ignore_errors=True)
                    # Delete from SQLite
                    con = sqlite3.connect(ledger_path)
                    q = "DELETE FROM ledger WHERE id IN ({})".format(",".join(["?"]*len(to_delete)))
                    con.execute(q, to_delete)
                    con.commit()
                    con.close()
                    st.success(f"Deleted {len(to_delete)} run(s).")
                    st.rerun()

        # Inspect Run
        st.markdown("### Inspect Run")
        run_ids = fdf["id"].tolist()
        if not run_ids:
            st.info("No runs match the current filters.")
        else:
            sel = st.selectbox("Select a run id", run_ids)
            row = fdf[fdf["id"] == sel].iloc[0]

            st.write(f"**Phase:** {row['phase']}  |  **Status:** "
                     f"{'pass' if row['pass']==1 else ('fail' if row['pass']==0 else 'unknown')}  "
                     f"|  **SHA:** {row['sha'] or '—'}")

            art_dir = Path("runtime/history") / sel
            if art_dir.exists():
                st.markdown(f"**Artifacts from `{art_dir}`**")
                for p in sorted(art_dir.glob("*")):
                    with st.expander(p.name, expanded=False):
                        try:
                            if p.suffix.lower() == ".json":
                                st.json(json.loads(p.read_text()))
                            else:
                                st.code(p.read_text())
                        except Exception:
                            st.code(p.read_text(errors='ignore'))
            else:
                st.info("No saved artifacts for this run.")
    else:
        st.info("Ledger is empty. Run a cycle to begin.")
