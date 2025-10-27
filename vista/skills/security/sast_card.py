import subprocess, json, os, hashlib
from typing import Dict, Any, List
from ...contracts.task_spec_v2 import TaskSpec
from ...contracts.artifact_v2 import Artifact
from ...memory.graph import ArtifactGraph
from ...contracts.stamping import stamp_artifact

class SASTCard:
    """Static Application Security Testing specialist card"""
    provides = ["vulnerability_scanning", "code_quality"]
    requires = ["codebase"]

    def run(self, spec: TaskSpec, graph: ArtifactGraph) -> Artifact:
        # Collect target code artifacts
        target_ids: List[str] = spec.inputs.get("code_artifacts", [])
        if target_ids:
            code_arts_data = [graph.store.get_artifact(aid) for aid in target_ids if graph.store.has_artifact(aid)]
            code_arts = [Artifact(**data) for data in code_arts_data if data]
        else:
            # fallback: all artifacts of kind "code" in the project
            code_arts = []
            for n, attrs in graph.g.nodes(data=True):
                art = attrs.get("artifact")
                if art and art.kind == "code":
                    code_arts.append(art)

        findings: List[Dict[str, Any]] = []
        scanner_versions = {}

        for art in code_arts:
            if not art:
                continue
            artifact_findings, versions = self._scan_artifact(art)
            findings.extend(artifact_findings)
            scanner_versions.update(versions)

        report = {
            "scanner": "bandit",
            "scanner_versions": scanner_versions,
            "scanned_artifacts": [a.artifact_id for a in code_arts],
            "findings": findings,
        }
        content = json.dumps(report, indent=2, sort_keys=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        content_path = f"./artifacts/{content_hash}"
        os.makedirs(os.path.dirname(content_path), exist_ok=True)
        with open(content_path, "w") as f:
            f.write(content)

        art = Artifact(
            artifact_id=f"security_scan_{spec.task_id}",
            project_id=spec.project_id,
            kind="security_report",
            path=content_path,
            blob_sha256=content_hash,
            content_ref=content_path,
            produced_by_task=spec.task_id,
            parents=[a.artifact_id for a in code_arts if a],
            metadata={
                "findings_count": len(findings),
                "critical_findings": sum(1 for f in findings if str(f.get("severity","")).upper() in {"CRITICAL","HIGH"}),
                "scanner_versions": scanner_versions
            }
        )
        return stamp_artifact(art, runner_id="python311")

    def _scan_artifact(self, artifact: Artifact) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        findings: List[Dict[str, Any]] = []
        versions: Dict[str, str] = {}

        if not artifact.path or not os.path.exists(artifact.path):
            return findings, versions

        # Get bandit version
        try:
            version_result = subprocess.run(
                ["bandit", "--version"],
                capture_output=True, text=True, timeout=10
            )
            if version_result.returncode == 0:
                versions["bandit"] = version_result.stdout.strip()
        except:
            versions["bandit"] = "unknown"

        # Bandit (Python). If missing, degrade gracefully.
        try:
            proc = subprocess.run(
                ["bandit", "-f", "json", "-r", artifact.path],
                capture_output=True, text=True, timeout=60
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                for issue in data.get("results", []):
                    findings.append({
                        "tool": "bandit",
                        "severity": issue.get("issue_severity", "MEDIUM"),
                        "confidence": issue.get("issue_confidence", "MEDIUM"),
                        "description": issue.get("issue_text", ""),
                        "file": issue.get("filename", ""),
                        "line": issue.get("line_number", None),
                        "test_id": issue.get("test_id", "")
                    })
        except FileNotFoundError:
            findings.append({"tool":"bandit","severity":"LOW","description":"bandit not installed; scan skipped"})
        except subprocess.TimeoutExpired:
            findings.append({"tool":"bandit","severity":"MEDIUM","description":"bandit timed out"})
        except json.JSONDecodeError:
            findings.append({"tool":"bandit","severity":"LOW","description":"bandit produced non-JSON output"})

        return findings, versions
