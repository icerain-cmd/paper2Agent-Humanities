"""Evidence-bounded scholarly dialogue without winner/loser judging."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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

    @property
    def actor(self) -> str:
        return self.actor_paper


class ScholarlyDialogue:
    def __init__(self, agents: list[PaperAgent]):
        self.agents = {agent.paper_id: agent for agent in agents}
        if len(self.agents) != len(agents):
            raise ProvenanceError("paper_id values must be unique")

    def _lookup(self, statement_id: str) -> EpistemicStatement:
        for agent in self.agents.values():
            try:
                return agent.store.get(statement_id)
            except ProvenanceError:
                pass
        raise ProvenanceError(f"unknown dialogue support statement: {statement_id}")

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
            foreign = [item.statement_id for item in supports if item.paper_id != actor_paper]
            if foreign:
                raise ProvenanceError(
                    f"{action.value} paper agent may use only its own paper evidence: {foreign}"
                )
            if actor_agent.edition_id is not None:
                wrong_edition = [
                    item.statement_id for item in supports
                    if item.edition_id != actor_agent.edition_id
                ]
                if wrong_edition:
                    raise ProvenanceError(
                        f"{action.value} paper agent may use only its own edition evidence: {wrong_edition}"
                    )

        cross_actions = {
            DialogueAction.COMPARE,
            DialogueAction.SYNTHESIZE,
            DialogueAction.IDENTIFY_GAP,
            DialogueAction.GENERATE_RESEARCH_QUESTION,
        }
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
            edition_id=actor_agent.edition_id if action in own_evidence_actions else None,
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
            actor_edition_id=actor_agent.edition_id,
            target_paper=target_paper,
            target_statement_id=target_statement,
            statement=statement,
            support_ids=support_ids,
            relation_type=relation_type,
        )


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
