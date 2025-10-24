import json
import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from agents.builder import run_builder
from agents.verifier import run_verifier
from agents.remediation.orchestrator import RemediationOrchestrator
from utils.validators import task_validator
from utils.metrics import collect_metrics
from learning.failure_patterns import FailurePatternAnalyzer
from learning.prompt_optimizer import PromptOptimizer
from utils.intelligent_cache import get_cache
from utils.time_utils import to_iso, utc_now

# Ensure we operate from project root so relative paths match CLI scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)

st.title("Relay Agents Control Panel")
cache = get_cache()

# Metrics sidebar
metrics = collect_metrics()
st.sidebar.subheader("Performance")
st.sidebar.metric("Verifications", metrics.get("total_verifications", 0))
st.sidebar.metric("Success Rate", f"{metrics.get('success_rate', 0)*100:.1f}%")
st.sidebar.metric("ARS Score", f"{metrics.get('ars_score', 1.0)*100:.1f}%")

# Sidebar for LLM parameters
st.sidebar.title("LLM Parameters")
model_options = ["qwen2.5-7b-instruct", "codellama-7b", "mistral-7b-instruct"]
selected_model = st.sidebar.selectbox("Model", model_options, index=0)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.4, 0.05)

# Inspect baton
runtimes_dir = Path("runtime")
runtimes_dir.mkdir(parents=True, exist_ok=True)
HISTORY_DIR = runtimes_dir / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
baton_path = runtimes_dir / "baton.json"
if not baton_path.exists():
    baton_path.write_text(json.dumps({
        "synopsis": "Fresh start.",
        "next_goal": "Define the first development goal before running builder.",
        "open_issues": [],
        "retrieval_keys": []
    }, indent=2))

baton = json.loads(baton_path.read_text())

st.subheader("Current Baton")
st.json(baton)

st.subheader("Edit Baton State")
synopsis_input = st.text_area("Synopsis", baton.get("synopsis", ""), height=100)
next_goal_input = st.text_area("Next Goal", baton.get("next_goal", ""), height=100)
open_issues_input = st.text_area(
    "Open Issues (JSON array)",
    json.dumps(baton.get("open_issues", []), indent=2),
    height=150,
)
retrieval_keys_input = st.text_input(
    "Retrieval Keys (comma-separated)",
    ", ".join(baton.get("retrieval_keys", []))
)

if st.button("Save Baton State"):
    try:
        new_open_issues = json.loads(open_issues_input or "[]")
        if not isinstance(new_open_issues, list):
            raise ValueError("Open issues must be a JSON array.")
    except (json.JSONDecodeError, ValueError) as exc:
        st.error(f"Could not parse open issues: {exc}")
    else:
        new_retrieval_keys = [k.strip() for k in retrieval_keys_input.split(",") if k.strip()]
        baton.update({
            "synopsis": synopsis_input.strip(),
            "next_goal": next_goal_input.strip(),
            "open_issues": new_open_issues,
            "retrieval_keys": new_retrieval_keys,
        })
        baton_path.write_text(json.dumps(baton, indent=2))
        st.success("Baton state updated.")
        st.experimental_rerun()

st.subheader("Task Object Editor")
task_json = baton.get("task", {})
task_text = st.text_area("Task Object JSON", json.dumps(task_json, indent=2), height=220)
col_validate, col_save = st.columns(2)
with col_validate:
    if st.button("Validate Task Object"):
        try:
            task_data = json.loads(task_text or "{}")
            is_valid, task_obj, message = task_validator.validate_and_create_task(task_data)
            if is_valid:
                st.success("Task object valid.")
            else:
                st.error(message)
        except json.JSONDecodeError as exc:
            st.error(f"Task JSON invalid: {exc}")
with col_save:
    if st.button("Save Task Object"):
        try:
            task_data = json.loads(task_text or "{}")
            is_valid, task_obj, message = task_validator.validate_and_create_task(task_data)
            if not is_valid:
                st.error(message)
            else:
                baton["task"] = task_obj.dict()
                baton_path.write_text(json.dumps(baton, indent=2))
                st.success("Task object saved to baton.")
                st.experimental_rerun()
        except json.JSONDecodeError as exc:
            st.error(f"Task JSON invalid: {exc}")

st.subheader("Verification Metrics")
metric_cols = st.columns(4)
metric_cols[0].metric("Total Runs", metrics.get("total_verifications", 0))
metric_cols[1].metric("Success Rate", f"{metrics.get('success_rate', 0)*100:.1f}%")
metric_cols[2].metric("Avg Confidence", f"{metrics.get('average_confidence', 0)*100:.1f}%")
metric_cols[3].metric("ARS Score", f"{metrics.get('ars_score', 1.0)*100:.1f}%")

