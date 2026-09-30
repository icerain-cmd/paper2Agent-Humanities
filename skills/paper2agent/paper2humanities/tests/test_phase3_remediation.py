import json
from unittest.mock import patch

import pytest

from paper2humanities.runtime.classifier import classify_query
from paper2humanities.runtime.pass_contract import evaluate_pass_contract, load_v5_contract
from paper2humanities.runtime.retrieval import retrieve
from paper2humanities.runtime.orchestration import live_turn
from paper2humanities.runtime.model_adapter import ModelResult


def test_query_routes_cover_every_live_action():
    cases = {
        "저자 귀속을 판정하라": "AUTHOR_ATTRIBUTION",
        "외부 인용의 저자 귀속을 판정하라": "EXTERNAL_ATTRIBUTION",
        "아우라 근거 페이지를 찾아라": "SOURCE_RETRIEVAL",
        "아우라를 해석하라": "INTERPRETATION",
        "아우라를 비판하라": "CRITIQUE",
        "비판에 응답하라": "RESPONSE",
        "두 판본을 비교하라": "CROSS_PAPER_COMPARE",
        "연구 공백을 찾아라": "RESEARCH_GAP",
        "연구질문을 제시하라": "RESEARCH_QUESTION",
    }
    for query, expected in cases.items():
        assert classify_query(query).value == expected


def test_panel_runtime_action_matches_classifier(tmp_path):
    from test_phase3_codex_runner import runner
    queries = ["저자 귀속을 판정하라", "두 판본을 비교하라", "아우라 근거 페이지를 찾아라"]
    panel = tmp_path / "queries.json"
    runner.write_json(panel, {"panel_id": "synthetic", "panel_type": "QUERY_ONLY",
                              "queries": [{"query_id": str(i), "query": q} for i, q in enumerate(queries)]})
    actions = []
    def fake_run(adapter, agent, query, action, **kwargs):
        actions.append(action)
        return {"outcome": "ABSTAINED", "classified_action": action,
                "turn": {"action": action}, "generator_subprocess_attempts": 0,
                "verifier_subprocess_attempts": 0}
    with patch.object(runner, "CodexExecAdapter", return_value=object()), patch.object(runner, "run_one", side_effect=fake_run):
        runner.generate_panel(panel, tmp_path / "responses.json")
    assert actions == [classify_query(q).value for q in queries]
    assert [r["turn"]["action"] for r in json.loads((tmp_path / "responses.json").read_text())["responses"]] == actions


def test_retrieval_match_no_support_edition_and_unrelated_only():
    from test_phase3_codex_runner import runner
    v2 = runner.AGENTS["benjamin-artwork-v2"]
    assert retrieve(v2, "second technology play")[0]
    for query in ("quasar nebula astrophysics", "V3 second technology play"):
        hits, trace = retrieve(v2, query)
        assert hits == []
        assert trace["selected_statement_ids"] == []
    hits, trace = retrieve(v2, "quasar nebula astrophysics", limit=20)
    assert not hits and not trace["candidate_statement_ids"]


def test_empty_evidence_reaches_abstention_contract():
    from test_phase3_codex_runner import runner
    payloads = []
    agent = runner.AGENTS["benjamin-artwork-v2"]
    class Adapter:
        def available(self):
            return True
        def generate_typed_turn(self, *, system_contract, payload):
            payloads.append(payload)
            turn = {"text": "No supporting passage was retrieved.",
                    "statement_type": "UNRESOLVED", "evidence_voice": "UNKNOWN",
                    "support_ids": [], "pages": [], "relation_type": "UNRESOLVED",
                    "actor_paper": agent.paper_id, "actor_edition_id": agent.edition_id,
                    "action": payload["dialogue_action"], "semantic_support": "UNSUPPORTED",
                    "evidence_sufficiency": "INSUFFICIENT", "qualification": None,
                    "evidence_span": None, "claims": []}
            return ModelResult(json.dumps(turn), "test", "test", {"attempts": 1}, "digest")
    turn, trace, _ = live_turn(Adapter(), agent, "quasar nebula astrophysics", "SOURCE_RETRIEVAL", {})
    assert trace["selected_statement_ids"] == []
    assert payloads[0]["evidence"] == []
    assert turn["statement_type"] == "UNRESOLVED"
    assert runner.turn_errors(turn, agent, set(), "SOURCE_RETRIEVAL") == []


