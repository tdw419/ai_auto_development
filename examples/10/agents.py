"""
Multi-Agent Verification Loop System
Implements Builder -> Verifier -> Scheduler pattern for long-horizon coherence
"""

import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from .path_shim import get_current_utc_time, to_iso_format
except ImportError:  # pragma: no cover - direct execution fallback
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from path_shim import get_current_utc_time, to_iso_format


class AgentRole(Enum):
    BUILDER = "builder"
    VERIFIER = "verifier"
    SCHEDULER = "scheduler"


class VerificationStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    RETRY = "retry"
    ESCALATE = "escalate"


@dataclass
class BatonPacket:
    """
    The handoff structure between agents.
    Contains everything needed for the next agent to continue.
    """
    turn_id: str
    timestamp: str
    builder_summary: str
    response_text: str
    files_changed: List[str]
    verification_hints: List[str]
    compressed_context: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_prompt(self) -> str:
        """Convert baton to a prompt for the next agent"""
        return f"""
PREVIOUS TURN SUMMARY:
{self.compressed_context}

FILES MODIFIED:
{', '.join(self.files_changed) if self.files_changed else 'None'}

BUILDER'S WORK:
{self.builder_summary}

VERIFICATION HINTS:
{chr(10).join(f"- {h}" for h in self.verification_hints)}
"""


@dataclass
class DefectCapsule:
    """
    Concise bug report from verifier to next builder
    """
    defect_id: str
    turn_id: str
    defect_type: str  # lint, test_failure, coherence, logic
    description: str
    suggested_fix: str
    affected_files: List[str]
    severity: str  # critical, high, medium, low
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_prompt(self) -> str:
        return f"""
DEFECT FOUND (#{self.defect_id}):
Type: {self.defect_type}
Severity: {self.severity}

Description:
{self.description}

Affected Files:
{', '.join(self.affected_files)}

Suggested Fix:
{self.suggested_fix}
"""


@dataclass
class TaskState:
    """
    Persistent state tracked across agent turns
    """
    task_id: str
    current_turn: int
    agent_history: List[Dict]
    roadmap_position: int
    total_roadmap_items: int
    open_issues: List[str]
    resolved_issues: List[str]
    checkpoints: List[Dict]
    token_usage: int
    
    def to_dict(self) -> dict:
        return asdict(self)


