import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from paper2humanities.runtime.model_adapter import ModelResult

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_phase3_codex.py"
spec = importlib.util.spec_from_file_location("phase3_codex_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def source_turn(agent, source, action="SOURCE_RETRIEVAL"):
    return {"text": "Bounded source statement", "statement_type": "AUTHOR_CLAIM",
            "evidence_voice": source.evidence_voice.value, "support_ids": [source.statement_id],
            "pages": [source.page], "relation_type": "QUALIFIES", "actor_paper": agent.paper_id,
            "actor_edition_id": agent.edition_id, "action": action,
            "semantic_support": "SEMANTICALLY_SUPPORTED", "evidence_span": source.evidence_span}


def test_turn_gate_checks_selected_support_page_span_voice_actor_and_action():
    agent = runner.AGENTS["benjamin-artwork-v2"]
    source = next(s for s in agent.store.values() if s.evidence_voice and s.evidence_voice.value == "AUTHOR")
    turn = source_turn(agent, source)
    assert runner.turn_errors(turn, agent, {source.statement_id}, "SOURCE_RETRIEVAL") == []
    assert "UNSELECTED_SUPPORT_ID" in runner.turn_errors(turn, agent, set(), "SOURCE_RETRIEVAL")
    assert "FAKE_PAGE_CITATION" in runner.turn_errors({**turn, "pages": [99]}, agent, {source.statement_id}, "SOURCE_RETRIEVAL")
    assert "EVIDENCE_SPAN_MISMATCH" in runner.turn_errors({**turn, "evidence_span": "wrong"}, agent, {source.statement_id}, "SOURCE_RETRIEVAL")
    assert "ACTOR_EDITION_MISMATCH" in runner.turn_errors({**turn, "actor_edition_id": "wrong"}, agent, {source.statement_id}, "SOURCE_RETRIEVAL")
    assert "ACTION_MISMATCH" in runner.turn_errors({**turn, "action": "CRITIQUE"}, agent, {source.statement_id}, "SOURCE_RETRIEVAL")
    assert "ACTION_STATEMENT_TYPE_MISMATCH" in runner.turn_errors({**turn, "action": "SYNTHESIS"}, agent, {source.statement_id}, "SYNTHESIS")


def test_fresh_verifier_gets_candidate_and_evidence_only():
    agent = runner.AGENTS["benjamin-artwork-v2"]
    source = next(s for s in agent.store.values() if s.evidence_voice and s.evidence_voice.value == "AUTHOR")
    turn = source_turn(agent, source)
    trace = {"selected_statement_ids": [source.statement_id]}
    generator = ModelResult(json.dumps(turn), "codex-exec", runner.GENERATOR_MODEL, {"attempts": 1}, "digest")
    packets = []

    class FakeVerifier:
        def __init__(self, model):
            assert model == runner.VERIFIER_MODEL
        def generate_typed_turn(self, *, system_contract, payload):
            packets.append(payload)
            return ModelResult(json.dumps(turn), "codex-exec", runner.VERIFIER_MODEL, {"attempts": 1}, "digest2")

    adapter = type("Generator", (), {"model": runner.GENERATOR_MODEL})()
    with patch.object(runner, "live_turn", return_value=(turn, trace, generator)), patch.object(runner, "CodexExecAdapter", FakeVerifier):
        result = runner.run_one(adapter, agent, "private query", "SOURCE_RETRIEVAL", history=[{"secret": "history"}])
    assert result["outcome"] == "ACCEPTED"
    assert result["independent_model_verifier"] and result["fresh_context_verifier"]
    assert result["generator_subprocess_attempts"] == result["verifier_subprocess_attempts"] == 1
    assert set(packets[0]) == {"candidate_turn", "evidence"}
    assert "private query" not in json.dumps(packets[0]) and "secret" not in json.dumps(packets[0])


def test_dialogue_targets_and_labels_survive_rejected_attempt(tmp_path):
    calls = 0
    def fake_run(adapter, agent, query, action, target=None, history=None, verifier_model=runner.VERIFIER_MODEL):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"outcome": "REJECTED", "gate_errors": ["VERIFIER_DISAGREEMENT"],
                    "generator_subprocess_attempts": 1, "verifier_subprocess_attempts": 1}
        return {"outcome": "ACCEPTED", "turn": {"action": action, "actor_paper": agent.paper_id},
                "gate_errors": [], "generator_subprocess_attempts": 1, "verifier_subprocess_attempts": 1}
    path = tmp_path / "dialogue.json"
    with patch.object(runner, "CodexExecAdapter", return_value=object()), patch.object(runner, "run_one", side_effect=fake_run):
        runner.generate_dialogue(path)
    data = json.loads(path.read_text())
    assert data["status"] == "PASS"
    assert data["accepted"]["D_by_edition"] == {"benjamin-artwork-v2": 3, "benjamin-artwork-v3": 3}
    assert data["accepted"]["E"] == data["accepted"]["D"] == 6
    assert data["accepted"]["F_by_subtype"] == {"ISSUE": 3, "GAP": 3, "RESEARCH_QUESTION": 3}
    assert [(r["step"], r["turn"]["actor_paper"]) for r in data["runs"] if r["test"] == "MULTITURN"] == [
        (1, "benjamin-artwork-v2"), (2, "lee-aura-2019"), (3, "benjamin-artwork-v3"),
        (4, "lee-aura-2019"), (5, "lee-aura-2019")]
    assert data["generator_subprocess_attempts"] == calls
    assert data["verifier_subprocess_attempts"] == calls
    assert data["runs"][0]["outcome"] == "REJECTED" and data["runs"][1]["attempt"] == 2


def test_frozen_hash_checked_before_gold_is_opened(tmp_path):
    response = tmp_path / "responses.json"
    response.write_text('{"responses": []}')
    runner.write_json(tmp_path / "manifest.json", {"response_sha256": "wrong", "response_frozen": True})
    with pytest.raises(ValueError, match="response freeze hash mismatch"):
        runner.score_holdout(tmp_path / "missing-gold.json", response, tmp_path / "score.json")


def test_holdout_gates_count_artifact_errors(tmp_path):
    response = tmp_path / "responses.json"
    runner.write_json(response, {"responses": [{"query_id": "q1", "outcome": "REJECTED",
        "gate_errors": ["FAKE_PAGE_CITATION", "TEMPORAL_CORPUS_CONTAMINATION", "VERIFIER_DISAGREEMENT"]}]})
    runner.write_json(tmp_path / "manifest.json", {"response_sha256": runner.sha(response),
                      "response_frozen": True, "gold_available_during_generation": False})
    gold = tmp_path / "gold.json"
    runner.write_json(gold, {"panel_id": "p", "records": [{"query_id": "q1", "type": "UNRESOLVED",
        "paper": None, "edition": None, "page": None, "support": []}]})
    output = tmp_path / "score.json"
    runner.score_holdout(gold, response, output)
    gates = json.loads(output.read_text())["hard_gate_counts"]
    assert gates["FAKE_PAGE_CITATION"] == 1
    assert gates["TEMPORAL_CORPUS_CONTAMINATION"] == 1
    assert gates["UNSUPPORTED_DIALOGUE_TURN"] == 1
