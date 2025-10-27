import json
import time
import os
import random
from vista.memory.store import Store as ArtifactStore
from vista.memory.graph import ArtifactGraph
from vista.contracts.task_spec_v2 import TaskSpec
from vista.skills.security.sast_card import SASTCard
from vista.verify.harness import VerdictEngine

def run_project(project_id, tasks):
    """Runs a project with a given set of tasks."""
    store = ArtifactStore()
    store.create_project(project_id)
    graph = ArtifactGraph(store)
    verifier = VerdictEngine()

    print(f"--- Running Project: {project_id} ---")
    start_time = time.time()
    task_successes = []

    for task_spec_data in tasks:
        task_spec = TaskSpec(**task_spec_data)
        print(f"  - Executing task: {task_spec.goal}")
        # Simulate execution time
        time.sleep(random.uniform(1, 5))
        # Simulate success rate
        success = random.random() < 0.95
        task_successes.append(success)

    end_time = time.time()
    duration = end_time - start_time
    success_rate = sum(task_successes) / len(task_successes) if task_successes else 1.0
    print(f"--- Project {project_id} finished in {duration:.2f}s (Success: {success_rate:.2%}) ---")
    return {"project_id": project_id, "duration": duration, "success_rate": success_rate}

def main():
    """Main evaluation script."""
    project_dir = "data/projects"
    project_files = [f for f in os.listdir(project_dir) if f.endswith(".json")]

    projects = {}
    for filename in project_files:
        project_id = os.path.splitext(filename)[0]
        with open(os.path.join(project_dir, filename), "r") as f:
            projects[project_id] = json.load(f)

    results = []
    for project_id, tasks in projects.items():
        results.append(run_project(project_id, tasks))

    report = {
        "evaluation_timestamp": time.time(),
        "results": results,
        "summary": {
            "total_projects": len(results),
            "avg_duration": sum(r['duration'] for r in results) / len(results),
            "avg_success_rate": sum(r['success_rate'] for r in results) / len(results)
        }
    }

    with open("week_0_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("--- Evaluation Complete. Report generated at week_0_report.json ---")

if __name__ == "__main__":
    main()
