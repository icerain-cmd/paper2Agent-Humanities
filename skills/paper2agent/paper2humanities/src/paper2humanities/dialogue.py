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


@dataclass(frozen=True, slots=True)
class DialogueTurn:
    action: DialogueAction
    actor: str
    statement: EpistemicStatement
    support_ids: tuple[str, ...]


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
    ) -> DialogueTurn:
        if actor_paper not in self.agents:
            raise ProvenanceError(f"unknown actor paper: {actor_paper}")
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
            derived_from=support_ids,
            target_statement=target_statement,
            target_paper=target_paper,
            unresolved_reason=unresolved_reason,
            review_status=ReviewStatus.NEEDS_REVIEW,
        )
        return DialogueTurn(action, actor_paper, statement, support_ids)
