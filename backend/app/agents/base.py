"""
Base Agent class + Agent-to-Agent (A2A) message protocol.

Each agent communicates via a structured AgentMessage so the orchestrator
can route, log, and stream progress to the UI -- this is our lightweight
A2A (agent-to-agent) protocol layer.
"""
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    type: str  # "task" | "result" | "error" | "status"
    payload: Any
    timestamp: float = field(default_factory=time.time)


class BaseAgent:
    name: str = "base_agent"

    def __init__(self, llm_client):
        self.llm = llm_client

    async def run(self, task_payload: dict) -> AgentMessage:
        raise NotImplementedError

    def emit_status(self, text: str) -> AgentMessage:
        return AgentMessage(sender=self.name, receiver="orchestrator", type="status", payload=text)