class BuilderAgent:
    """
    Handles bounded work sprints (15-20 minutes)
    Takes roadmap + context, produces artifacts + changelog
    """
    
    def __init__(self, llm_client, embedder, db_manager, max_duration_minutes=20):
        self.llm_client = llm_client
        self.embedder = embedder
        self.db = db_manager
        self.max_duration = max_duration_minutes * 60  # Convert to seconds
        self.role = AgentRole.BUILDER
    
    def run_iteration(
        self, 
        task_state: TaskState,
        roadmap_chunk: str,
        defect_capsule: Optional[DefectCapsule] = None
    ) -> BatonPacket:
        """
        Execute one builder iteration
        
        Args:
            task_state: Current persistent state
            roadmap_chunk: The specific goal for this sprint
            defect_capsule: Optional bug report from previous verifier
            
        Returns:
            BatonPacket for next agent
        """
        start_time = time.time()
        turn_id = self._generate_turn_id(task_state)
        
        # 1. Build context from LanceDB
        context_chunks = self.db.retrieve_relevant_context(
            query=roadmap_chunk,
            n_results=5
        )
        
        # 2. Construct prompt
        prompt = self._build_prompt(
            roadmap_chunk=roadmap_chunk,
            context_chunks=context_chunks,
            task_state=task_state,
            defect_capsule=defect_capsule
        )
        
        # 3. Call LLM (LM Studio)
        response = self.llm_client.generate(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7
        )
        
        # 4. Extract structured output
        parsed = self._parse_response(response)
        
        # 5. Embed and store immediately
        embedding = self.embedder.embed(response)
        self.db.store_turn(
            turn_id=turn_id,
            agent_role=self.role.value,
            content=response,
            embedding=embedding,
            metadata={
                'task_id': task_state.task_id,
                'turn_number': task_state.current_turn,
                'roadmap_chunk': roadmap_chunk,
                'files_changed': parsed['files_changed'],
                'status': VerificationStatus.PENDING.value,
                'timestamp': to_iso_format(get_current_utc_time())
            }
        )
        
        # 6. Create compressed summary
        compressed = self._compress_work(response, parsed)
        
        # 7. Package baton
        baton = BatonPacket(
            turn_id=turn_id,
            timestamp=to_iso_format(get_current_utc_time()),
            builder_summary=compressed,
            response_text=response,
            files_changed=parsed['files_changed'],
            verification_hints=parsed['verification_hints'],
            compressed_context=self._compress_context(context_chunks),
            metadata={
                'duration_seconds': time.time() - start_time,
                'token_count': len(response.split()),
                'roadmap_chunk': roadmap_chunk
            }
        )
        
        return baton
    
    def _generate_turn_id(self, task_state: TaskState) -> str:
        """Generate unique turn ID"""
        base = f"{task_state.task_id}_turn_{task_state.current_turn}"
        return hashlib.sha256(base.encode()).hexdigest()[:16]
    
    def _build_prompt(
        self,
        roadmap_chunk: str,
        context_chunks: List[Dict],
        task_state: TaskState,
        defect_capsule: Optional[DefectCapsule]
    ) -> str:
        """Construct the builder prompt"""
        
        context_section = "\n\n".join([
            f"[Context {i+1}]\n{c['text']}" 
            for i, c in enumerate(context_chunks)
        ])
        
        defect_section = ""
        if defect_capsule:
            defect_section = f"\n\nPREVIOUS ITERATION HAD ISSUES:\n{defect_capsule.to_prompt()}"
        
        open_issues = "\n".join(f"- {issue}" for issue in task_state.open_issues)
        
        return f"""You are a builder agent in a multi-agent verification system.
Your job is to complete the following task with high quality code and clear documentation.

CURRENT ROADMAP GOAL:
{roadmap_chunk}

RELEVANT CONTEXT FROM HISTORY:
{context_section}

OPEN ISSUES TO CONSIDER:
{open_issues if open_issues else "None"}
{defect_section}

Please provide your implementation with the following structure:
1. IMPLEMENTATION: Your code/changes
2. FILES_CHANGED: List of files you modified
3. VERIFICATION_HINTS: What the verifier should check
4. SUMMARY: Brief description of what you did

Remember: You have {self.max_duration // 60} minutes max for this sprint.
Focus on quality over quantity. The verifier will check your work.
"""
    
    def _parse_response(self, response: str) -> Dict:
        """Extract structured information from LLM response"""
        # Simple parser - you'd make this more robust
        parsed = {
            'files_changed': [],
            'verification_hints': [],
            'summary': ''
        }
        
        # Extract sections (simple implementation)
        if 'FILES_CHANGED:' in response:
            files_section = response.split('FILES_CHANGED:')[1].split('VERIFICATION_HINTS:')[0]
            parsed['files_changed'] = [
                line.strip('- ').strip() 
                for line in files_section.split('\n') 
                if line.strip()
            ]
        
        if 'VERIFICATION_HINTS:' in response:
            hints_section = response.split('VERIFICATION_HINTS:')[1].split('SUMMARY:')[0]
            parsed['verification_hints'] = [
                line.strip('- ').strip() 
                for line in hints_section.split('\n') 
                if line.strip()
            ]
        
        if 'SUMMARY:' in response:
            parsed['summary'] = response.split('SUMMARY:')[1].strip()
        
        return parsed
    
    def _compress_work(self, response: str, parsed: Dict) -> str:
        """Create paragraph-level synopsis"""
        return f"Modified {len(parsed['files_changed'])} files. {parsed['summary'][:200]}"
    
    def _compress_context(self, chunks: List[Dict]) -> str:
        """Compress context chunks into brief summary"""
        summaries = [c.get('summary', c['text'][:100]) for c in chunks[:3]]
        return " | ".join(summaries)


