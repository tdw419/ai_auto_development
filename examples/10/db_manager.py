"""
LanceDB Manager for Agent Turn History
Stores embeddings, retrieves context, manages checkpoints
"""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import lancedb
import numpy as np

try:
    from .path_shim import get_current_utc_time, to_iso_format
except ImportError:  # pragma: no cover - direct execution fallback
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from path_shim import get_current_utc_time, to_iso_format


class LanceDBManager:
    """
    Manages all vector storage operations for the multi-agent system
    """
    
    def __init__(self, db_path: str = "./data/lancedb"):
        """
        Initialize LanceDB connection
        
        Args:
            db_path: Path to LanceDB database
        """
        self.db = lancedb.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize required tables if they don't exist"""
        
        # Table 1: Agent Turns (main conversation log)
        if "agent_turns" not in self.db.table_names():
            # Create with sample data to establish schema
            sample = [{
                'turn_id': 'init',
                'agent_role': 'builder',
                'content': 'initialization',
                'vector': np.zeros(768).tolist(),  # Assuming 768-dim embeddings
                'task_id': 'init',
                'turn_number': 0,
                'status': 'passed',
                'timestamp': to_iso_format(get_current_utc_time()),
                'files_changed': json.dumps([]),
                'roadmap_chunk': '',
                'metadata': json.dumps({})
            }]
            self.db.create_table("agent_turns", sample)
        
        self.turns_table = self.db.open_table("agent_turns")
        
        # Table 2: Checkpoints (successful milestones)
        if "checkpoints" not in self.db.table_names():
            sample = [{
                'checkpoint_id': 'init',
                'turn_id': 'init',
                'checkpoint_type': 'init',
                'vector': np.zeros(768).tolist(),
                'timestamp': to_iso_format(get_current_utc_time()),
                'files': json.dumps([]),
                'metadata': json.dumps({})
            }]
            self.db.create_table("checkpoints", sample)
        
        self.checkpoints_table = self.db.open_table("checkpoints")
        
        # Table 3: Defects (bugs and issues)
        if "defects" not in self.db.table_names():
            sample = [{
                'defect_id': 'init',
                'turn_id': 'init',
                'defect_type': 'init',
                'vector': np.zeros(768).tolist(),
                'severity': 'low',
                'description': 'init',
                'resolved': False,
                'timestamp': to_iso_format(get_current_utc_time()),
                'metadata': json.dumps({})
            }]
            self.db.create_table("defects", sample)
        
        self.defects_table = self.db.open_table("defects")
        
        # Table 4: Escalations (human intervention needed)
        if "escalations" not in self.db.table_names():
            sample = [{
                'escalation_id': 'init',
                'task_id': 'init',
                'turn': 0,
                'defect_id': 'init',
                'timestamp': to_iso_format(get_current_utc_time()),
                'resolved': False,
                'metadata': json.dumps({})
            }]
            self.db.create_table("escalations", sample)
        
        self.escalations_table = self.db.open_table("escalations")
    
    def store_turn(
        self,
        turn_id: str,
        agent_role: str,
        content: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any]
    ):
        """
        Store a complete agent turn with embedding
        
        Args:
            turn_id: Unique turn identifier
            agent_role: 'builder' or 'verifier'
            content: Full text content
            embedding: Vector embedding
            metadata: Additional data (task_id, turn_number, etc.)
        """
        
        record = {
            'turn_id': turn_id,
            'agent_role': agent_role,
            'content': content,
            'vector': embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
            'task_id': metadata.get('task_id', ''),
            'turn_number': metadata.get('turn_number', 0),
            'status': metadata.get('status', 'pending'),
            'timestamp': metadata.get('timestamp', to_iso_format(get_current_utc_time())),
            'files_changed': json.dumps(metadata.get('files_changed', [])),
            'roadmap_chunk': metadata.get('roadmap_chunk', ''),
            'metadata': json.dumps(metadata)
        }
        
        self.turns_table.add([record])
    
    def retrieve_relevant_context(
        self,
        query: str,
        n_results: int = 5,
        filter_by: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve most relevant past turns using vector search
        
        Args:
            query: Search query (will be embedded)
            n_results: Number of results to return
            filter_by: Optional filters (e.g., {'status': 'passed'})
            
        Returns:
            List of relevant turn records
        """
        
        # This is a placeholder - you'd embed the query first
        # For now, return recent successful turns
        
        # In production:
        # query_embedding = self.embedder.embed(query)
        # results = self.turns_table.search(query_embedding).limit(n_results)
        
        # Placeholder: return recent passed turns
        df = self.turns_table.to_pandas()
        
        if filter_by:
            for key, value in filter_by.items():
                df = df[df[key] == value]
        
        # Get most recent
        df = df.sort_values('timestamp', ascending=False).head(n_results)
        
        results = []
        for _, row in df.iterrows():
            results.append({
                'turn_id': row['turn_id'],
                'text': row['content'],
                'summary': row['content'][:200] + '...',
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })
        
        return results
    
    def retrieve_similar_turns(
        self,
        embedding: np.ndarray,
        n_results: int = 3,
        exclude_status: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Find similar past turns using vector similarity
        
        Args:
            embedding: Query embedding vector
            n_results: Number of results
            exclude_status: Statuses to exclude (e.g., ['failed'])
            
        Returns:
            Similar turn records
        """
        
        # Convert embedding to list if needed
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        # Perform vector search
        results = self.turns_table.search(embedding).limit(n_results).to_pandas()
        
        # Filter by status if needed
        if exclude_status:
            results = results[~results['status'].isin(exclude_status)]
        
        # Convert to list of dicts
        similar = []
        for _, row in results.iterrows():
            similar.append({
                'turn_id': row['turn_id'],
                'content': row['content'],
                'agent_role': row['agent_role'],
                'status': row['status'],
                'distance': row.get('_distance', 0)
            })
        
        return similar
    
    def update_turn_status(
        self,
        turn_id: str,
        status: str,
        verifier_notes: str = ""
    ):
        """
        Update the status of a turn after verification
        
        Args:
            turn_id: Turn to update
            status: New status ('passed', 'failed', 'retry')
            verifier_notes: Notes from verifier
        """
        
        # LanceDB doesn't support direct updates, so we need to:
        # 1. Read the record
        # 2. Delete it
        # 3. Re-insert with updated data
        
        df = self.turns_table.to_pandas()
        record = df[df['turn_id'] == turn_id].iloc[0]
        
        # Update fields
        metadata = json.loads(record['metadata'])
        metadata['verifier_notes'] = verifier_notes
        metadata['verified_at'] = to_iso_format(get_current_utc_time())
        
        updated_record = {
            'turn_id': record['turn_id'],
            'agent_role': record['agent_role'],
            'content': record['content'],
            'vector': record['vector'],
            'task_id': record['task_id'],
            'turn_number': record['turn_number'],
            'status': status,
            'timestamp': record['timestamp'],
            'files_changed': record['files_changed'],
            'roadmap_chunk': record['roadmap_chunk'],
            'metadata': json.dumps(metadata)
        }
        
        # Delete old and insert new (LanceDB pattern)
        self.turns_table.delete(f"turn_id = '{turn_id}'")
        self.turns_table.add([updated_record])
    
    def store_checkpoint(
        self,
        turn_id: str,
        checkpoint_type: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any]
    ):
        """
        Store a checkpoint (successful milestone)
        
        Args:
            turn_id: Associated turn
            checkpoint_type: Type (e.g., 'verification_success')
            embedding: Vector embedding
            metadata: Additional data
        """
        
        checkpoint_id = f"{turn_id}_checkpoint_{checkpoint_type}"
        
        record = {
            'checkpoint_id': checkpoint_id,
            'turn_id': turn_id,
            'checkpoint_type': checkpoint_type,
            'vector': embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
            'timestamp': to_iso_format(get_current_utc_time()),
            'files': json.dumps(metadata.get('files', [])),
            'metadata': json.dumps(metadata)
        }
        
        self.checkpoints_table.add([record])
    
    def store_defect(
        self,
        defect_id: str,
        turn_id: str,
        defect_data: Dict[str, Any],
        embedding: np.ndarray
    ):
        """
        Store a defect capsule
        
        Args:
            defect_id: Unique defect identifier
            turn_id: Associated turn
            defect_data: Defect capsule data
            embedding: Vector embedding of defect
        """
        
        record = {
            'defect_id': defect_id,
            'turn_id': turn_id,
            'defect_type': defect_data.get('defect_type', 'unknown'),
            'vector': embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
            'severity': defect_data.get('severity', 'medium'),
            'description': defect_data.get('description', ''),
            'resolved': False,
            'timestamp': to_iso_format(get_current_utc_time()),
            'metadata': json.dumps(defect_data)
        }
        
        self.defects_table.add([record])
    
    def retrieve_similar_defects(
        self,
        embedding: np.ndarray,
        n_results: int = 3
    ) -> List[Dict]:
        """
        Find similar past defects (for learning from past mistakes)
        
        Args:
            embedding: Query embedding
            n_results: Number of results
            
        Returns:
            Similar defect records
        """
        
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        results = self.defects_table.search(embedding).limit(n_results).to_pandas()
        
        similar = []
        for _, row in results.iterrows():
            metadata = json.loads(row['metadata'])
            similar.append({
                'defect_id': row['defect_id'],
                'defect_type': row['defect_type'],
                'description': row['description'],
                'severity': row['severity'],
                'resolved': row['resolved'],
                'suggested_fix': metadata.get('suggested_fix', ''),
                'distance': row.get('_distance', 0)
            })
        
        return similar
    
    def store_escalation(self, escalation_data: Dict[str, Any]):
        """
        Store an escalation to human
        
        Args:
            escalation_data: Full escalation information
        """
        
        record = {
            'escalation_id': f"esc_{escalation_data['task_id']}_{escalation_data['turn']}",
            'task_id': escalation_data['task_id'],
            'turn': escalation_data['turn'],
            'defect_id': escalation_data['defect']['defect_id'],
            'timestamp': escalation_data['timestamp'],
            'resolved': False,
            'metadata': json.dumps(escalation_data)
        }
        
        self.escalations_table.add([record])
    
    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Summary dict with counts and statistics
        """
        
        turns_df = self.turns_table.to_pandas()
        task_turns = turns_df[turns_df['task_id'] == task_id]
        
        summary = {
            'task_id': task_id,
            'total_turns': len(task_turns),
            'passed_turns': len(task_turns[task_turns['status'] == 'passed']),
            'failed_turns': len(task_turns[task_turns['status'] == 'failed']),
            'builder_turns': len(task_turns[task_turns['agent_role'] == 'builder']),
            'verifier_turns': len(task_turns[task_turns['agent_role'] == 'verifier']),
            'start_time': task_turns['timestamp'].min() if len(task_turns) > 0 else None,
            'end_time': task_turns['timestamp'].max() if len(task_turns) > 0 else None
        }
        
        return summary
    
    def cleanup_old_data(self, days: int = 30):
        """
        Archive or delete old data
        
        Args:
            days: Keep data newer than this many days
        """
        
        cutoff = to_iso_format(get_current_utc_time() - timedelta(days=days))
        
        # Delete old turns
        self.turns_table.delete(f"timestamp < '{cutoff}'")
        
        # Keep checkpoints and defects for longer (90 days)
        long_cutoff = to_iso_format(get_current_utc_time() - timedelta(days=90))
        self.checkpoints_table.delete(f"timestamp < '{long_cutoff}'")
        self.defects_table.delete(f"timestamp < '{long_cutoff}'")
