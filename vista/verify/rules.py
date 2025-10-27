from typing import Tuple, List, Callable, Optional
from ..contracts.artifact_v2 import Artifact
from ..memory.graph import ArtifactGraph

def require_passing_security_lineage(
    artifact: Artifact,
    graph: ArtifactGraph,
    verdict_lookup: Callable[[str], Optional[dict]]
) -> Tuple[bool, List[str]]:
    """
    Require deployable artifacts to have passing security reports in lineage.

    Args:
        artifact: Artifact to check
        graph: Artifact graph for lineage traversal
        verdict_lookup: Function to get verdict by artifact_id

    Returns:
        Tuple of (is_compliant, error_messages)
    """
    if artifact.kind not in {"dockerfile", "deploy_manifest", "service"}:
        return True, []  # Not a deployable artifact

    errors = []
    security_reports_found = 0
    passing_security_reports = 0

    # Walk through ancestors
    for ancestor in graph.get_lineage(artifact.artifact_id):
        if ancestor.kind == "security_report":
            security_reports_found += 1
            verdict = verdict_lookup(ancestor.artifact_id)
            if verdict and verdict.get("pass"):
                passing_security_reports += 1

    # Check requirements
    if security_reports_found == 0:
        errors.append("No security reports found in artifact lineage")
    elif passing_security_reports == 0:
        errors.append("No passing security reports in artifact lineage")

    is_compliant = len(errors) == 0

    if is_compliant and security_reports_found > 0:
        errors.append(f"✅ Security lineage: {passing_security_reports}/{security_reports_found} reports passing")

    return is_compliant, errors

def check_release_rules(
    artifact: Artifact,
    graph: ArtifactGraph,
    verdict_lookup: Callable[[str], Optional[dict]]
) -> Dict[str, Any]:
    """
    Comprehensive release rule checking.
    """
    security_ok, security_errors = require_passing_security_lineage(artifact, graph, verdict_lookup)

    rules = {
        "security_lineage": {
            "passed": security_ok,
            "errors": security_errors
        },
        "all_passed": security_ok
    }

    return rules
