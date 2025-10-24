#!/usr/bin/env python3
"""
Three-judge verifier orchestrator for the VISTA V-loop.
"""
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agents.judges.probing_judge import run_probing_judge
from agents.judges.adversarial_judge import run_adversarial_judge
from agents.judges.meta_judge import run_meta_judge
from utils.ledger import update_verification_ledger
from utils.intelligent_cache import get_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class VerifierOrchestrator:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.cache = get_cache()

    def run(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Running three-judge verification pipeline")

        baton = self._load_baton()

        result: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": baton.get("task", {}).get("id") or task_context.get("task_id", "unknown"),
            "judges": {},
            "final_verdict": None,
            "defect_capsule": None,
            "confidence": 0.0,
            "errors": [],
        }

        # Probing Judge
        logger.info("1) Probing judge")
        probing = run_probing_judge(self.workspace, task_context)
        result["judges"]["probing"] = probing
        if probing.get("error"):
            result["errors"].append(probing["error"])

        # Adversarial Judge
        logger.info("2) Adversarial judge")
        adversarial = run_adversarial_judge(baton)
        result["judges"]["adversarial"] = adversarial
        if adversarial.get("fallback"):
            result["errors"].append("Adversarial judge used fallback logic")

        # Meta Judge
        logger.info("3) Meta judge")
        meta = run_meta_judge(probing, adversarial, baton)
        result["judges"]["meta"] = meta
        result["final_verdict"] = meta.get("pass")
        result["defect_capsule"] = meta.get("defect")
        result["confidence"] = meta.get("confidence", 0.0)
        if meta.get("fallback"):
            result["errors"].append("Meta judge used fallback logic")

        self._log_summary(result)
        self._record_ledger(result)
        self._cache_result(result, baton)
        return result

    def _load_baton(self) -> Dict[str, Any]:
        baton_path = self.workspace / "runtime" / "baton.next.json"
        if not baton_path.exists():
            raise FileNotFoundError(f"Baton not found: {baton_path}")
        return json.loads(baton_path.read_text())

    def _log_summary(self, result: Dict[str, Any]) -> None:
        verdict = "SUCCESS" if result["final_verdict"] else "FAILURE"
        logger.info("Verification summary")
        logger.info("  verdict     : %s", verdict)
        logger.info("  confidence  : %.2f", result.get("confidence", 0.0))
        logger.info("  errors      : %d", len(result.get("errors", [])))

    def _record_ledger(self, result: Dict[str, Any]) -> None:
        try:
            ledger_entry = {
                "task_id": result["task_id"],
                "timestamp": result["timestamp"],
                "objective_pass": result["judges"]["probing"].get("overall_pass", False),
                "adversarial_severity": result["judges"]["adversarial"].get("severity", "low"),
                "meta_decision": "SUCCESS" if result["final_verdict"] else "FAILURE",
                "defect_capsule": result.get("defect_capsule"),
                "confidence": result.get("confidence", 0.0),
                "errors": result.get("errors", []),
                "adversarial_findings": [
                    {
                        "type": "attack_vector",
                        "description": item,
                        "severity": result["judges"]["adversarial"].get("severity", "low"),
                    }
                    for item in result["judges"]["adversarial"].get("attack_vectors", [])
                ],
            }
            update_verification_ledger(ledger_entry)
        except Exception as exc:
            logger.warning("Failed to record verification ledger: %s", exc)

    def _cache_result(self, result: Dict[str, Any], baton: Dict[str, Any]) -> None:
        """Persist verification result in cache for quick reuse and UI stats."""
        try:
            builder_snapshot = baton.get("builder_output")
            if builder_snapshot is None:
                builder_snapshot = {
                    "synopsis": baton.get("synopsis"),
                    "commit_suggestion": baton.get("commit_suggestion"),
                    "open_issues": baton.get("open_issues"),
                }
            cache_source = {
                "task_id": result.get("task_id"),
                "builder": builder_snapshot,
            }
            cache_key = hashlib.md5(json.dumps(cache_source, sort_keys=True).encode()).hexdigest()
            metadata = {
                "goal": baton.get("task", {}).get("goal"),
                "timestamp": result.get("timestamp"),
                "final_verdict": result.get("final_verdict"),
            }
            self.cache.store_verification_result(
                cache_key,
                result,
                task_id=result.get("task_id"),
                metadata=metadata,
            )
        except Exception as exc:
            logger.debug("Unable to cache verification result: %s", exc)


def run_verifier(task_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience wrapper returning simplified outcome used by other agents."""
    orchestrator = VerifierOrchestrator(Path("."))
    result = orchestrator.run(task_context or {})

    simplified = {
        "pass": bool(result.get("final_verdict")),
        "confidence": result.get("confidence", 0.0),
        "defect": result.get("defect_capsule"),
        "probing": result["judges"].get("probing"),
        "adversarial": result["judges"].get("adversarial"),
        "meta": result["judges"].get("meta"),
        "timestamp": result.get("timestamp"),
    }

    # Surface git checkpoint if available
    checkpoint_path = Path("runtime/checkpoint.json")
    if simplified["pass"] and checkpoint_path.exists():
        try:
            simplified["sha"] = json.loads(checkpoint_path.read_text()).get("sha")
        except Exception:
            simplified["sha"] = None

    return simplified


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the VISTA verifier orchestrator.")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--task-json", help="Optional task context JSON file")
    parser.add_argument("--output", help="Optional output path for verification result")
    args = parser.parse_args()

    task_context: Dict[str, Any] = {}
    if args.task_json:
        task_path = Path(args.task_json)
        if task_path.exists():
            text = task_path.read_text().strip()
            if text:
                task_context = json.loads(text)

    orchestrator = VerifierOrchestrator(Path(args.workspace))
    result = orchestrator.run(task_context)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
        print(f"Verification result saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result["final_verdict"] else 1)


if __name__ == "__main__":
    main()
