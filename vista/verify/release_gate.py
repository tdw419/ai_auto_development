from typing import Tuple, List, Dict, Any

def release_ok(verdict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if verdict passes release gates.

    Returns:
        Tuple of (is_ok, error_messages)
    """
    errors: List[str] = []

    # Check security gate
    if "sec" in verdict.get("required_judges", []):
        sec_results = [r for r in verdict["results"] if r["judge"] == "sec"]
        if not sec_results or not sec_results[0]["pass"]:
            errors.append("🚫 Security gate failed")

    # Check performance gate
    if "perf" in verdict.get("required_judges", []):
        perf_results = [r for r in verdict["results"] if r["judge"] == "perf"]
        if not perf_results or not perf_results[0]["pass"]:
            errors.append("🚫 Performance gate failed")

    # Check core judges
    core_judges = verdict.get("required_judges", [])
    for judge in core_judges:
        judge_results = [r for r in verdict["results"] if r["judge"] == judge]
        if judge_results and not judge_results[0]["pass"]:
            errors.append(f"🚫 {judge} judge failed")

    return (len(errors) == 0, errors)

def can_release(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive release check with detailed reporting.
    """
    is_ok, errors = release_ok(verdict)

    return {
        "can_release": is_ok,
        "errors": errors,
        "verdict_id": verdict.get("artifact_id", "unknown"),
        "project_id": verdict.get("project_id", "unknown"),
        "overall_score": verdict.get("overall_score", 0),
        "required_judges": verdict.get("required_judges", []),
        "passed_judges": [
            r["judge"] for r in verdict["results"]
            if r.get("pass", False)
        ],
        "failed_judges": [
            r["judge"] for r in verdict["results"]
            if not r.get("pass", True)
        ]
    }
