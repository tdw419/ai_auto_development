import networkx as nx
from typing import List
from .store import Store
from ..contracts.artifact_v2 import Artifact

class ArtifactGraph:
    def __init__(self, store: Store):
        self.g = nx.DiGraph()
        self.store = store

    def sync_from_store(self, project_id: str):
        """Sync graph from persistent storage for a project"""
        self.g.clear()
        artifacts = self.store.list_artifacts(project_id)

        for artifact_data in artifacts:
            artifact = Artifact(**artifact_data)
            self.g.add_node(
                artifact.artifact_id,
                kind=artifact.kind,
                meta=artifact.metadata,
                artifact=artifact
            )
            for parent_id in artifact.parents:
                if self.store.has_artifact(parent_id):
                    self.g.add_edge(parent_id, artifact.artifact_id)

    def neighborhood(self, artifact_id: str, hops: int = 2) -> List[Artifact]:
        """Get contextual artifacts within N hops for agents/judges"""
        if artifact_id not in self.g:
            return []

        nodes = {artifact_id}
        for _ in range(hops):
            expanded = set()
            for node in list(nodes):
                expanded.update(self.g.predecessors(node))
                expanded.update(self.g.successors(node))
            nodes |= expanded

        arts = []
        for n in nodes:
            art = self.g.nodes[n].get("artifact")
            if art: arts.append(art)
        return arts

    def get_lineage(self, artifact_id: str) -> List[Artifact]:
        """Get complete lineage (all ancestors) of an artifact"""
        if artifact_id not in self.g:
            return []

        ancestors = set()
        nodes = [artifact_id]
        while nodes:
            node = nodes.pop()
            for pred in self.g.predecessors(node):
                if pred not in ancestors:
                    ancestors.add(pred)
                    nodes.append(pred)

        return [Artifact(**self.store.get_artifact(a)) for a in ancestors if self.store.has_artifact(a)]
