"""Evidence-bounded scholarly dialogue without winner/loser judging."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from .paper_agent import PaperAgent
from .schema import EpistemicStatement, ProvenanceError, ReviewStatus, StatementType


class DialogueAction(str, Enum):
    COMPARE = "COMPARE"
    QUESTION = "QUESTION"
    CRITIQUE = "CRITIQUE"
    RESPOND = "RESPOND"
    SYNTHESIZE = "SYNTHESIZE"
    IDENTIFY_GAP = "IDENTIFY_GAP"
    GENERATE_RESEARCH_QUESTION = "GENERATE_RESEARCH_QUESTION"


class RelationType(str, Enum):
    CONTRADICTS = "CONTRADICTS"
    TENSIONS_WITH = "TENSIONS_WITH"
    QUALIFIES = "QUALIFIES"
    EXTENDS = "EXTENDS"
    REFRAMES = "REFRAMES"
    NOT_ADDRESSED = "NOT_ADDRESSED"
    UNRESOLVED = "UNRESOLVED"


class SemanticSupportStatus(str, Enum):
    PROVENANCE_VALID = "PROVENANCE_VALID"
    SEMANTICALLY_SUPPORTED = "SEMANTICALLY_SUPPORTED"
    OVERSTATED = "OVERSTATED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class DialogueTurn:
    turn_id: str
    action: DialogueAction
    actor_paper: str
    actor_edition_id: str | None
    target_paper: str | None
    target_statement_id: str | None
    statement: EpistemicStatement
    support_ids: tuple[str, ...]
    relation_type: RelationType = RelationType.UNRESOLVED
    semantic_support: SemanticSupportStatus = SemanticSupportStatus.PROVENANCE_VALID
    review_status: ReviewStatus = ReviewStatus.NEEDS_REVIEW
    review_binding_sha256: str | None = None

    @property
    def actor(self) -> str:
        return self.actor_paper


class ScholarlyDialogue:
    def __init__(self, agents: list[PaperAgent]):
        self.agents = {agent.paper_id: agent for agent in agents}
        if len(self.agents) != len(agents):
            raise ProvenanceError("paper_id values must be unique")
        self.reviewed_turns: dict[str, EpistemicStatement] = {}

    def _lookup(self, statement_id: str) -> EpistemicStatement:
        if statement_id in self.reviewed_turns:
            return self.reviewed_turns[statement_id]
        for agent in self.agents.values():
            try:
                return agent.store.get(statement_id)
            except ProvenanceError:
                pass
        raise ProvenanceError(f"unknown dialogue support statement: {statement_id}")

    def register_reviewed_turn(self, turn: DialogueTurn) -> None:
        validate_turn_for_publication(turn)
        if turn.turn_id in self.reviewed_turns:
            raise ProvenanceError(f"duplicate reviewed dialogue turn: {turn.turn_id}")
        for agent in self.agents.values():
            try:
                agent.store.get(turn.turn_id)
            except ProvenanceError:
                continue
            raise ProvenanceError(f"dialogue turn id collides with source statement: {turn.turn_id}")
        self.reviewed_turns[turn.turn_id] = turn.statement

    def create_turn(
        self,
        *,
        action: DialogueAction,
        actor_paper: str,
        statement_id: str,
        text: str,
        support_ids: tuple[str, ...] = (),
        target_statement: str | None = None,
        target_paper: str | None = None,
        unresolved_reason: str | None = None,
        relation_type: RelationType = RelationType.UNRESOLVED,
    ) -> DialogueTurn:
        cross_actions = {
            DialogueAction.COMPARE,
            DialogueAction.SYNTHESIZE,
            DialogueAction.IDENTIFY_GAP,
            DialogueAction.GENERATE_RESEARCH_QUESTION,
        }
        if actor_paper == "synthesis-agent":
            if action not in cross_actions:
                raise ProvenanceError("synthesis-agent may only perform cross-paper synthesis operations")
            actor_agent = None
        else:
            if actor_paper not in self.agents:
                raise ProvenanceError(f"unknown actor paper: {actor_paper}")
            actor_agent = self.agents[actor_paper]
            try:
                actor_agent.validate_output_text(text)
            except ValueError as exc:
                raise ProvenanceError(str(exc)) from exc
        if target_paper and target_paper not in self.agents:
            raise ProvenanceError(f"unknown target paper: {target_paper}")
        if target_statement:
            self._lookup(target_statement)
        supports = [self._lookup(sid) for sid in support_ids]
        support_papers = {item.paper_id for item in supports if item.paper_id}

        own_evidence_actions = {
            DialogueAction.CRITIQUE,
            DialogueAction.RESPOND,
            DialogueAction.QUESTION,
        }
        if action in own_evidence_actions:
            foreign = [
                item.statement_id for item in supports
                if item.paper_id != actor_paper
                or item.source_id != actor_agent.source_id
                or item.edition_id != actor_agent.edition_id
                or item.statement_type not in {StatementType.AUTHOR_CLAIM, StatementType.SOURCE_QUOTE}
            ]
            if foreign:
                raise ProvenanceError(
                    f"{action.value} paper agent may use only its own paper evidence: {foreign}"
                )

        if action in cross_actions and len(support_papers) < 2:
            raise ProvenanceError(f"{action.value} requires provenance from at least two papers")

        if action in {DialogueAction.CRITIQUE, DialogueAction.RESPOND, DialogueAction.QUESTION}:
            if not (target_statement or target_paper):
                raise ProvenanceError(f"{action.value} requires an explicit target")

        if action == DialogueAction.CRITIQUE:
            stype = StatementType.CRITIQUE
        elif action == DialogueAction.RESPOND:
            stype = StatementType.INTERPRETATION
        elif action in {DialogueAction.QUESTION, DialogueAction.GENERATE_RESEARCH_QUESTION}:
            stype = StatementType.UNRESOLVED
            unresolved_reason = unresolved_reason or "Scholarly question remains open."
        else:
            stype = StatementType.AI_SYNTHESIS

        statement = EpistemicStatement(
            statement_id=statement_id,
            statement_type=stype,
            text=text,
            paper_id=actor_paper if action in own_evidence_actions else None,
            edition_id=actor_agent.edition_id if action in own_evidence_actions and actor_agent is not None else None,
            derived_from=support_ids,
            target_statement=target_statement,
            target_paper=target_paper,
            unresolved_reason=unresolved_reason,
            review_status=ReviewStatus.NEEDS_REVIEW,
        )
        return DialogueTurn(
            turn_id=statement_id,
            action=action,
            actor_paper=actor_paper,
            actor_edition_id=actor_agent.edition_id if actor_agent is not None else None,
            target_paper=target_paper,
            target_statement_id=target_statement,
            statement=statement,
            support_ids=support_ids,
            relation_type=relation_type,
        )


REVIEW_BINDING_FIELDS = (
    "turn_id", "text", "statement_type", "support_ids", "relation_type",
    "actor_paper", "actor_edition_id", "target_paper", "target_statement_id",
)


def review_binding_sha256(turn: DialogueTurn | dict) -> str:
    """Bind a semantic decision to the exact publication fields, in fixed JSON order."""
    if isinstance(turn, DialogueTurn):
        values = {
            "turn_id": turn.turn_id, "text": turn.statement.text,
            "statement_type": turn.statement.statement_type.value,
            "support_ids": list(turn.support_ids), "relation_type": turn.relation_type.value,
            "actor_paper": turn.actor_paper, "actor_edition_id": turn.actor_edition_id,
            "target_paper": turn.target_paper, "target_statement_id": turn.target_statement_id,
        }
    else:
        values = {key: turn[key] for key in REVIEW_BINDING_FIELDS}
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_turn_for_publication(turn: DialogueTurn) -> None:
    if turn.review_status != ReviewStatus.REVIEWED:
        raise ProvenanceError("dialogue turn requires human/reviewer REVIEWED status before publication")
    if turn.semantic_support not in {
        SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
        SemanticSupportStatus.PARTIALLY_SUPPORTED,
    }:
        raise ProvenanceError(
            f"dialogue turn semantic support is not publishable: {turn.semantic_support.value}"
        )
    if turn.review_binding_sha256 != review_binding_sha256(turn):
        raise ProvenanceError("SEMANTIC_REVIEW_STALE: reviewed turn differs from approved content")