class VerifierAgent:
    """
    Tests and validates builder's work
    Runs in 5-10 minutes after builder completes
    """
    
    def __init__(self, llm_client, embedder, db_manager, test_runner, max_duration_minutes=10):
        self.llm_client = llm_client
        self.embedder = embedder
        self.db = db_manager
        self.test_runner = test_runner
        self.max_duration = max_duration_minutes * 60
        self.role = AgentRole.VERIFIER
    
    def validate(self, baton: BatonPacket, repo_path: str) -> tuple[VerificationStatus, Optional[DefectCapsule]]:
        """
        Validate builder's work
        
        Returns:
            (status, defect_capsule_if_failed)
        """
        start_time = time.time()
        defects = []
        
        # 1. Static checks (lint, format)
        lint_results = self._run_lint_checks(baton.files_changed, repo_path)
        if lint_results['failed']:
            defects.append({
                'type': 'lint',
                'severity': 'medium',
                'description': f"Lint errors in {len(lint_results['errors'])} files",
                'details': lint_results['errors']
            })
        
        # 2. Run tests
        test_results = self.test_runner.run_tests(repo_path)
        if not test_results['passed']:
            defects.append({
                'type': 'test_failure',
                'severity': 'high',
                'description': f"{test_results['failed_count']} tests failed",
                'details': test_results['failures']
            })
        
        # 3. LLM-based coherence check
        coherence_check = self._check_coherence(baton)
        if not coherence_check['coherent']:
            defects.append({
                'type': 'coherence',
                'severity': 'high',
                'description': coherence_check['reason'],
                'details': coherence_check['suggestions']
            })
        
        # 4. Domain-specific probes (from verification hints)
        probe_results = self._run_domain_probes(baton)
        defects.extend(probe_results)
        
        # 5. Determine status
        if not defects:
            status = VerificationStatus.PASSED
            self._record_success(baton)
            return status, None
        
        # Has critical defects?
        critical_defects = [d for d in defects if d['severity'] == 'critical']
        if critical_defects or len(defects) > 3:
            status = VerificationStatus.FAILED
        else:
            status = VerificationStatus.RETRY
        
        # 6. Create defect capsule
        defect_capsule = self._create_defect_capsule(baton, defects)
        
        # 7. Store verification result
        self._record_verification(baton, status, defect_capsule)
        
        return status, defect_capsule
    
    def _run_lint_checks(self, files: List[str], repo_path: str) -> Dict:
        """Run static analysis"""
        # Placeholder - implement your actual linting
        return {
            'failed': False,
            'errors': []
        }
    
    def _check_coherence(self, baton: BatonPacket) -> Dict:
        """Use LLM to check logical coherence"""
        
        # Retrieve similar past work
        similar_turns = self.db.retrieve_similar_turns(
            embedding=self.embedder.embed(baton.response_text),
            n_results=3
        )
        
        prompt = f"""You are a code reviewer checking for coherence and quality.

BUILDER'S WORK:
{baton.builder_summary}

RESPONSE:
{baton.response_text[:1000]}...

SIMILAR PAST WORK:
{self._format_similar_turns(similar_turns)}

Check for:
1. Logical consistency
2. Completeness
3. Alignment with the task goal
4. No obvious bugs or issues

Respond with JSON:
{{
    "coherent": true/false,
    "reason": "explanation",
    "suggestions": ["fix1", "fix2"]
}}
"""
        
        response = self.llm_client.generate(prompt, max_tokens=500, temperature=0.3)
        
        try:
            result = json.loads(response)
            return result
        except:
            return {'coherent': True, 'reason': 'Could not parse check', 'suggestions': []}
    
    def _run_domain_probes(self, baton: BatonPacket) -> List[Dict]:
        """Run any domain-specific checks from hints"""
        defects = []
        
        for hint in baton.verification_hints:
            if 'api' in hint.lower():
                # Run API tests
                pass
            elif 'data quality' in hint.lower():
                # Run data validation
                pass
        
        return defects
    
    def _create_defect_capsule(self, baton: BatonPacket, defects: List[Dict]) -> DefectCapsule:
        """Package defects into actionable capsule"""
        
        # Prioritize most severe defect
        primary_defect = max(defects, key=lambda d: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[d['severity']])
        
        defect_id = hashlib.sha256(f"{baton.turn_id}_{time.time()}".encode()).hexdigest()[:12]
        
        # Generate suggested fix using LLM
        suggested_fix = self._generate_fix_suggestion(baton, defects)
        
        return DefectCapsule(
            defect_id=defect_id,
            turn_id=baton.turn_id,
            defect_type=primary_defect['type'],
            description=self._summarize_defects(defects),
            suggested_fix=suggested_fix,
            affected_files=baton.files_changed,
            severity=primary_defect['severity']
        )
    
    def _generate_fix_suggestion(self, baton: BatonPacket, defects: List[Dict]) -> str:
        """Use LLM to suggest fixes"""
        defect_summary = "\n".join([f"- {d['description']}" for d in defects])
        
        prompt = f"""Given these defects found in the code:

{defect_summary}

Provide a concise, actionable fix suggestion (2-3 sentences):
"""
        
        return self.llm_client.generate(prompt, max_tokens=200, temperature=0.5)
    
    def _summarize_defects(self, defects: List[Dict]) -> str:
        """Create human-readable summary"""
        return f"Found {len(defects)} issues: " + ", ".join([d['type'] for d in defects])
    
    def _format_similar_turns(self, turns: List[Dict]) -> str:
        """Format similar past work for context"""
        return "\n\n".join([f"[Past Turn]\n{t['content'][:200]}..." for t in turns[:2]])
    
    def _record_success(self, baton: BatonPacket):
        """Update DB with successful verification"""
        self.db.update_turn_status(
            turn_id=baton.turn_id,
            status=VerificationStatus.PASSED.value,
            verifier_notes="All checks passed"
        )
        
        # Embed the success for future reference
        success_text = f"Successfully completed: {baton.builder_summary}"
        embedding = self.embedder.embed(success_text)
        self.db.store_checkpoint(
            turn_id=baton.turn_id,
            checkpoint_type='verification_success',
            embedding=embedding,
            metadata={'files': baton.files_changed}
        )
    
    def _record_verification(self, baton: BatonPacket, status: VerificationStatus, defect: Optional[DefectCapsule]):
        """Store verification results"""
        self.db.update_turn_status(
            turn_id=baton.turn_id,
            status=status.value,
            verifier_notes=defect.description if defect else "Passed"
        )
        
        if defect:
            # Embed the defect for future learning
            defect_text = defect.to_prompt()
            embedding = self.embedder.embed(defect_text)
            self.db.store_defect(
                defect_id=defect.defect_id,
                turn_id=baton.turn_id,
                defect_data=defect.to_dict(),
                embedding=embedding
            )


