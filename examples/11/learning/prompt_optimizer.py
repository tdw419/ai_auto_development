#!/usr/bin/env python3
"""VISTA Prompt Optimization Engine."""
from __future__ import annotations

import json
import logging
import math
import random
import sqlite3
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

from utils.time_utils import to_iso, utc_now

logger = logging.getLogger(__name__)

PERFORMANCE_DB = Path("data/prompt_performance.db")
OPTIMIZED_DIR = Path("prompts/optimized")


class PromptOptimizer:
    """Evolve prompt templates based on historical verification performance."""

    def __init__(self) -> None:
        self.variants = self._load_variants()
        self.performance = self._load_performance()
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_optimized_builder_prompt(self, task_type: str, risk_profile: Dict[str, Any]) -> str:
        if risk_profile.get("overall_risk", 0) > 0.7:
            return self._best_variant("builder", task_type)
        return self._bandit_variant("builder", task_type)

    def get_targeted_adversarial_prompt(self, defect_pattern: Dict[str, Any]) -> str:
        base = self.variants["adversarial"].get("adversarial_strict_v1", {}).get("template", "")
        focus = self._pattern_focus(defect_pattern.get("primary_type", "unknown"))
        return base.replace("{{PATTERN_FOCUS}}", focus)

    def record_prompt_performance(
        self,
        variant_id: str,
        task_type: str,
        success: bool,
        confidence: float,
        metrics: Dict[str, Any],
    ) -> None:
        self._store_performance(
            {
                "variant_id": variant_id,
                "task_type": task_type,
                "success": success,
                "confidence": confidence,
                "metrics": metrics,
                "timestamp": to_iso(utc_now()),
            }
        )
        self.performance[variant_id][task_type].append({"success": success, "confidence": confidence})

    def evolve_prompts(self) -> List[Dict[str, Any]]:
        created: List[Dict[str, Any]] = []
        for category in ["builder", "adversarial"]:
            created.extend(self._evolve_category(category))
        self.history.append({"timestamp": to_iso(utc_now()), "created": len(created)})
        return created

    def get_optimization_insights(self) -> Dict[str, Any]:
        total = sum(len(records) for variant in self.performance.values() for records in variant.values())
        trend = self._performance_trend()
        return {
            "total_records": total,
            "evolution_steps": len(self.history),
            "trend": trend,
            "top_variants": self._top_variants(5),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_variants(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        variants: Dict[str, Dict[str, Dict[str, Any]]] = {"builder": {}, "adversarial": {}, "meta": {}}
        OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
        defaults = {
            "builder": ["builder_stable_v1", "builder_creative_v1", "builder_precise_v1"],
            "adversarial": ["adversarial_strict_v1", "adversarial_comprehensive_v1"],
            "meta": ["meta_balanced_v1"],
        }
        for category, names in defaults.items():
            for name in names:
                template = self._load_template(name)
                variants[category][name] = {
                    "template": template,
                    "generation": 1,
                    "stability": "high" if "stable" in name or "strict" in name else "medium",
                    "created": to_iso(utc_now()),
                }
        return variants

    def _load_template(self, variant_name: str) -> str:
        paths = [OPTIMIZED_DIR / f"{variant_name}.txt", Path("prompts") / f"{variant_name.split('_')[0]}.base.txt"]
        for path in paths:
            if path.exists():
                return path.read_text()
        return "Base prompt template"

    def _load_performance(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        perf: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        if not PERFORMANCE_DB.exists():
            return perf
        conn = sqlite3.connect(PERFORMANCE_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id TEXT,
                task_type TEXT,
                success INTEGER,
                confidence REAL,
                metrics TEXT,
                timestamp TEXT
            )
            """
        )
        cursor.execute("SELECT variant_id, task_type, success, confidence FROM prompt_performance")
        for variant_id, task_type, success, confidence in cursor.fetchall():
            perf[variant_id][task_type].append({"success": bool(success), "confidence": confidence})
        conn.close()
        return perf

    def _best_variant(self, category: str, task_type: str) -> str:
        variants = self.variants.get(category, {})
        best_score = -1.0
        best_template = next(iter(variants.values()))["template"] if variants else ""
        for variant_id, info in variants.items():
            records = self.performance.get(variant_id, {}).get(task_type, [])
            if not records:
                continue
            success_rate = sum(r["success"] for r in records) / len(records)
            confidence = sum(r["confidence"] for r in records) / len(records)
            score = success_rate * confidence
            if score > best_score:
                best_score = score
                best_template = info["template"]
        return best_template

    def _bandit_variant(self, category: str, task_type: str) -> str:
        variants = self.variants.get(category, {})
        if not variants:
            return ""
        total = sum(len(self.performance.get(vid, {}).get(task_type, [])) for vid in variants)
        best_id = None
        best_score = float("-inf")
        for variant_id, info in variants.items():
            records = self.performance.get(variant_id, {}).get(task_type, [])
            count = len(records)
            if count == 0:
                score = float("inf")
            else:
                success_rate = sum(r["success"] for r in records) / count
                bonus = math.sqrt(2 * math.log(total + 1) / count)
                score = success_rate + bonus
            if score > best_score:
                best_score = score
                best_id = variant_id
        return variants[best_id]["template"] if best_id else next(iter(variants.values()))["template"]

    def _pattern_focus(self, pattern_type: str) -> str:
        focus_map = {
            "syntax_error": "Emphasize syntax validation and language rules.",
            "import_error": "Verify module imports and environment setup.",
            "security_issue": "Perform exhaustive security testing and exploit analysis.",
            "test_failure": "Focus on test coverage gaps and boundary cases.",
            "logic_error": "Inspect business logic, conditionals, and data flow.",
        }
        return focus_map.get(pattern_type, "Conduct comprehensive adversarial testing across all dimensions.")

    def _store_performance(self, record: Dict[str, Any]) -> None:
        PERFORMANCE_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(PERFORMANCE_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id TEXT,
                task_type TEXT,
                success INTEGER,
                confidence REAL,
                metrics TEXT,
                timestamp TEXT
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO prompt_performance (variant_id, task_type, success, confidence, metrics, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["variant_id"],
                record["task_type"],
                int(record["success"]),
                record["confidence"],
                json.dumps(record["metrics"]),
                record["timestamp"],
            ),
        )
        conn.commit()
        conn.close()

    def _evolve_category(self, category: str) -> List[Dict[str, Any]]:
        variants = self.variants.get(category, {})
        if len(variants) < 2:
            return []
        parent_ids = list(variants.keys())
        parent1 = random.choice(parent_ids)
        parent2 = random.choice([vid for vid in parent_ids if vid != parent1])
        offspring: List[Dict[str, Any]] = []
        for _ in range(2):
            template = self._mutate(self._crossover(variants[parent1]["template"], variants[parent2]["template"]))
            variant_id = f"{category}_gen{variants[parent1]['generation']+1}_v{random.randint(100,999)}"
            new_variant = {
                "template": template,
                "generation": variants[parent1]["generation"] + 1,
                "stability": "low",
                "created": to_iso(utc_now()),
            }
            self.variants[category][variant_id] = new_variant
            offspring.append({"variant_id": variant_id, **new_variant})
        return offspring

    def _crossover(self, prompt1: str, prompt2: str) -> str:
        lines1 = prompt1.splitlines()
        lines2 = prompt2.splitlines()
        child = []
        max_len = max(len(lines1), len(lines2))
        for i in range(max_len):
            if i < len(lines1) and i < len(lines2):
                child.append(random.choice([lines1[i], lines2[i]]))
            elif i < len(lines1):
                child.append(lines1[i])
            else:
                child.append(lines2[i])
        return "\n".join(child)

    def _mutate(self, prompt: str, rate: float = 0.1) -> str:
        lines = prompt.splitlines()
        new_lines = []
        for line in lines:
            if random.random() < rate:
                new_lines.append(self._mutate_line(line))
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

    def _mutate_line(self, line: str) -> str:
        if not line.strip():
            return line
        if random.random() < 0.3:
            return line.upper()
        if random.random() < 0.3:
            return "**" + line.strip() + "**"
        return line + " (ensure thorough coverage)"

    def _performance_trend(self) -> Dict[str, Any]:
        recent = self._period_performance(7)
        historical = self._period_performance(30)
        if not recent or not historical:
            return {"trend": "unknown", "improvement": 0.0}
        improvement = recent["success_rate"] - historical["success_rate"]
        if improvement > 0.05:
            trend = "improving"
        elif improvement < -0.05:
            trend = "declining"
        else:
            trend = "stable"
        return {"trend": trend, "improvement": improvement}

    def _period_performance(self, days: int) -> Dict[str, Any] | None:
        cutoff = to_iso(utc_now() - timedelta(days=days))
        if not PERFORMANCE_DB.exists():
            return None
        conn = sqlite3.connect(PERFORMANCE_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT success, confidence FROM prompt_performance WHERE timestamp > ?",
            (cutoff,),
        )
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return None
        success_rate = sum(row[0] for row in rows) / len(rows)
        avg_confidence = sum(row[1] for row in rows) / len(rows)
        return {"success_rate": success_rate, "average_confidence": avg_confidence}

    def _top_variants(self, limit: int) -> List[Dict[str, Any]]:
        scored = []
        for category, variants in self.variants.items():
            for variant_id, info in variants.items():
                fitness = self._variant_fitness(category, variant_id)
                total_tests = sum(len(records) for records in self.performance.get(variant_id, {}).values())
                scored.append({
                    "variant_id": variant_id,
                    "category": category,
                    "fitness": fitness,
                    "tests": total_tests,
                    "generation": info["generation"],
                })
        return sorted(scored, key=lambda x: x["fitness"], reverse=True)[:limit]

    def _variant_fitness(self, category: str, variant_id: str) -> float:
        records = self.performance.get(variant_id, {})
        total = sum(len(r) for r in records.values())
        if total == 0:
            return 0.5
        successes = sum(rec["success"] for recs in records.values() for rec in recs)
        avg_confidence = sum(rec["confidence"] for recs in records.values() for rec in recs) / total
        diversity = len(records)
        return successes / total * avg_confidence + min(0.3, diversity * 0.05)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Prompt optimization toolkit")
    parser.add_argument("--evolve", action="store_true")
    parser.add_argument("--insights", action="store_true")
    args = parser.parse_args()

    optimizer = PromptOptimizer()
    if args.evolve:
        created = optimizer.evolve_prompts()
        print(f"Created {len(created)} new variants")
    if args.insights:
        print(json.dumps(optimizer.get_optimization_insights(), indent=2))


if __name__ == "__main__":
    main()
