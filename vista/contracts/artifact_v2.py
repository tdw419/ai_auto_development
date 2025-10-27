from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class Artifact(BaseModel):
    artifact_id: str
    project_id: str
    kind: str               # "db_schema","api_spec","ui_wire","dockerfile","tests",...
    path: Optional[str]     # repo path if file materialized
    blob_sha256: str        # content hash
    content_ref: str        # blob store key (e.g., ./artifacts/<sha>)
    produced_by_task: str
    parents: List[str]      # upstream artifact_ids
    metadata: Dict[str, Any]  # metrics, model, token cost, etc.
    created_at: float = Field(default_factory=__import__('time').time)
