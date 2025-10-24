#!/usr/bin/env python3
"""
Implements the six-step deep thinking remediation prompt.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


def run_deep_thinking_process(
    defect_capsule: Dict[str, Any],
    task_context: Dict[str, Any],
    historical_context: str = "",
    attempt_count: int = 1,
) -> Dict[str, Any]:
    """Execute 6-step reasoning; fall back to deterministic plan if LLM fails."""
    prompt = _build_prompt(defect_capsule, task_context, historical_context, attempt_count)
    client = LLMClient()

    try:
        result = client.generate_structured_response(
            prompt=prompt,
            system_message="You are a senior engineer performing post-mortem remediation planning.",
            response_format="json",
            temperature=0.2,
        )
        if result.get("fallback"):
            return _fallback_plan(defect_capsule)
        return _ensure_schema(result)
    except Exception as exc:
        logger.warning("Deep thinking process failed: %s", exc)
        return _fallback_plan(defect_capsule)


def _build_prompt(
    defect: Dict[str, Any],
    task: Dict[str, Any],
    history: str,
    attempt: int,
) -> str:
    return f"""
# DEFECT REMEDIATION — ATTEMPT {attempt}

## DEFECT CAPSULE
Title: {defect.get('title', 'Unknown defect')}
Severity: {defect.get('severity', 'medium')}
Reproduction Steps: {json.dumps(defect.get('repro_steps', []), indent=2)}
Observations: {defect.get('observations', 'None')}
Suspected Files: {json.dumps(defect.get('suspected_files', []), indent=2)}

## ORIGINAL TASK
Goal: {task.get('goal', 'No goal provided')}
Constraints: {json.dumps(task.get('constraints', []), indent=2)}
Success Metrics: {json.dumps(task.get('success_metrics', []), indent=2)}

## HISTORICAL CONTEXT
{history or 'No historical matches.'}

Provide a JSON object with 6 sections, following this schema:
{{
  "step1_acknowledge_failure": {{
    "specific_failures": ["..."],
    "constraints_violated": ["..."],
    "error_patterns": ["..."]
  }},
  "step2_clarify_goal": {{
    "fundamental_objective": "...",
    "requirements_clarification": "...",
    "success_criteria": ["..."]
  }},
  "step3_conflict_detection": {{
    "root_cause_analysis": "...",
    "requirement_conflicts": ["..."],
    "historical_insights": "..."
  }},
  "step4_propose_fix": {{
    "specific_changes": ["..."],
    "files_to_modify": ["..."],
    "root_cause_solution": "..."
  }},
  "step5_risk_analysis": {{
    "potential_risks": ["..."],
    "side_effects": ["..."],
    "risk_mitigation": ["..."]
  }},
  "step6_validation_plan": {{
    "verification_methods": ["..."],
    "new_tests_required": ["..."],
    "regression_prevention": ["..."]
  }},
  "confidence": 0.75,
  "summary": "Brief summary of remediation approach."
}}
"""


def _ensure_schema(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all required sections exist."""
    required_sections = [
        "step1_acknowledge_failure",
        "step2_clarify_goal",
        "step3_conflict_detection",
        "step4_propose_fix",
        "step5_risk_analysis",
        "step6_validation_plan",
    ]
    for section in required_sections:
        plan.setdefault(section, {})
    plan.setdefault("confidence", 0.5)
    plan.setdefault("summary", "Automated remediation plan.")
    return plan


def _fallback_plan(defect: Dict[str, Any]) -> Dict[str, Any]:
    """Return deterministic plan when LLM unavailable."""
    files = defect.get("suspected_files", ["UNKNOWN"])
    return {
        "fallback": True,
        "step1_acknowledge_failure": {
            "specific_failures": [defect.get("observations", "Undiagnosed failure")],
            "constraints_violated": [],
            "error_patterns": [],
        },
        "step2_clarify_goal": {
            "fundamental_objective": f"Resolve defect: {defect.get('title', 'unknown')}",
            "requirements_clarification": "Ensure fix aligns with original constraints.",
            "success_criteria": ["All tests pass", "Defect reproduction steps succeed"],
        },
        "step3_conflict_detection": {
            "root_cause_analysis": "Requires manual analysis.",
            "requirement_conflicts": [],
            "historical_insights": "No data available.",
        },
        "step4_propose_fix": {
            "specific_changes": ["Review suspected files and implement targeted fix."],
            "files_to_modify": files,
            "root_cause_solution": "Apply minimal change to address failure point.",
        },
        "step5_risk_analysis": {
            "potential_risks": ["Risk of regression", "Unintended side effects"],
            "side_effects": [],
            "risk_mitigation": ["Add regression tests", "Perform code review"],
        },
        "step6_validation_plan": {
            "verification_methods": ["Run full verification suite", "Manual QA if needed"],
            "new_tests_required": ["Add regression test covering failure path"],
            "regression_prevention": ["Document fix and add monitoring if applicable"],
        },
        "confidence": 0.3,
        "summary": "Fallback remediation plan requiring manual validation.",
    }
