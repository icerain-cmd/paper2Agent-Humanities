import pytest

from paper2humanities import (
    DialogueAction,
    EpistemicStatement,
    EvidenceVoice,
    PaperAgent,
    ProvenanceError,
    ReviewStatus,
    ScholarlyDialogue,
    StatementType,
)


def agent(paper_id, statement_id):
    statement = EpistemicStatement(
        statement_id=statement_id,
        statement_type=StatementType.AUTHOR_CLAIM,
        text=f"Claim from {paper_id}",
        paper_id=paper_id,
        source_id=f"source-{paper_id}",
        author=f"Author {paper_id}",
        page=1,
        evidence_span=f"Evidence from {paper_id}",
        citation="PDF p.1",
        evidence_voice=EvidenceVoice.AUTHOR,
        review_status=ReviewStatus.REVIEWED,
    )
    return PaperAgent(
        paper_id,
        f"Paper {paper_id}",
        f"Author {paper_id}",
        f"source-{paper_id}",
        "a" * 64,
        [],
        [statement],
    )


def test_cross_paper_synthesis_preserves_provenance():
    a, b = agent("a", "a1"), agent("b", "b1")
    dialogue = ScholarlyDialogue([a, b])
    turn = dialogue.create_turn(
        action=DialogueAction.SYNTHESIZE,
        actor_paper="a",
        statement_id="syn1",
        text="The papers differ on the status of mediation.",
        support_ids=("a1", "b1"),
    )
    assert turn.statement.statement_type == StatementType.AI_SYNTHESIS
    assert turn.statement.derived_from == ("a1", "b1")


def test_cross_paper_synthesis_requires_two_papers():
    a, b = agent("a", "a1"), agent("b", "b1")
    dialogue = ScholarlyDialogue([a, b])
    with pytest.raises(ProvenanceError):
        dialogue.create_turn(
            action=DialogueAction.COMPARE,
            actor_paper="a",
            statement_id="cmp1",
            text="comparison",
            support_ids=("a1",),
        )


def test_paper_agent_response_cannot_borrow_other_paper_evidence():
    a, b = agent("a", "a1"), agent("b", "b1")
    dialogue = ScholarlyDialogue([a, b])
    with pytest.raises(ProvenanceError):
        dialogue.create_turn(
            action=DialogueAction.RESPOND,
            actor_paper="a",
            statement_id="r1",
            text="response",
            support_ids=("a1", "b1"),
            target_paper="b",
        )


def test_critique_requires_explicit_target_and_own_evidence():
    a, b = agent("a", "a1"), agent("b", "b1")
    dialogue = ScholarlyDialogue([a, b])
    turn = dialogue.create_turn(
        action=DialogueAction.CRITIQUE,
        actor_paper="a",
        statement_id="k1",
        text="A source-bounded critique.",
        support_ids=("a1",),
        target_paper="b",
    )
    assert turn.statement.statement_type == StatementType.CRITIQUE
    assert turn.statement.target_paper == "b"


def test_unknown_critique_target_paper_fails():
    a, b = agent("a", "a1"), agent("b", "b1")
    dialogue = ScholarlyDialogue([a, b])
    with pytest.raises(ProvenanceError):
        dialogue.create_turn(
            action=DialogueAction.CRITIQUE,
            actor_paper="a",
            statement_id="k-missing",
            text="critique",
            support_ids=("a1",),
            target_paper="missing-paper",
        )


def test_research_question_remains_unresolved_not_author_claim():
    a, b = agent("a", "a1"), agent("b", "b1")
    dialogue = ScholarlyDialogue([a, b])
    turn = dialogue.create_turn(
        action=DialogueAction.GENERATE_RESEARCH_QUESTION,
        actor_paper="a",
        statement_id="rq1",
        text="How does mediation alter the distance relation?",
        support_ids=("a1", "b1"),
    )
    assert turn.statement.statement_type == StatementType.UNRESOLVED
