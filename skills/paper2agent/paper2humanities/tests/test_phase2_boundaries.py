from dataclasses import replace
from pathlib import Path
import json
import pytest

from paper2humanities import (
    DialogueAction,
    EpistemicStatement,
    EvidenceVoice,
    PaperAgent,
    ProvenanceError,
    RelationType,
    ReviewStatus,
    ScholarlyDialogue,
    SemanticSupportStatus,
    StatementType,
    validate_turn_for_publication,
)

ROOT = Path(__file__).resolve().parents[1]


def grounded(paper_id, source_id, edition_id, sid, text="evidence"):
    return EpistemicStatement(
        statement_id=sid,
        statement_type=StatementType.AUTHOR_CLAIM,
        text=f"claim {sid}",
        paper_id=paper_id,
        source_id=source_id,
        author="Walter Benjamin",
        page=1,
        evidence_span=text,
        citation="source p.1",
        edition_id=edition_id,
        evidence_voice=EvidenceVoice.AUTHOR,
        review_status=ReviewStatus.REVIEWED,
    )


def edition_agent(edition):
    paper = edition
    source = f"source-{edition}"
    statement = grounded(paper, source, edition, f"{edition}-s")
    return PaperAgent(
        paper, f"Paper {edition}", "Walter Benjamin", source, "a" * 64,
        [], [statement], edition_id=edition,
    )


def test_v2_statement_cannot_be_loaded_as_v3_agent_evidence():
    statement = grounded(
        "benjamin-artwork-v3", "source-benjamin-artwork-v3",
        "benjamin-artwork-v2", "wrong-edition",
    )
    with pytest.raises(ValueError, match="edition boundary"):
        PaperAgent(
            "benjamin-artwork-v3", "V3", "Walter Benjamin",
            "source-benjamin-artwork-v3", "b" * 64, [], [statement],
            edition_id="benjamin-artwork-v3",
        )


def test_v3_response_cannot_use_v2_support():
    v2 = edition_agent("benjamin-artwork-v2")
    v3 = edition_agent("benjamin-artwork-v3")
    dialogue = ScholarlyDialogue([v2, v3])
    with pytest.raises(ProvenanceError, match="own paper evidence"):
        dialogue.create_turn(
            action=DialogueAction.RESPOND,
            actor_paper="benjamin-artwork-v3",
            statement_id="v3-response",
            text="response",
            support_ids=("benjamin-artwork-v2-s",),
            target_paper="benjamin-artwork-v2",
        )


def test_cross_edition_synthesis_preserves_both_source_agents():
    v2 = edition_agent("benjamin-artwork-v2")
    v3 = edition_agent("benjamin-artwork-v3")
    dialogue = ScholarlyDialogue([v2, v3])
    turn = dialogue.create_turn(
        action=DialogueAction.SYNTHESIZE,
        actor_paper="benjamin-artwork-v2",
        statement_id="cross-edition-synthesis",
        text="The editions differ on this passage.",
        support_ids=("benjamin-artwork-v2-s", "benjamin-artwork-v3-s"),
    )
    assert turn.statement.statement_type == StatementType.AI_SYNTHESIS
    assert set(turn.support_ids) == {"benjamin-artwork-v2-s", "benjamin-artwork-v3-s"}


def test_lee_2019_temporal_corpus_blocks_later_concepts():
    lee = PaperAgent.from_json(ROOT / "fixtures" / "lee-aura-2019-agent.json")
    for term in ["아투라", "기계세", "Mechanocene", "기술생성시대", "공진주체 WE", "마찰의 투명성", "생성 아우라"]:
        with pytest.raises(ValueError, match="temporal/corpus boundary"):
            lee.validate_output_text(f"Lee 2019 response imports {term}.")


def test_lee_dialogue_response_cannot_import_later_concept():
    lee = PaperAgent.from_json(ROOT / "fixtures" / "lee-aura-2019-agent.json")
    other = edition_agent("benjamin-artwork-v3")
    dialogue = ScholarlyDialogue([lee, other])
    with pytest.raises(ProvenanceError, match="temporal/corpus boundary"):
        dialogue.create_turn(
            action=DialogueAction.RESPOND,
            actor_paper="lee-aura-2019",
            statement_id="lee-late-contamination",
            text="이 비판은 생성 아우라로 해결된다.",
            support_ids=("lee-c-transparent",),
            target_paper="benjamin-artwork-v3",
        )


def test_semantic_review_required_before_dialogue_publication():
    a = edition_agent("benjamin-artwork-v2")
    b = edition_agent("benjamin-artwork-v3")
    dialogue = ScholarlyDialogue([a, b])
    turn = dialogue.create_turn(
        action=DialogueAction.CRITIQUE,
        actor_paper="benjamin-artwork-v2",
        statement_id="critique-1",
        text="A source-bounded tension.",
        support_ids=("benjamin-artwork-v2-s",),
        target_paper="benjamin-artwork-v3",
        relation_type=RelationType.TENSIONS_WITH,
    )
    with pytest.raises(ProvenanceError, match="REVIEWED"):
        validate_turn_for_publication(turn)
    reviewed = replace(
        turn,
        review_status=ReviewStatus.REVIEWED,
        semantic_support=SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
    )
    validate_turn_for_publication(reviewed)
    unsupported = replace(reviewed, semantic_support=SemanticSupportStatus.UNSUPPORTED)
    with pytest.raises(ProvenanceError, match="not publishable"):
        validate_turn_for_publication(unsupported)


def test_source_map_keeps_v2_mapping_separate_from_v3():
    data = json.loads((ROOT / "evals" / "lee-benjamin-source-map.json").read_text())
    assert data["status"] == "PRE_APPROVAL_MAPPING"
    assert data["benjamin_agent_status"] == "PENDING_SOURCE_APPROVAL"
    assert data["counts"]["EXACT"] == 0
    v2 = [m for m in data["mappings"] if m["benjamin_edition_id"] == "benjamin-artwork-v2"]
    v3 = [m for m in data["mappings"] if m["benjamin_edition_id"] == "benjamin-artwork-v3"]
    assert len(v2) == 1 and v2[0]["benjamin_gs_page"] == 359
    assert len(v3) == 4
    assert all(m["mapping_status"] == "STRONG_MATCH" for m in data["mappings"])
