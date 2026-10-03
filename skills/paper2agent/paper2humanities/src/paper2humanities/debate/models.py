from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any
import uuid

class DebateAction(str, Enum):
    POSITION="POSITION"
    RESPONSE="RESPONSE"
    CRITIQUE="CRITIQUE"
    QUESTION="QUESTION"
    REBUTTAL="REBUTTAL"
    CLARIFICATION="CLARIFICATION"
    CLOSING="CLOSING"

@dataclass
class DebateTurn:
    turn_id: str
    speaker_agent_id: str
    target_agent_ids: list[str]
    action: DebateAction
    text: str
    support_ids: list[str]
    pages: list[int]
    evidence: list[dict[str, Any]]
    semantic_support: str
    qualification: str | None = None
    context_turn_ids: list[str] = field(default_factory=list)
    verification_status: str = "PASS"
    def to_dict(self): return asdict(self)

@dataclass
class DebateSession:
    topic: str
    participant_ids: list[str]
    max_turns: int = 8
    session_id: str = field(default_factory=lambda: f"debate-{uuid.uuid4()}")
    current_turn: int = 0
    status: str = "READY"
    active_issue: str | None = None
    turns: list[DebateTurn] = field(default_factory=list)
    interventions: list[dict[str, Any]] = field(default_factory=list)
    def to_dict(self):
        d=asdict(self)
        d["turns"]=[t.to_dict() for t in self.turns]
        return d
