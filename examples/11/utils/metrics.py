"""Performance metrics for the VISTA verification loop."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import sqlite3

from utils.ledger import get_verification_history, calculate_ars_score


def collect_metrics(limit: int = 200) -> Dict[str, Any]:
    """Return high-level metrics derived from the verification ledger."""
    metrics: Dict[str, Any] = {
        "total_verifications": 0,
        "successful_verifications": 0,
        "failed_verifications": 0,
        "success_rate": 0.0,
        "average_confidence": 0.0,
        "ars_score": 1.0,
        "recent_failures": [],
    }

    try:
        history = get_verification_history(limit=limit)
    except Exception:
        history = []

    total = len(history)
    if total == 0:
        return metrics

    successes = sum(1 for rec in history if rec.get("meta_decision") == "SUCCESS")
    confidence_sum = sum(rec.get("confidence", 0.0) for rec in history)

    metrics["total_verifications"] = total
    metrics["successful_verifications"] = successes
    metrics["failed_verifications"] = total - successes
    metrics["success_rate"] = successes / total if total else 0.0
    metrics["average_confidence"] = confidence_sum / total if total else 0.0

    try:
        metrics["ars_score"] = calculate_ars_score()
    except Exception:
        metrics["ars_score"] = 1.0

    recent_failures: List[Dict[str, Any]] = []
    for rec in history:
        if rec.get("meta_decision") != "SUCCESS" and rec.get("defect_capsule"):
            capsule = rec.get("defect_capsule")
            if isinstance(capsule, str):
                # already deserialized in ledger utils, but guard anyway
                try:
                    import json

                    capsule = json.loads(capsule)
                except Exception:
                    capsule = {"title": capsule}
            recent_failures.append(
                {
                    "timestamp": rec.get("timestamp"),
                    "title": capsule.get("title", "Unknown defect"),
                    "severity": capsule.get("severity", "unknown"),
                }
            )

    metrics["recent_failures"] = recent_failures[:5]
    return metrics
