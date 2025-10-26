from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, DefaultDict
from collections import defaultdict, deque
import asyncio
import uuid
import threading

@dataclass
class BusMessage:
    id: str
    topic: str            # e.g. "artifact.backend.schema"
    frm: str              # agent type
    to: Optional[str]     # None => broadcast
    payload: Dict[str, Any]
    ts: str

class AgentCommunicationBus:
    """
    Hybrid sync/async bus:
      - .publish(...) and .broadcast_artifact(...) are thread-safe
      - subscribers can pull (sync) or await (async) by topic
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._shared_context: Dict[str, Dict[str, Any]] = {}
        self._queues: DefaultDict[str, deque[BusMessage]] = defaultdict(deque)
        self._async_conds: DefaultDict[str, asyncio.Condition] = defaultdict(asyncio.Condition)

    # ---------- ARTIFACT CONTEXT ----------
    def broadcast_artifact(self, agent_type: str, artifact_type: str, data: Dict[str, Any]) -> BusMessage:
        key = f"{agent_type}.{artifact_type}"
        msg = BusMessage(
            id=str(uuid.uuid4()),
            topic=f"artifact.{key}",
            frm=agent_type,
            to=None,
            payload={"data": data},
            ts=datetime.now(timezone.utc).isoformat()
        )
        with self._lock:
            self._shared_context[key] = {"data": data, "agent": agent_type, "timestamp": msg.ts}
            self._queues[msg.topic].append(msg)
        # Wake async waiters if an event loop is running
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._notify_async(msg.topic))
        except RuntimeError:  # pragma: no cover
            # This is expected in a purely synchronous context (like tests)
            pass
        return msg

    def get_shared_context(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._shared_context)

    # ---------- MESSAGING ----------
    def publish(self, *, topic: str, frm: str, to: Optional[str], payload: Dict[str, Any]) -> BusMessage:
        msg = BusMessage(
            id=str(uuid.uuid4()),
            topic=topic, frm=frm, to=to, payload=payload,
            ts=datetime.now(timezone.utc).isoformat()
        )
        with self._lock:
            self._queues[topic].append(msg)
        # Wake async waiters if an event loop is running
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._notify_async(topic))
        except RuntimeError:  # pragma: no cover
            # This is expected in a purely synchronous context (like tests)
            pass
        return msg

    def drain(self, topic: str, limit: int = 32) -> List[BusMessage]:
        out: List[BusMessage] = []
        with self._lock:
            q = self._queues[topic]
            for _ in range(min(limit, len(q))):
                out.append(q.popleft())
        return out

    async def wait_for(self, topic: str, timeout: Optional[float] = None) -> List[BusMessage]:
        cond = self._async_conds[topic]
        async with cond:
            if timeout is None:
                await cond.wait()
            else:
                try:
                    await asyncio.wait_for(cond.wait(), timeout)
                except asyncio.TimeoutError:
                    return []
        return self.drain(topic)

    async def _notify_async(self, topic: str):
        cond = self._async_conds[topic]
        async with cond:
            cond.notify_all()
