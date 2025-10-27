from typing import Dict, Any
from .artifact_v2 import Artifact

def stamp_artifact(a: Artifact, runner_id: str, extra_meta: Dict[str, Any] = None) -> Artifact:
    """Stamp artifact with execution context and metadata"""
    md = dict(a.metadata)
    md["runner_id"] = runner_id
    md["stamped_at"] = __import__('time').time()

    if extra_meta:
        md.update(extra_meta)

    # Return new artifact with updated metadata (immutable)
    return Artifact(
        artifact_id=a.artifact_id,
        project_id=a.project_id,
        kind=a.kind,
        path=a.path,
        blob_sha256=a.blob_sha256,
        content_ref=a.content_ref,
        produced_by_task=a.produced_by_task,
        parents=a.parents,
        metadata=md,
        created_at=a.created_at
    )
