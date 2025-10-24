import subprocess
from pathlib import Path
from typing import Dict, Any, List
import json
import shlex


def run_probing_judge(workspace_dir: Path, task_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run enhanced verification script to gather objective test results.
    Returns structured report with pass/fail and detailed diagnostics.
    """
    script_path = workspace_dir / "scripts" / "verify_enhanced.sh"
    if not script_path.exists():
        return {
            "overall_pass": False,
            "error": f"Verification script not found: {script_path}",
            "test_results": [],
            "raw_output": "",
        }

    try:
        proc = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(workspace_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
        output = proc.stdout
        passed = proc.returncode == 0

        test_results = _extract_test_results(output)

        return {
            "overall_pass": passed,
            "test_results": test_results,
            "raw_output": output,
            "return_code": proc.returncode,
        }
    except Exception as exc:
        return {
            "overall_pass": False,
            "error": str(exc),
            "test_results": [],
            "raw_output": "",
        }


def _extract_test_results(output: str) -> List[Dict[str, Any]]:
    """
    Parse script output and produce structured test results.
    Looks for lines beginning with PASS/FAIL/WARN indicators.
    """
    results: List[Dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("✅ PASS:"):
            results.append({"status": "PASS", "message": line[8:].strip()})
        elif line.startswith("❌ FAIL:"):
            results.append({"status": "FAIL", "message": line[8:].strip()})
        elif line.startswith("⚠️  WARN:"):
            results.append({"status": "WARN", "message": line[8:].strip()})
    return results
