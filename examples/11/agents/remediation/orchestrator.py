#!/usr/bin/env python3
"""
High-level remediation orchestration using deep thinking reasoning.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from agents.remediation.deep_thinking import run_deep_thinking_process
from schemas.task_models import AgentContext, TaskObject
from utils.rag_history import search_similar_defects, store_remediation_pattern
from utils.time_utils import format_duration, to_iso, utc_now

logger = logging.getLogger(__name__)


class RemediationOrchestrator:
    """Create remediation baton after verification failure."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.attempt_limit = 3

    def generate_remediation_baton(
        self,
        verification_result: Dict[str, Any],
        last_baton: Dict[str, Any],
    ) -> Dict[str, Any]:
        started_at = to_iso(utc_now())
        defect = verification_result.get("defect") or {}
        task_data = last_baton.get("task") or {}
        original_task = TaskObject(**task_data) if task_data else TaskObject(goal="Fix defect")

        attempt = verification_result.get("attempt", 1)
        history = search_similar_defects(defect, limit=3)
        historical_context = self._summarize_history(history)

        plan = run_deep_thinking_process(
            defect_capsule=defect,
            task_context=original_task.dict(),
            historical_context=historical_context,
            attempt_count=attempt,
        )

        if not plan.get("fallback"):
            store_remediation_pattern(defect, plan)

        remediation_task = self._build_remediation_task(original_task, defect, plan, attempt)
        baton = remediation_task.to_baton_format()
        baton["task"]["remediation_plan"] = plan
        baton["synopsis"] = plan.get("summary", "Remediation plan ready.")
        baton["open_issues"] = [defect]
        baton["next_goal"] = remediation_task.goal
        baton["remediation_meta"] = {
            "attempt": attempt,
            "started_at": started_at,
            "completed_at": to_iso(utc_now()),
            "elapsed": format_duration(started_at),
        }
        return baton

    def _summarize_history(self, history: list) -> str:
        if not history:
            return "No similar historical defects found."
        lines = ["Similar historical defect patterns:"]
        for entry in history[:3]:
            defect = entry.get("defect_data", {})
            strategy = entry.get("resolution_strategy", {})
            lines.append(f"- {defect.get('title', 'Unknown defect')} (success={entry.get('resolved')})")
            summary = strategy.get("summary")
            if summary:
                lines.append(f"  Summary: {summary}")
        return "\n".join(lines)

    def _build_remediation_task(
        self,
        original_task: TaskObject,
        defect: Dict[str, Any],
        plan: Dict[str, Any],
        attempt: int,
    ) -> TaskObject:
        goal = f"Remediate: {defect.get('title', 'Defect')} (attempt {attempt})"
        constraints = list(original_task.constraints)
        constraints.append("Follow remediation plan summary.")
        constraints.append("Ensure reproduction steps now succeed.")

        success_metrics = list(original_task.success_metrics)
        success_metrics.append("All reproduction steps pass")
        success_metrics.append("New regression tests succeed")

        context = original_task.agent_context
        retrieval_keys = list(context.retrieval_keys or [])
        retrieval_keys.extend(["remediation", defect.get("title", "")])

        agent_context = AgentContext(
            previous_synopsis=plan.get("summary", context.previous_synopsis),
            open_issues=[defect],
            retrieval_keys=retrieval_keys,
            commit_reference=context.commit_reference,
        )

        task = TaskObject(
            goal=goal,
            constraints=constraints,
            success_metrics=success_metrics,
            output_contract=original_task.output_contract,
            agent_context=agent_context,
            allowed_tools=original_task.allowed_tools,
            duration_minutes=max(10, min(30, original_task.duration_minutes + 5)),
        )
        return task
