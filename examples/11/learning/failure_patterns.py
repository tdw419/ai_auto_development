#!/usr/bin/env python3
"""
VISTA Failure Pattern Recognition Engine

Identifies systemic verification failure patterns and estimates risk for new tasks.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.time_utils import to_iso, utc_now

logger = logging.getLogger(__name__)

LEDGER_DB_PATH = Path("data/verification_ledger.db")


class FailurePatternAnalyzer:
    """Analyse verification history and predict risk for upcoming tasks."""

    def __init__(self, ledger_path: Optional[Path] = None) -> None:
        self.ledger_path = ledger_path or LEDGER_DB_PATH

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze_verification_history(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Return pattern analysis for recent verification history."""
        try:
            records = self._load_verification_records(lookback_days)
        except Exception as exc:
            logger.error("Failure analysis error: %s", exc)
            return self._error_result(str(exc))

        if not records:
            return self._empty_result()

        summary = self._compute_summary(records)
        clusters = self._cluster_failures(records)
        temporal = self._temporal_patterns(records)
        risks = self._risk_factors(records)

        recommendations = self._recommendations(summary, clusters)

        return {
            "summary": summary,
            "pattern_clusters": clusters,
            "temporal_trends": temporal,
            "risk_factors": risks,
            "recommendations": recommendations,
        }

    def predict_failure_risk(self, task_object: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate failure risk for a pending task."""
        risk_factors: List[Dict[str, Any]] = []

        complexity = self._task_complexity(task_object)
        if complexity > 0.3:
            risk_factors.append(
                {
                    "factor": "complexity",
                    "score": complexity,
                    "description": "High number of constraints or strict output requirements.",
                }
            )

        similarity = self._similarity_to_known_failures(task_object)
        if similarity > 0.2:
            risk_factors.append(
                {
                    "factor": "similar_to_past_failures",
                    "score": similarity,
                    "description": "Task resembles previously failed efforts.",
                }
            )

        overall = min(1.0, complexity * 0.5 + similarity * 0.5)
        confidence = 0.6 + 0.1 * bool(task_object.get("success_metrics"))

        return {
            "task_id": task_object.get("id", "unknown"),
            "overall_risk": overall,
            "confidence": min(confidence, 0.95),
            "risk_factors": sorted(risk_factors, key=lambda x: x["score"], reverse=True),
            "timestamp": to_iso(utc_now()),
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _load_verification_records(self, lookback_days: int) -> List[Dict[str, Any]]:
        if not self.ledger_path.exists():
            logger.warning("Ledger database not found at %s", self.ledger_path)
            return []

        cutoff_time = utc_now() - timedelta(days=lookback_days)
        cutoff = to_iso(cutoff_time)
        conn = sqlite3.connect(self.ledger_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT vr.*, af.finding_type, af.description, af.severity
            FROM verification_records vr
            LEFT JOIN adversarial_findings af ON vr.id = af.verification_id
            WHERE vr.timestamp > ?
            ORDER BY vr.timestamp DESC
            """,
            (cutoff,),
        )

        records: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None

        for row in cursor.fetchall():
            row_dict = dict(row)
            if current is None or current["id"] != row_dict["id"]:
                if current:
                    records.append(current)
                current = {
                    "id": row_dict["id"],
                    "task_id": row_dict["task_id"],
                    "timestamp": row_dict["timestamp"],
                    "objective_pass": bool(row_dict["objective_pass"]),
                    "meta_decision": row_dict["meta_decision"],
                    "adversarial_severity": row_dict["adversarial_severity"],
                    "confidence": row_dict["confidence"] or 0.0,
                    "defect_capsule": json.loads(row_dict["defect_capsule"]) if row_dict["defect_capsule"] else None,
                    "errors": json.loads(row_dict["errors"]) if row_dict["errors"] else [],
                    "adversarial_findings": [],
                }
            if current and row_dict["finding_type"]:
                current["adversarial_findings"].append(
                    {
                        "type": row_dict["finding_type"],
                        "description": row_dict["description"],
                        "severity": row_dict["severity"],
                    }
                )

        if current:
            records.append(current)

        conn.close()
        return records

    def _compute_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(records)
        successes = sum(1 for r in records if r["meta_decision"] == "SUCCESS")
        objective_passes = sum(1 for r in records if r["objective_pass"])
        discrepancies = sum(1 for r in records if r["objective_pass"] != (r["meta_decision"] == "SUCCESS"))
        average_confidence = sum(r["confidence"] for r in records) / total if total else 0.0

        ars = 1.0 - (discrepancies / total) if total else 1.0

        return {
            "total_verifications": total,
            "success_rate": successes / total if total else 0.0,
            "failure_rate": 1 - successes / total if total else 0.0,
            "objective_pass_rate": objective_passes / total if total else 0.0,
            "adversarial_resilience_score": ars,
            "average_confidence": average_confidence,
            "discrepancy_rate": discrepancies / total if total else 0.0,
        }

    def _cluster_failures(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        failures = [r for r in records if r["meta_decision"] != "SUCCESS"]
        clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for record in failures:
            capsule = record.get("defect_capsule") or {}
            primary_type = self._classify_defect(capsule, record["adversarial_findings"])
            severity = capsule.get("severity", record.get("adversarial_severity", "medium"))
            cluster_key = f"{primary_type}:{severity}"
            clusters[cluster_key].append({"record": record, "capsule": capsule})

        results: List[Dict[str, Any]] = []
        for key, members in clusters.items():
            if len(members) < 2:
                continue
            primary_type, severity = key.split(":")
            common_files = self._common_files(members)
            results.append(
                {
                    "cluster_id": key,
                    "primary_type": primary_type,
                    "severity": severity,
                    "frequency": len(members),
                    "common_files": common_files,
                    "examples": [self._summarize_defect(m["record"]) for m in members[:3]],
                    "recurrence_rate": len(members) / len(failures) if failures else 0.0,
                }
            )

        return sorted(results, key=lambda item: item["frequency"], reverse=True)

    def _temporal_patterns(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        hourly_totals: Dict[int, int] = defaultdict(int)
        hourly_failures: Dict[int, int] = defaultdict(int)

        for record in records:
            try:
                hour = datetime.fromisoformat(record["timestamp"]).hour
            except ValueError:
                continue
            hourly_totals[hour] += 1
            if record["meta_decision"] != "SUCCESS":
                hourly_failures[hour] += 1

        rates = {
            hour: (hourly_failures.get(hour, 0) / hourly_totals[hour]) if hourly_totals.get(hour) else 0.0
            for hour in range(24)
        }
        peak_hours = sorted(rates.items(), key=lambda item: item[1], reverse=True)[:3]
        return {"hourly_failure_rates": rates, "peak_failure_hours": peak_hours}

    def _risk_factors(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        factors: List[Dict[str, Any]] = []

        high_severity = [r for r in records if r["adversarial_severity"] in {"high", "critical"}]
        if high_severity:
            failure_ratio = sum(r["meta_decision"] != "SUCCESS" for r in high_severity) / len(high_severity)
            factors.append(
                {
                    "factor": "high_severity_adversarial",
                    "risk_rate": failure_ratio,
                    "description": "High/critical adversarial findings often lead to failure.",
                }
            )

        low_confidence = [r for r in records if r["confidence"] < 0.7]
        if low_confidence:
            failure_ratio = sum(r["meta_decision"] != "SUCCESS" for r in low_confidence) / len(low_confidence)
            factors.append(
                {
                    "factor": "low_verification_confidence",
                    "risk_rate": failure_ratio,
                    "description": "Low judge confidence correlates with failures.",
                }
            )

        return sorted(factors, key=lambda item: item["risk_rate"], reverse=True)

    def _recommendations(self, summary: Dict[str, Any], clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []
        success_rate = summary.get("success_rate", 0)
        ars = summary.get("adversarial_resilience_score", 1)

        if success_rate < 0.75:
            recs.append(
                {
                    "type": "quality_improvement",
                    "priority": "high",
                    "description": f"Success rate is {success_rate:.1%}. Reinforce builder prompts and training.",
                    "action": "Review recurring failure clusters to strengthen builder reasoning.",
                }
            )
        if ars < 0.9:
            recs.append(
                {
                    "type": "security_improvement",
                    "priority": "medium",
                    "description": f"Adversarial resilience score is {ars:.3f}.",
                    "action": "Augment adversarial prompts with targeted attack scenarios.",
                }
            )

        for cluster in clusters[:3]:
            recs.append(
                {
                    "type": "pattern_specific",
                    "priority": "medium",
                    "description": f"Recurring pattern: {cluster['primary_type']} (×{cluster['frequency']})",
                    "action": "Introduce specialised remediation template for this defect category.",
                }
            )
        return recs

    # ------------------------------------------------------------------ #
    # Helper computations
    # ------------------------------------------------------------------ #
    def _classify_defect(self, capsule: Dict[str, Any], findings: List[Dict[str, Any]]) -> str:
        title = (capsule.get("title") or "").lower()
        keywords = self._keywords(title)

        if any(word in keywords for word in {"security", "attack", "injection"}):
            return "security_issue"
        if any(word in keywords for word in {"syntax", "parse", "compile"}):
            return "syntax_error"
        if any(word in keywords for word in {"test", "assert", "failure"}):
            return "test_failure"
        if any(word in keywords for word in {"logic", "incorrect", "wrong"}):
            return "logic_error"
        if any(f.get("severity") in {"high", "critical"} for f in findings):
            return "security_issue"
        return "unknown"

    def _common_files(self, members: List[Dict[str, Any]]) -> List[str]:
        files: List[str] = []
        for member in members:
            capsule = member.get("capsule") or {}
            files.extend(capsule.get("suspected_files", []))
        counts = Counter(files)
        return [file for file, count in counts.items() if count >= 2][:5]

    def _summarize_defect(self, record: Dict[str, Any]) -> Dict[str, Any]:
        capsule = record.get("defect_capsule") or {}
        return {
            "timestamp": record.get("timestamp"),
            "title": capsule.get("title", "Unknown defect"),
            "severity": capsule.get("severity", record.get("adversarial_severity", "medium")),
        }

    def _task_complexity(self, task_object: Dict[str, Any]) -> float:
        constraints = len(task_object.get("constraints", []))
        success_metrics = len(task_object.get("success_metrics", []))
        allowed_tools = len(task_object.get("allowed_tools", []))

        score = min(0.5, constraints * 0.08) + min(0.3, success_metrics * 0.05)
        if allowed_tools and allowed_tools < 3:
            score += 0.2
        return min(score, 1.0)

    def _similarity_to_known_failures(self, task_object: Dict[str, Any]) -> float:
        # Placeholder for future embedding similarity
        return 0.0

    def _keywords(self, text: str) -> List[str]:
        stop_words = {"the", "and", "for", "with", "this", "that", "have", "from", "were", "been", "error"}
        words = re.findall(r"[a-z]{3,15}", text)
        return [w for w in words if w not in stop_words][:10]

    # ------------------------------------------------------------------ #
    # Result helpers
    # ------------------------------------------------------------------ #
    def _empty_result(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_verifications": 0,
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "adversarial_resilience_score": 1.0,
                "average_confidence": 0.0,
                "objective_pass_rate": 0.0,
                "discrepancy_rate": 0.0,
            },
            "pattern_clusters": [],
            "temporal_trends": {},
            "risk_factors": [],
            "recommendations": [
                {
                    "type": "data_collection",
                    "priority": "high",
                    "description": "No verification history available for analysis.",
                    "action": "Collect verification runs to enable pattern recognition.",
                }
            ],
        }

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        result = self._empty_result()
        result["error"] = error_msg
        result["recommendations"].append(
            {
                "type": "system_error",
                "priority": "high",
                "description": f"Pattern analysis error: {error_msg}",
                "action": "Verify ledger database integrity and schema.",
            }
        )
        return result


def main() -> None:
    """CLI entry point for offline analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="VISTA Failure Pattern Analyzer")
    parser.add_argument("--lookback", type=int, default=30, help="Lookback window in days")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()

    analyzer = FailurePatternAnalyzer()
    analysis = analyzer.analyze_verification_history(args.lookback)

    if args.output:
        Path(args.output).write_text(json.dumps(analysis, indent=2))
        print(f"Analysis written to {args.output}")
    else:
        print(json.dumps(analysis, indent=2))

    summary = analysis.get("summary", {})
    print("\n=== SUMMARY ===")
    print(f"Total verifications: {summary.get('total_verifications', 0)}")
    print(f"Success rate       : {summary.get('success_rate', 0):.1%}")
    print(f"ARS score          : {summary.get('adversarial_resilience_score', 1):.3f}")
    print(f"Pattern clusters   : {len(analysis.get('pattern_clusters', []))}")


if __name__ == "__main__":
    main()
