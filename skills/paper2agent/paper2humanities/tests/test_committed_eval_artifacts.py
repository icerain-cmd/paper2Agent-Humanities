import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def load(name):
    return json.loads((EVALS / name).read_text())


def test_committed_blind_panel_is_query_only_and_has_50_unique_queries():
    panel = load("lee-aura-2019-blind-panel.json")
    assert panel["panel_type"] == "BLIND_ADVERSARIAL_PANEL"
    assert panel["gold_hidden"] is True
    assert panel["fixture_answer_key_reuse"] is False
    assert panel["query_count"] == 50 == len(panel["queries"])
    assert len({item["query_id"] for item in panel["queries"]}) == 50
    assert all(set(item) == {"query_id", "query"} for item in panel["queries"])


def test_committed_gold_panel_covers_required_adversarial_categories():
    panel = load("lee-aura-2019-adversarial-panel.json")
    assert panel["gold_review"] == "PASS"
    assert panel["query_count"] == 50 == len(panel["records"])
    categories = {item["adversarial_category"] for item in panel["records"]}
    required = {
        "false_attribution", "embedded_quotation", "interpretation_promotion",
        "concept_neighbor", "page_trap", "unsupported_premise", "mixed_voice",
    }
    assert required <= categories
    assert sum(item["adversarial_category"] == "page_trap" for item in panel["records"]) >= 4
    assert sum(item["adversarial_category"] == "ambiguous_attribution" for item in panel["records"]) >= 4
    provenance = panel["generation_provenance"]
    assert provenance["behavioral_responses_excluded_from_gold_creation"] is True


def test_behavioral_response_ids_exactly_match_blind_panel():
    blind = load("lee-aura-2019-blind-panel.json")
    responses = load("lee-aura-2019-behavioral-responses.json")
    assert {x["query_id"] for x in blind["queries"]} == {
        x["query_id"] for x in responses["responses"]
    }


def test_benjamin_candidates_keep_v2_and_v3_separate_after_approval():
    data = load("benjamin-source-candidates.json")
    items = data["candidates"]
    assert {item["edition_id"] for item in items} == {
        "benjamin-artwork-v2", "benjamin-artwork-v3"
    }
    assert len({item["canonical_source"] for item in items}) == 2
    assert all(item["approval_status"] == "APPROVED_AND_VERIFIED" for item in items)
    assert data["agent_status"] == "BUILT"