def test_verifier_rejects_action_type_confusion():
    from test_phase3_codex_runner import runner, source_turn
    agent = runner.AGENTS["benjamin-artwork-v2"]
    source = next(s for s in agent.store.values() if s.evidence_voice and s.evidence_voice.value == "AUTHOR")
    turn = source_turn(agent, source, "CROSS_PAPER_COMPARE")
    assert "ACTION_STATEMENT_TYPE_MISMATCH" in runner.turn_errors(
        turn, agent, {source.statement_id}, "CROSS_PAPER_COMPARE")
    turn["action"] = "EXTERNAL_ATTRIBUTION"
    assert "FALSE_AUTHOR_CLAIM" in runner.turn_errors(
        turn, agent, {source.statement_id}, "EXTERNAL_ATTRIBUTION")


def test_v5_contract_thresholds():
    contract = load_v5_contract()
    assert {"WRONG_SOURCE_ID", "STALE_SEMANTIC_REVIEW"} <= set(contract["required_hard_gates"])
    report = {"accuracy": 1.0, "source_id_accuracy": 1.0,
              "unsupported_premise_rejection": 1.0,
              "hard_gate_counts": {name: 0 for name in contract["required_hard_gates"]}}
    assert evaluate_pass_contract(report, contract)["status"] == "PASS"
    for accuracy in (0.20, 0.89):
        assert evaluate_pass_contract({**report, "accuracy": accuracy}, contract)["status"] == "FAIL"
    assert evaluate_pass_contract({**report, "source_id_accuracy": 0.94}, contract)["status"] == "FAIL"
    assert evaluate_pass_contract({**report, "unsupported_premise_rejection": 0.89}, contract)["status"] == "FAIL"
    bad = {**report, "hard_gate_counts": {**report["hard_gate_counts"], "WRONG_SOURCE_ID": 1}}
    assert evaluate_pass_contract(bad, contract)["status"] == "FAIL"
    with pytest.raises(ValueError, match="missing hard gates"):
        evaluate_pass_contract({**report, "hard_gate_counts": {}}, contract)


def test_v5_scoring_checks_source_id_and_frozen_semantic_review(tmp_path):
    from test_phase3_codex_runner import runner
    agent = runner.AGENTS["lee-aura-2019"]
    response = tmp_path / "responses.json"
    turn = {"actor_paper": agent.paper_id, "actor_edition_id": agent.edition_id,
            "statement_type": "UNRESOLVED", "action": "SOURCE_RETRIEVAL"}
    runner.write_json(response, {"responses": [{"query_id": "q1", "source_id": agent.source_id,
        "outcome": "ABSTAINED", "turn": turn, "gate_errors": []}]})
    digest = runner.sha(response)
    runner.write_json(tmp_path / "responses.manifest.json", {"response_sha256": digest,
        "response_frozen": True, "gold_available_during_generation": False})
    gold = tmp_path / "gold.json"
    runner.write_json(gold, {"panel_id": "v5-synthetic", "panel_type": "HOLDOUT30_V5_GOLD",
        "records": [{"query_id": "q1", "type": "UNRESOLVED", "paper": agent.paper_id,
                     "edition": agent.edition_id, "page": None, "support": [], "source_id": agent.source_id}]})
    output = tmp_path / "score.json"
    runner.score_holdout(gold, response, output)
    assert json.loads(output.read_text())["hard_gate_counts"]["STALE_SEMANTIC_REVIEW"] == 1
    runner.write_json(tmp_path / "responses.semantic-review.json", {"response_sha256": digest,
        "reviewed_query_ids": ["q1"]})
    runner.score_holdout(gold, response, output)
    assert json.loads(output.read_text())["status"] == "PASS"
    raw = json.loads(response.read_text())
    raw["responses"][0]["source_id"] = "wrong"
    runner.write_json(response, raw)
    runner.write_json(tmp_path / "responses.manifest.json", {"response_sha256": runner.sha(response),
        "response_frozen": True, "gold_available_during_generation": False})
    runner.score_holdout(gold, response, output)
    scored = json.loads(output.read_text())
    assert scored["status"] == "FAIL"
    assert scored["hard_gate_counts"]["WRONG_SOURCE_ID"] == 1