if metrics.get("recent_failures"):
    with st.expander("Recent Failures"):
        for failure in metrics["recent_failures"]:
            st.write(f"- [{failure.get('severity', 'unknown')}] {failure.get('title')} ({failure.get('timestamp')})")

st.subheader("System Insights")
insight_cols = st.columns(2)
if insight_cols[0].button("Run Failure Pattern Analysis"):
    show_pattern_analysis()
if insight_cols[1].button("Prompt Optimization Insights"):
    show_prompt_optimization()

st.subheader("Cache Management")
cache_stats = cache.stats()
cache_cols = st.columns(3)
cache_cols[0].metric("LLM rows", cache_stats["llm"]["stored_rows"])
cache_cols[1].metric("Verification rows", cache_stats["verification"]["stored_rows"])
cache_cols[2].metric("LLM memory", cache_stats["llm"]["memory_items"])

with st.expander("Cache details"):
    st.json(cache_stats)

if st.button("Cleanup Expired Cache Entries"):
    with st.spinner("Removing expired cache entries..."):
        removed = cache.cleanup()
    st.success(
        f"Removed expired rows — LLM: {removed['llm']}, Verification: {removed['verification']}, Patterns: {removed['patterns']}"
    )


def show_pattern_analysis() -> None:
    st.header("🔍 Failure Pattern Analysis")
    analyzer = FailurePatternAnalyzer()
    with st.spinner("Analyzing verification history..."):
        analysis = analyzer.analyze_verification_history()

    summary = analysis.get("summary", {})
    cols = st.columns(4)
    cols[0].metric("Records", summary.get("total_verifications", 0))
    cols[1].metric("Success Rate", f"{summary.get('success_rate', 0)*100:.1f}%")
    cols[2].metric("ARS", f"{summary.get('adversarial_resilience_score', 1)*100:.1f}%")
    cols[3].metric("Discrepancy", f"{summary.get('discrepancy_rate', 0)*100:.1f}%")

    clusters = analysis.get("pattern_clusters", [])
    if clusters:
        st.subheader("Recurring Patterns")
        for cluster in clusters[:5]:
            with st.expander(f"{cluster['primary_type']} (×{cluster['frequency']})"):
                st.write(f"Severity: {cluster['severity']}")
                st.write(f"Recurrence: {cluster['recurrence_rate']*100:.1f}%")
                if cluster["common_files"]:
                    st.write(f"Common files: {', '.join(cluster['common_files'])}")

    recommendations = analysis.get("recommendations", [])
    if recommendations:
        st.subheader("Recommendations")
        for rec in recommendations:
            priority = rec.get("priority", "medium").upper()
            st.write(f"**[{priority}] {rec['description']}**")
            st.write(f" → {rec['action']}")


def show_prompt_optimization() -> None:
    st.header("🔄 Prompt Optimization Insights")
    optimizer = PromptOptimizer()
    insights = optimizer.get_optimization_insights()

    cols = st.columns(3)
    cols[0].metric("Variants Tested", insights.get("total_records", 0))
    cols[1].metric("Evolution Steps", insights.get("evolution_steps", 0))
    trend = insights.get("trend", {})
    cols[2].metric("Trend", trend.get("trend", "unknown"))

    st.subheader("Top Performing Variants")
    for variant in insights.get("top_variants", []):
        st.write(
            f"**{variant['variant_id']}** (fitness {variant['fitness']:.3f}, tests {variant['tests']}, generation {variant['generation']})"
        )


defect_path = runtimes_dir / "defect.json"
if defect_path.exists():
    st.subheader("Last Defect Capsule")
    defect_data = json.loads(defect_path.read_text())
    st.json(defect_data)
    if st.button("Replay Last Defect"):
        updated_baton = {
            "synopsis": f"Remediate verifier defect: {defect_data.get('title', 'Unnamed defect')}",
            "next_goal": defect_data.get("title", "Address verifier defect"),
            "open_issues": [defect_data],
            "retrieval_keys": baton.get("retrieval_keys", []),
        }
        baton_path.write_text(json.dumps(updated_baton, indent=2))
        st.success("Baton updated from last defect.")
        st.experimental_rerun()


