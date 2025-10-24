#!/usr/bin/env python3
"""Legacy CLI entry point with timezone-aware logging."""
from __future__ import annotations

import sys
from pathlib import Path


def _setup_paths() -> None:
    """Ensure local modules resolve regardless of working directory."""
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    repo_root = current_dir.parents[2] if len(current_dir.parents) > 2 else current_dir.parent
    examples_dir = repo_root / "examples"
    for candidate in (repo_root, examples_dir, current_dir.parent):
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


_setup_paths()

from path_shim import get_current_utc_time, to_iso_format  # noqa: E402
from agents import run_agent_workflow  # noqa: E402
from db_manager import LanceDBManager  # noqa: E402


def main() -> int:
    print("VISTA Legacy CLI (timezone-aware)")
    print(f"Started at: {to_iso_format(get_current_utc_time())}")

    try:
        LanceDBManager()

        result = run_agent_workflow({"task": "legacy_cli_demo"})
        print("Workflow result:")
        print(result)
        print(f"Completed at: {to_iso_format(get_current_utc_time())}")
        return 0
    except Exception as exc:  # pragma: no cover - runtime diagnostics
        print(f"CLI execution failed: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover - manual run
    sys.exit(main())
