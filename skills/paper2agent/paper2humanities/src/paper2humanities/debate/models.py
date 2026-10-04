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
    REVISION="REVISION"
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
    thesis: str | None = None
    target_claim: str | None = None
    stance_update: str | None = None
    unresolved_point: str | None = None

    def to_dict(self):
        d=asdict(self)
        d["action"]=self.action.value
        return d

    @classmethod
    def from_dict(cls,data:dict)->"DebateTurn":
        return cls(
            turn_id=data["turn_id"],
            speaker_agent_id=data["speaker_agent_id"],
            target_agent_ids=list(data.get("target_agent_ids") or []),
            action=DebateAction(data["action"]),
            text=data.get("text",""),
            support_ids=list(data.get("support_ids") or []),
            pages=[int(x) for x in (data.get("pages") or [])],
            evidence=list(data.get("evidence") or []),
            semantic_support=data.get("semantic_support","UNSUPPORTED"),
            qualification=data.get("qualification"),
            context_turn_ids=list(data.get("context_turn_ids") or []),
            verification_status=data.get("verification_status","PASS"),
            thesis=data.get("thesis"),
            target_claim=data.get("target_claim"),
            stance_update=data.get("stance_update"),
            unresolved_point=data.get("unresolved_point"),
        )

@dataclass
class DebateSession:
    topic: str
    participant_ids: list[str]
    max_turns: int = 10
    protocol_version: str = "2.0"
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

    @classmethod
    def from_dict(cls,data:dict)->"DebateSession":
        return cls(
            topic=data["topic"],
            participant_ids=list(data.get("participant_ids") or []),
            max_turns=int(data.get("max_turns",10)),
            protocol_version=data.get("protocol_version","1.0"),
            session_id=data["session_id"],
            current_turn=int(data.get("current_turn",0)),
            status=data.get("status","READY"),
            active_issue=data.get("active_issue"),
            turns=[DebateTurn.from_dict(x) for x in data.get("turns") or []],
            interventions=list(data.get("interventions") or []),
        )
