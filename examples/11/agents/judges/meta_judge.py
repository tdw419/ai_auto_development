import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from utils.llm_client import LLMClient

CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5-7b-instruct")


def _fallback_verdict(objective: Dict[str, Any], adversarial: Dict[str, Any]) -> Dict[str, Any]:
    objective_pass = objective.get("passed", False)
    adversarial_severity = adversarial.get("severity", "low")
    passed = objective_pass and adversarial_severity != "high"

    defect = None
    if not passed:
        defect = {
            "title": "Verification failed",
            "repro_steps": ["Review objective report", "Review adversarial findings"],
            "observations": f"Objective passed: {objective_pass}, Adversarial severity: {adversarial_severity}",
            "suspected_files": [],
            "test_suggestion": "Add comprehensive regression coverage",
            "severity": "high" if not objective_pass else adversarial_severity,
        }

    return {
        "pass": passed,
        "defect": defect,
        "reasoning": "Fallback logic based on objective/adversarial outcomes",
        "confidence": 0.3,
        "fallback": True,
    }


def run_meta_judge(
    objective_report: Dict[str, Any],
    adversarial_report: Dict[str, Any],
    baton: Dict[str, Any],
    model: str = CHAT_MODEL,
) -> Dict[str, Any]:
    prompt_path = Path("prompts/judge.meta.txt")
    if not prompt_path.exists():
        return _fallback_verdict(objective_report, adversarial_report)

    task = baton.get("task", {})
    output = baton.get("builder_output", {})

    template = prompt_path.read_text()
    user_prompt = (
        template.replace("{{objective_report}}", json.dumps(objective_report, indent=2))
        .replace("{{adversarial_report}}", json.dumps(adversarial_report, indent=2))
        .replace("{{success_metrics}}", json.dumps(task.get("success_metrics", []), indent=2))
        .replace("{{task_goal}}", task.get("goal", "unknown goal"))
        .replace("{{builder_synopsis}}", output.get("synopsis", ""))
        .replace("{{open_issues}}", json.dumps(output.get("open_issues", []), indent=2))
    )

    try:
        client = LLMClient(model=model)
        response = client.generate_structured_response(
            prompt=user_prompt,
            system_message="You are the final arbiter combining objective tests and adversarial critique.",
            temperature=0.0,
            response_format="json",
        )
        if response.get("fallback"):
            return _fallback_verdict(objective_report, adversarial_report)
        return _normalize_meta_verdict(response)
    except Exception:
        return _fallback_verdict(objective_report, adversarial_report)


def _normalize_meta_verdict(data: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(data)

    if "pass" not in data:
        data["pass"] = False
    if "defect" not in data:
        data["defect"] = None
    if "reasoning" not in data:
        data["reasoning"] = "No reasoning provided"
    if "confidence" not in data:
        data["confidence"] = 0.5

    defect = data.get("defect")
    if defect:
        defect.setdefault("repro_steps", ["Unable to reproduce"])
        defect.setdefault("observations", "No observations provided")
        defect.setdefault("suspected_files", [])
        defect.setdefault("test_suggestion", "Add regression test")
        defect.setdefault("severity", "medium")

    return data


def calculate_meta_confidence(meta_verdict: Dict[str, Any]) -> float:
    base = meta_verdict.get("confidence", 0.5)
    reasoning = meta_verdict.get("reasoning", "")
    reasoning_bonus = min(0.3, len(reasoning) / 200.0)
    final = min(1.0, max(0.0, base + reasoning_bonus))
    return final
