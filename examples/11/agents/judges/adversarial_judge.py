import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple

from utils.llm_client import LLMClient

CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5-7b-instruct")


def _fallback_result(reason: str) -> Dict[str, Any]:
    return {
        "attack_vectors": [reason],
        "security_risks": ["adversarial judge unavailable"],
        "missing_tests": [],
        "architecture_concerns": [],
        "severity": "low",
        "confidence": 0.1,
        "fallback": True,
    }


def _normalize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if data.get("fallback"):
        return _fallback_result("LLM fallback response")

    for key in ["attack_vectors", "security_risks", "missing_tests", "architecture_concerns"]:
        if key not in data or not isinstance(data[key], list):
            data[key] = []
    if data.get("severity") not in {"low", "medium", "high"}:
        data["severity"] = "low"
    if "confidence" not in data:
        data["confidence"] = 0.5
    return data


def run_adversarial_judge(baton: Dict[str, Any], model: str = CHAT_MODEL) -> Dict[str, Any]:
    prompt_path = Path("prompts/judge.adversarial.txt")
    if not prompt_path.exists():
        return _fallback_result("missing adversarial prompt")

    task = baton.get("task", {})
    output = baton.get("builder_output", {})

    prompt = prompt_path.read_text()
    prompt = (
        prompt.replace("{{task_goal}}", task.get("goal", "unknown goal"))
        .replace("{{synopsis}}", output.get("synopsis", ""))
        .replace("{{patch_bundle}}", json.dumps(output.get("patch_bundle", []), indent=2))
        .replace("{{verification_hints}}", json.dumps(output.get("verification_hints", []), indent=2))
    )

    try:
        client = LLMClient(model=model)
        response = client.generate_structured_response(
            prompt=prompt,
            system_message="You are a ruthless, precise adversarial reviewer.",
            temperature=0.1,
            response_format="json",
        )
        return _normalize_response(response)
    except Exception as exc:
        return _fallback_result(str(exc))


def calculate_adversarial_score(result: Dict[str, Any]) -> Tuple[bool, float]:
    severity_weight = {"low": 0, "medium": 0.3, "high": 1.0}.get(result.get("severity", "low"), 0)
    total_findings = (
        len(result.get("attack_vectors", []))
        + len(result.get("security_risks", []))
        + len(result.get("architecture_concerns", []))
    )
    base = max(0.0, 1.0 - (severity_weight + 0.1 * total_findings))
    confidence = result.get("confidence", 0.5)
    score = max(0.0, min(1.0, base * confidence))
    passed = result.get("severity") != "high" and total_findings <= 2
    return passed, score