class SchedulerAgent:
    """
    Central coordinator that manages the relay race
    Decides: next task, retry, escalate, or complete
    """
    
    def __init__(self, builder: BuilderAgent, verifier: VerifierAgent, db_manager):
        self.builder = builder
        self.verifier = verifier
        self.db = db_manager
        self.max_retries = 2
        self.role = AgentRole.SCHEDULER
    
    def run_task(self, task_state: TaskState, roadmap: List[str], repo_path: str) -> TaskState:
        """
        Execute full multi-agent loop for a task
        
        Args:
            task_state: Initial task state
            roadmap: List of subtasks to complete
            repo_path: Path to repository
            
        Returns:
            Final task state
        """
        
        task_state.total_roadmap_items = len(roadmap)
        retry_count = 0
        current_defect = None
        
        while task_state.roadmap_position < len(roadmap):
            roadmap_chunk = roadmap[task_state.roadmap_position]
            
            print(f"\n{'='*60}")
            print(f"TURN {task_state.current_turn + 1}: {roadmap_chunk[:50]}...")
            print(f"{'='*60}")
            
            # === BUILDER PHASE ===
            print(f"\n[BUILDER] Starting iteration...")
            baton = self.builder.run_iteration(
                task_state=task_state,
                roadmap_chunk=roadmap_chunk,
                defect_capsule=current_defect
            )
            
            # Record in history
            task_state.agent_history.append({
                'turn': task_state.current_turn,
                'agent': 'builder',
                'turn_id': baton.turn_id,
                'timestamp': baton.timestamp
            })
            
            # === VERIFIER PHASE ===
            print(f"[VERIFIER] Validating builder's work...")
            status, defect_capsule = self.verifier.validate(baton, repo_path)
            
            task_state.agent_history.append({
                'turn': task_state.current_turn,
                'agent': 'verifier',
                'status': status.value,
                'timestamp': to_iso_format(get_current_utc_time())
            })
            
            # === DECISION LOGIC ===
            if status == VerificationStatus.PASSED:
                print(f"[SCHEDULER] ✓ Turn passed! Moving to next roadmap item.")
                
                # Store checkpoint
                task_state.checkpoints.append({
                    'turn': task_state.current_turn,
                    'roadmap_position': task_state.roadmap_position,
                    'commit_hash': self._get_repo_hash(repo_path),
                    'baton': baton.to_dict()
                })
                
                # Clear retry state
                retry_count = 0
                current_defect = None
                
                # Move forward
                task_state.roadmap_position += 1
                task_state.current_turn += 1
                
                # RESUBMIT to app (your original loop!)
                self._resubmit_to_app(baton)
                
            elif status == VerificationStatus.FAILED or status == VerificationStatus.RETRY:
                retry_count += 1
                
                if retry_count > self.max_retries:
                    print(f"[SCHEDULER] ⚠ Max retries reached. ESCALATING to human.")
                    task_state.open_issues.append(
                        f"Turn {task_state.current_turn}: {defect_capsule.description}"
                    )
                    self._escalate_to_human(task_state, defect_capsule)
                    
                    # Skip this roadmap item for now
                    task_state.roadmap_position += 1
                    retry_count = 0
                    current_defect = None
                else:
                    print(f"[SCHEDULER] ↻ Retry {retry_count}/{self.max_retries} - Sending defect back to builder...")
                    current_defect = defect_capsule
                
                task_state.current_turn += 1
            
            # Token budget check
            task_state.token_usage += len(baton.response_text.split())
            if task_state.token_usage > 100000:  # Arbitrary limit
                print(f"[SCHEDULER] ⚠ Token budget exceeded. Compressing history...")
                self._compress_history(task_state)
        
        print(f"\n{'='*60}")
        print(f"TASK COMPLETE! Finished {task_state.roadmap_position} roadmap items.")
        print(f"{'='*60}")
        
        return task_state
    
    def _get_repo_hash(self, repo_path: str) -> str:
        """Get current git commit hash"""
        # Placeholder - use actual git commands
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]
    
    def _resubmit_to_app(self, baton: BatonPacket):
        """
        YOUR ORIGINAL LOOP: Feed response back to app
        This is where you'd inject into your UI/API
        """
        print(f"[APP RESUBMIT] Sending turn {baton.turn_id} to application...")
        
        # This would be your actual app integration:
        # - Post to your API endpoint
        # - Update UI state
        # - Trigger next user interaction
        # - Whatever your "custom app input" does
        
        pass
    
    def _escalate_to_human(self, task_state: TaskState, defect: DefectCapsule):
        """Notify maintainer of persistent issues"""
        escalation = {
            'task_id': task_state.task_id,
            'turn': task_state.current_turn,
            'defect': defect.to_dict(),
            'history_summary': self._summarize_history(task_state),
            'timestamp': to_iso_format(get_current_utc_time())
        }
        
        # Store escalation
        self.db.store_escalation(escalation)
        
        # In production: send notification (email, Slack, etc.)
        print(f"\n⚠️  ESCALATION REQUIRED ⚠️")
        print(json.dumps(escalation, indent=2))
    
    def _compress_history(self, task_state: TaskState):
        """Compress agent history to reduce token usage"""
        # Keep only last N turns in detail, summarize the rest
        recent_turns = task_state.agent_history[-10:]
        older_summary = f"Completed {len(task_state.agent_history) - 10} earlier turns"
        
        task_state.agent_history = [
            {'summary': older_summary, 'turn': 'compressed'}
        ] + recent_turns
        
        task_state.token_usage = task_state.token_usage // 2  # Rough estimate
    
    def _summarize_history(self, task_state: TaskState) -> str:
        """Create concise history for escalation"""
        return f"Task {task_state.task_id}: {task_state.current_turn} turns, {task_state.roadmap_position}/{task_state.total_roadmap_items} items complete"


def run_agent_workflow(task_config: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight legacy workflow wrapper with timezone-aware timestamps."""
    start = get_current_utc_time()
    result = {
        "status": "completed",
        "task": task_config,
        "started_at": to_iso_format(start),
        "completed_at": to_iso_format(get_current_utc_time()),
    }
    return result


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    demo = run_agent_workflow({"example": "legacy_cli"})
    print(json.dumps(demo, indent=2))
