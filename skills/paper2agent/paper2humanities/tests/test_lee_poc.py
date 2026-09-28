import json
from pathlib import Path

from paper2humanities import (
    EvidenceVoice,
    PaperAgent,
    PaperEvidenceIndex,
    StatementType,
    evaluate_agent,
    validate_against_source,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load():
    agent = PaperAgent.from_json(FIXTURES / "lee-aura-2019-agent.json")
    index = PaperEvidenceIndex.from_dict(
        json.loads((FIXTURES / "lee-aura-2019-evidence-index.json").read_text())
    )
    return agent, index


def test_lee_agent_identity_and_source_hash():
    agent, index = load()
    assert agent.title == "기술편집시대 아우라 연구의 방향성"
    assert agent.author == "이용욱"
    assert agent.source_sha256 == index.source_sha256
    assert index.source_sha256 == "864e341de1fa049fd3c5285c882125967671aebde4ef37f5d9156613d061adae"


def test_all_lee_quotes_and_author_claims_are_page_traceable():
    agent, index = load()
    grounded = [
        item
        for item in agent.store.values()
        if item.statement_type in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}
    ]
    assert grounded
    for statement in grounded:
        validate_against_source(statement, index)


def test_unsupported_author_claim_gate_is_zero():
    agent, index = load()
    report = evaluate_agent(agent, index)
    assert report["unsupported_author_claim"] == 0
    assert report["unsupported_claim_rate"] == 0.0
    assert report["page_level_traceability"] == 1.0
    assert report["source_attribution_accuracy"] == 1.0


def test_retrieval_question_a_returns_grounded_aura_material():
    agent, _ = load()
    results = agent.retrieve("기술편집시대 아우라 투명화 신뢰화")
    assert results
    assert any(item.statement_id == "lee-c-tension" for item in results)
    assert all(item.statement_type != StatementType.AI_SYNTHESIS for item in results[:3])


def test_attribution_question_b_keeps_lee_benjamin_and_ai_separate():
    agent, _ = load()
    lee = agent.store.get("lee-c-transparent")
    benjamin = agent.store.get("lee-q-benjamin-second-tech")
    interpretation = agent.store.get("lee-i-distance")
    assert lee.statement_type == StatementType.AUTHOR_CLAIM and lee.author == "이용욱"
    assert benjamin.statement_type == StatementType.SOURCE_QUOTE
    assert benjamin.author.startswith("Walter Benjamin")
    assert benjamin.evidence_voice == EvidenceVoice.EXTERNAL
    assert interpretation.statement_type == StatementType.INTERPRETATION
    assert interpretation.author is None


def test_evidence_question_c_has_exact_page_and_citation():
    agent, index = load()
    claim = agent.store.get("lee-c-trust-definition")
    assert claim.page == 24
    assert "printed p.270" in claim.citation
    assert index.contains(claim.page, claim.evidence_span)
