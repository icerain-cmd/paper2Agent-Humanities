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
    review_binding_sha256,
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
        review_binding_sha256=review_binding_sha256(turn),
    )
    validate_turn_for_publication(reviewed)
    unsupported = replace(reviewed, semantic_support=SemanticSupportStatus.UNSUPPORTED)
    with pytest.raises(ProvenanceError, match="not publishable"):
        validate_turn_for_publication(unsupported)


@pytest.mark.parametrize("text", [
    "erste Technik", "ersten Technik", "erster Technik", "erstes Technik",
    "zweite Technik", "zweiten Technik", "zweiter Technik", "zweites Technik",
])
def test_v3_lexical_defense_covers_german_inflections(text):
    v3 = edition_agent("benjamin-artwork-v3")
    with pytest.raises(ValueError, match="temporal/corpus boundary"):
        v3.validate_output_text(f"The phrase {text} belongs to V2.")


def test_v3_rejects_v2_support_even_without_v2_wording():
    dialogue = ScholarlyDialogue([
        edition_agent("benjamin-artwork-v2"), edition_agent("benjamin-artwork-v3")
    ])
    with pytest.raises(ProvenanceError, match="own paper evidence"):
        dialogue.create_turn(
            action=DialogueAction.CRITIQUE, actor_paper="benjamin-artwork-v3",
            statement_id="v3-mislabeled", text="A neutral sentence.",
            support_ids=("benjamin-artwork-v2-s",), target_paper="benjamin-artwork-v2",
        )


@pytest.mark.parametrize("change", [
    lambda t: replace(t, statement=replace(t.statement, text="Changed after review")),
    lambda t: replace(t, support_ids=("other-support",)),
    lambda t: replace(t, relation_type=RelationType.QUALIFIES),
    lambda t: replace(t, actor_edition_id="benjamin-artwork-v3"),
    lambda t: replace(t, target_paper="another-paper"),
    lambda t: replace(t, target_statement_id="another-target"),
])
def test_review_binding_invalidates_mutated_publication_fields(change):
    dialogue = ScholarlyDialogue([
        edition_agent("benjamin-artwork-v2"), edition_agent("benjamin-artwork-v3")
    ])
    turn = dialogue.create_turn(
        action=DialogueAction.CRITIQUE, actor_paper="benjamin-artwork-v2",
        statement_id="bound-turn", text="The reviewed text.",
        support_ids=("benjamin-artwork-v2-s",),
        target_paper="benjamin-artwork-v3", relation_type=RelationType.TENSIONS_WITH,
    )
    approved = replace(turn, review_status=ReviewStatus.REVIEWED,
                       semantic_support=SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
                       review_binding_sha256=review_binding_sha256(turn))
    validate_turn_for_publication(approved)
    with pytest.raises(ProvenanceError, match="SEMANTIC_REVIEW_STALE"):
        validate_turn_for_publication(change(approved))


@pytest.mark.parametrize("field,value", [
    ("text", "Changed after approval"),
    ("support_ids", ["b-v3-c-aura-withers"]),
    ("relation_type", "QUALIFIES"),
    ("actor_edition_id", "benjamin-artwork-v3"),
    ("target_paper", "benjamin-artwork-v3"),
    ("target_statement_id", "lee-c-immersion"),
])
def test_committed_semantic_review_digest_rejects_artifact_mutations(field, value):
    base = ROOT / "evals" / "phase2"
    turn = json.loads((base / "test-d-critiques.json").read_text())["turns"][0]
    review = json.loads((base / "phase2-semantic-review.json").read_text())
    approval = next(row for row in review["reviews"] if row["turn_id"] == turn["turn_id"])
    assert review_binding_sha256(turn) == approval["review_binding_sha256"]
    mutated = {**turn, field: value}
    assert review_binding_sha256(mutated) != approval["review_binding_sha256"]


def test_source_map_keeps_v2_mapping_separate_from_v3():
    data = json.loads((ROOT / "evals" / "lee-benjamin-source-map.json").read_text())
    assert data["status"] == "APPROVED_MAPPING"
    assert data["benjamin_agent_status"] == "BUILT"
    assert data["counts"]["EXACT"] == 0
    v2 = [m for m in data["mappings"] if m["benjamin_edition_id"] == "benjamin-artwork-v2"]
    v3 = [m for m in data["mappings"] if m["benjamin_edition_id"] == "benjamin-artwork-v3"]
    assert len(v2) == 1 and v2[0]["benjamin_gs_page"] == 359
    assert len(v3) == 4
    assert all(m["mapping_status"] == "STRONG_MATCH" for m in data["mappings"])


def test_benjamin_verified_sources_are_explicitly_approved():
    data = json.loads((ROOT / "evals" / "benjamin-source-verification.json").read_text())
    assert data["approval_status"] == "APPROVED_AND_VERIFIED"
    assert len(data["sources"]) == 2
    assert all(item["source_verified"] is True for item in data["sources"])
    assert all(item["user_approved"] is True for item in data["sources"])
    by_id = {item["edition_id"]: item for item in data["sources"]}
    assert by_id["benjamin-artwork-v2"]["container_pdf_page_range"] == [196, 230]
    assert by_id["benjamin-artwork-v2"]["gs_page_range"] == [350, 384]
    assert by_id["benjamin-artwork-v3"]["pdf_page_range"] == [1, 38]
    assert by_id["benjamin-artwork-v3"]["gs_page_range"] == [471, 508]
    assert not any(by_id["benjamin-artwork-v3"]["v2_only_term_hits"].values())


def test_benjamin_agent_fixtures_are_separate_and_edition_bound():
    v2 = PaperAgent.from_json(ROOT / "fixtures" / "benjamin-artwork-v2-agent.json")
    v3 = PaperAgent.from_json(ROOT / "fixtures" / "benjamin-artwork-v3-agent.json")
    assert v2.paper_id == v2.edition_id == "benjamin-artwork-v2"
    assert v3.paper_id == v3.edition_id == "benjamin-artwork-v3"
    assert v2.source_id != v3.source_id
    assert len(v2.store.values()) >= 3
    assert len(v3.store.values()) >= 3


def test_phase2_dialogue_artifacts_meet_minimum_counts_and_types():
    base = ROOT / "evals" / "phase2"
    d = json.loads((base / "test-d-critiques.json").read_text())
    e = json.loads((base / "test-e-lee-responses.json").read_text())
    f = json.loads((base / "test-f-synthesis.json").read_text())
    assert d["critique_count"] >= 6 and d["v2_count"] >= 3 and d["v3_count"] >= 3
    assert e["response_count"] == d["critique_count"]
    assert len(f["issues"]) >= 3 and len(f["research_gaps"]) >= 3 and len(f["research_questions"]) >= 3
    assert all(x["statement_type"] in {"AI_SYNTHESIS", "UNRESOLVED"} for x in f["issues"] + f["research_gaps"] + f["research_questions"])
    assert all(x["statement_type"] == "UNRESOLVED" for x in f["research_questions"])


def test_phase2_hard_gate_verification_is_zero_error():
    data = json.loads((ROOT / "evals" / "phase2" / "phase2-dialogue-verification.json").read_text())
    for key in ["FALSE_AUTHOR_CLAIM","EXTERNAL_AS_AUTHOR_ERROR","CROSS_EDITION_CONTAMINATION","UNSUPPORTED_DIALOGUE_TURN","TEMPORAL_CORPUS_CONTAMINATION","FAKE_PAGE_CITATION"]:
        assert data[key] == 0
        assert data["hard_gates"][key] is True
    assert data["TEST_D"] == data["TEST_E"] == data["TEST_F"] == "PASS"
