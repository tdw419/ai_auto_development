#!/usr/bin/env python3
"""
VISTA V-Loop Command Line Interface
"""
import argparse
import json
import sys
from .memory.store import Store as ArtifactStore
from .memory.graph import ArtifactGraph
from .contracts.task_spec_v2 import TaskSpec
from .skills.security.sast_card import SASTCard
from .verify.harness import VerdictEngine
from .runners.context import RunnerRegistry
from .memory.store import Store

def cmd_scan(args):
    """Run security scan and verification"""
    store = ArtifactStore()
    g = ArtifactGraph(store)
    g.sync_from_store(args.project)

    task = TaskSpec(
        task_id=args.task_id,
        project_id=args.project,
        role="security",
        goal="Security scan via CLI",
        inputs={"code_artifacts": args.code_artifacts},
        deliverables=["security_report.json"],
        acceptance=args.acceptance
    )

    print(f"🔍 Running SAST scan for project: {args.project}")
    report = SASTCard().run(task, g)
    store.put(report)
    g.sync_from_store(args.project)

    print("✅ Scan complete. Running verification...")
    out = VerdictEngine().verify(report, task, g)

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        status = "PASS" if out["pass"] else "FAIL"
        print(f"\n📊 VERDICT: {status}")
        print(f"📈 Overall Score: {out['overall_score']}")
        print(f"👥 Required Judges: {', '.join(out['required_judges'])}")
        print(f"🏃 Runner: {out['runner_id']}")

        for result in out["results"]:
            judge_status = "✅" if result["pass"] else "❌"
            print(f"  {judge_status} {result['judge']}: {result['score']:.2f}")

def cmd_runners(args):
    """List available runners"""
    runners = RunnerRegistry.list_runners()
    if runners:
        print("🏃 Available Runners:")
        for runner_id, runner_type in runners.items():
            print(f"  {runner_id}: {runner_type}")
    else:
        print("❌ No runners registered")

def cmd_projects(args):
    """List projects in database"""
    proj = Store().list_projects()
    if not proj: print("📂 No projects yet."); return
    print("📂 Projects:"); [print(f"  • {p}") for p in proj]

def main():
    parser = argparse.ArgumentParser(description="VISTA V-Loop - Autonomous AI Development System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Run security scan and verification")
    scan_parser.add_argument("--project", required=True, help="Project ID")
    scan_parser.add_argument("--task-id", default="security_scan_cli", help="Task ID")
    scan_parser.add_argument("--code-artifacts", nargs="*", default=[], help="Code artifact IDs to scan")
    scan_parser.add_argument("--acceptance", nargs="*", default=["No critical vulnerabilities found"], help="Acceptance criteria")
    scan_parser.add_argument("--json", action="store_true", help="Output as JSON")
    scan_parser.set_defaults(func=cmd_scan)

    # Runners command
    runners_parser = subparsers.add_parser("runners", help="List available runners")
    runners_parser.set_defaults(func=cmd_runners)

    # Projects command
    projects_parser = subparsers.add_parser("projects", help="List projects")
    projects_parser.set_defaults(func=cmd_projects)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