def start_remediation_sprint(defect: Dict[str, Any]) -> None:
    """Trigger remediation via orchestrator and refresh the baton."""
    orchestrator = RemediationOrchestrator(Path("."))
    current_baton = json.loads(baton_path.read_text())
    verification_snapshot = {"defect": defect, "attempt": current_baton.get("task", {}).get("remediation_attempt", 0) + 1}
    remediation_baton = orchestrator.generate_remediation_baton(verification_snapshot, current_baton)
    baton_path.write_text(json.dumps(remediation_baton, indent=2))
    st.success("Remediation baton prepared. Builder can now run the remediation sprint.")
    st.experimental_rerun()


def show_verifier_details(outcome: Dict[str, Any]) -> None:
    """Pretty-print verifier responses from all judges."""
    verdict = "PASS" if outcome.get("pass") else "FAIL"
    st.subheader(f"Verifier Output — {verdict}")
    cols = st.columns(3)
    cols[0].metric("Verdict", verdict)
    cols[1].metric("Confidence", f"{outcome.get('confidence', 0.0)*100:.1f}%")
    if outcome.get("pass"):
        cols[2].metric("SHA", outcome.get("sha", "n/a"))
    else:
        cols[2].metric("Severity", (outcome.get("defect") or {}).get("severity", "unknown"))

    with st.expander("Meta Judge Verdict", expanded=True):
        st.json(outcome.get("meta", {}))
    with st.expander("Adversarial Judge Findings"):
        st.json(outcome.get("adversarial", {}))
    with st.expander("Probing Judge Report"):
        st.json(outcome.get("probing", {}))

    if outcome.get("pass"):
        try:
            log_output = subprocess.run(
                ["git", "log", "-n", "5", "--pretty=format:%h %s"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
            if log_output:
                with st.expander("Recent Commits"):
                    for line in log_output:
                        st.write(line)
        except Exception as git_exc:
            st.warning(f"Unable to read git log: {git_exc}")
    else:
        defect = outcome.get("defect")
        if defect:
            with st.expander("Defect Capsule", expanded=True):
                st.json(defect)

# Run actions
if st.button("Run Builder"):
    result = handle_builder_run(selected_model, temperature)
    st.success("Builder complete")
    st.subheader("Builder Output")
    st.json(result)

    retrieved = result.get("retrieved_snippets") or []
    if retrieved:
        with st.expander("Retrieved Snippets"):
            for idx, snippet in enumerate(retrieved, start=1):
                st.markdown(f"**{idx}.** {snippet}")

if st.button("Run Verifier"):
    outcome = handle_verifier_run()
    show_verifier_details(outcome)
    if not outcome["pass"]:
        if st.button("Start Remediation Sprint", key="remediation_single"):
            start_remediation_sprint(outcome.get("defect") or {})

if st.button("Run Full Cycle (Builder → Verifier)"):
    builder_out = handle_builder_run(selected_model, temperature)
    st.subheader("Builder Output")
    st.json(builder_out)
    retrieved = builder_out.get("retrieved_snippets") or []
    if retrieved:
        with st.expander("Retrieved Snippets"):
            for idx, snippet in enumerate(retrieved, start=1):
                st.markdown(f"**{idx}.** {snippet}")

    outcome = handle_verifier_run()
    show_verifier_details(outcome)
    if not outcome["pass"]:
        if st.button("Start Remediation Sprint", key="remediation_full"):
            start_remediation_sprint(outcome.get("defect") or {})

# Make sure data directory exists
data_dir = Path("data")
data_dir.mkdir(parents=True, exist_ok=True)

ledger_path = data_dir / "ledger.db"


def ensure_ledger_schema():
    conn = sqlite3.connect(ledger_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger (
            id TEXT PRIMARY KEY,
            ts TEXT,
            phase TEXT,
            roadmap_key TEXT,
            synopsis TEXT,
            pass INTEGER,
            sha TEXT,
            defects TEXT,
            artifact_dir TEXT
        )
        """
    )
    try:
        conn.execute("ALTER TABLE ledger ADD COLUMN artifact_dir TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def create_run_id(prefix: str) -> str:
    return f"{utc_now().strftime('%Y%m%dT%H%M%S')}_{prefix}_{uuid.uuid4().hex[:6]}"


def save_builder_artifacts(result, baton_snapshot, model, temperature):
    run_id = create_run_id("builder")
    run_dir = HISTORY_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "builder_output.json").write_text(json.dumps(result, indent=2))
    (run_dir / "baton_snapshot.json").write_text(json.dumps(baton_snapshot, indent=2))
    (run_dir / "settings.json").write_text(json.dumps({"model": model, "temperature": temperature}, indent=2))
    for rel in ["runtime/builder_raw.json", "runtime/baton.next.json", "runtime/baton.json"]:
        src = Path(rel)
        if src.exists():
            shutil.copy2(src, run_dir / src.name)
    return run_id, str(run_dir)


def save_verifier_artifacts(outcome, baton_snapshot):
    run_id = create_run_id("verifier")
    run_dir = HISTORY_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "verifier_output.json").write_text(json.dumps(outcome, indent=2))
    (run_dir / "baton_snapshot.json").write_text(json.dumps(baton_snapshot, indent=2))
    for rel in ["runtime/defect.json", "runtime/checkpoint.json", "runtime/baton.next.json", "runtime/baton.json"]:
        src = Path(rel)
        if src.exists():
            shutil.copy2(src, run_dir / src.name)
    return run_id, str(run_dir)


def append_ledger_entry(run_id, phase, synopsis, passed=None, sha=None, defects=None, artifact_dir="", roadmap_key="manual"):
    ensure_ledger_schema()
    conn = sqlite3.connect(ledger_path)
    conn.execute(
        "INSERT OR REPLACE INTO ledger (id, ts, phase, roadmap_key, synopsis, pass, sha, defects, artifact_dir) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            to_iso(utc_now()),
            phase,
            roadmap_key,
            (synopsis or "")[:500],
            None if passed is None else int(bool(passed)),
            sha,
            json.dumps(defects or []),
            artifact_dir,
        ),
    )
    conn.commit()
    conn.close()


def handle_builder_run(model, temperature):
    current_baton = json.loads(baton_path.read_text())
    result = run_builder(model=model, temperature=temperature)
    run_id, artifact_dir = save_builder_artifacts(result, current_baton, model, temperature)
    roadmap_key = result.get("commit_suggestion") or current_baton.get("next_goal", "manual")
    append_ledger_entry(run_id, "builder", result.get("synopsis", ""), artifact_dir=artifact_dir, roadmap_key=roadmap_key)
    return result


def handle_verifier_run():
    current_baton = json.loads(baton_path.read_text())
    outcome = run_verifier()
    run_id, artifact_dir = save_verifier_artifacts(outcome, current_baton)
    defects_list = []
    if not outcome.get("pass") and outcome.get("defect"):
        defects_list = [outcome["defect"]]
    append_ledger_entry(
        run_id,
        "verifier",
        current_baton.get("synopsis", outcome.get("notes", "")),
        passed=outcome.get("pass"),
        sha=outcome.get("sha"),
        defects=defects_list,
        artifact_dir=artifact_dir,
        roadmap_key=current_baton.get("next_goal", "manual"),
    )
    return outcome


ensure_ledger_schema()

st.subheader("Ledger")
if ledger_path.exists():
    conn = sqlite3.connect(ledger_path)
    df = pd.read_sql_query("SELECT * FROM ledger ORDER BY ts DESC", conn)
    conn.close()
    if df.empty:
        st.info("Ledger will appear after the first run is logged.")
    else:
        if "artifact_dir" not in df.columns:
            df["artifact_dir"] = ""
        display_df = df.drop(columns=["artifact_dir"], errors="ignore")
        st.dataframe(display_df, use_container_width=True)

        option_labels = [
            f"{row['ts']} · {row['phase']} · {row['synopsis'][:60]}"
            for _, row in df.iterrows()
        ]
        selected_idx = st.selectbox("Inspect run", range(len(df)), format_func=lambda idx: option_labels[idx])
        selected_row = df.iloc[selected_idx]

        st.subheader("Run Details")
        details = {
            "timestamp": selected_row.get("ts"),
            "phase": selected_row.get("phase"),
            "roadmap_key": selected_row.get("roadmap_key"),
            "synopsis": selected_row.get("synopsis"),
            "pass": selected_row.get("pass"),
            "sha": selected_row.get("sha"),
            "defects": json.loads(selected_row.get("defects")) if selected_row.get("defects") else [],
        }
        st.json(details)

        artifact_dir = selected_row.get("artifact_dir")
        if artifact_dir and Path(artifact_dir).exists():
            st.subheader("Artifacts")
            for file_path in sorted(Path(artifact_dir).glob("*")):
                st.markdown(f"**{file_path.name}**")
                try:
                    st.json(json.loads(file_path.read_text()))
                except Exception:
                    st.code(file_path.read_text())
        else:
            st.info("No saved artifacts for this run.")
else:
    st.info("Ledger will appear after the first run is logged.")
