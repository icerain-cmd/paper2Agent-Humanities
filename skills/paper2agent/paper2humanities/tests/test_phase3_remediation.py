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


def test_v6_multilingual_aliases_recover_v5_expected_evidence_without_padding():
    from test_phase3_codex_runner import runner
    cases = [
        (runner.AGENTS["benjamin-artwork-v2"], "V2에서 첫째 기술과 둘째 기술이 인간을 투입하는 방식이 다르다는 근거", "AUTHOR_ATTRIBUTION", "b-v2-c-technique-human-use"),
        (runner.AGENTS["benjamin-artwork-v3"], "V3에서 제의가치와 전시가치를 작품 수용의 두 극으로 설명하는 근거", "SOURCE_RETRIEVAL", "b-v3-c-cult-exhibition"),
        (runner.AGENTS["benjamin-artwork-v2"], "V2에서 현대 예술의 사회적 기능을 자연과 인류의 상호작용 연습과 연결하는 근거", "SOURCE_RETRIEVAL", "b-v2-c-art-function"),
        (runner.AGENTS["benjamin-artwork-v2"], "V2의 자연과 인류의 상호작용 개념", "CRITIQUE", "b-v2-c-interplay"),
    ]
    for agent, query, action, expected in cases:
        hits, trace = retrieve(agent, query, action=action)
        assert expected in trace["selected_statement_ids"]
        assert hits
    hits, trace = retrieve(runner.AGENTS["benjamin-artwork-v2"], "quasar nebula astrophysics", limit=50)
    assert hits == [] and trace["selected_statement_ids"] == []


def test_v6_phase3_lee_fixture_contains_reviewed_grounded_immersion_claim():
    from test_phase3_codex_runner import runner
    source = runner.AGENTS["lee-aura-2019"].store.get("lee-c-immersion")
    assert source.statement_type.value == "AUTHOR_CLAIM"
    assert source.evidence_voice.value == "AUTHOR"
    assert source.page == 17 and source.evidence_span == "수용 태도|정신분산|정신몰입"
    assert source.review_status.value == "REVIEWED"


def test_v6_pageless_interpretation_is_trace_hint_not_final_evidence():
    from test_phase3_codex_runner import runner
    packets = []
    actor = runner.AGENTS["benjamin-artwork-v3"]
    lee = runner.AGENTS["lee-aura-2019"]
    class Adapter:
        def available(self): return True
        def generate_typed_turn(self, *, system_contract, payload):
            packets.append(payload)
            turn = {"text": "insufficient", "statement_type": "UNRESOLVED", "evidence_voice": "UNKNOWN",
                    "support_ids": [], "pages": [], "relation_type": "UNRESOLVED", "actor_paper": actor.paper_id,
                    "actor_edition_id": actor.edition_id, "action": payload["dialogue_action"],
                    "semantic_support": "UNSUPPORTED", "evidence_sufficiency": "INSUFFICIENT",
                    "qualification": None, "evidence_span": None, "claims": []}
            return ModelResult(json.dumps(turn), "test", "test", {"attempts": 1}, "digest")
    _, trace, _ = live_turn(Adapter(), actor, "Benjamin V3의 정신분산과 Lee 2019의 몰입을 함께 검토하는 연구질문", "RESEARCH_QUESTION", {}, supporting_agents=(lee,))
    assert "lee-i-distance" not in trace["selected_statement_ids"]
    assert "lee-i-distance" in {h["statement_id"] for h in trace["retrieval_hints"]}
    assert "lee-c-immersion" in trace["selected_statement_ids"]
    assert trace["missing_required_sources"] == []
    assert all(item["page"] and item["evidence_span"] for item in trace["selected_evidence"])
    assert all(e["page"] and e["evidence_span"] for e in packets[0]["evidence"])


def test_v6_pageless_final_support_and_missing_actor_are_explicit_gates():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    sid = "lee-i-distance"
    turn = {"text": "derived", "statement_type": "INTERPRETATION", "evidence_voice": "UNKNOWN",
            "support_ids": [sid], "pages": [17], "relation_type": "QUALIFIES", "actor_paper": lee.paper_id,
            "actor_edition_id": lee.edition_id, "action": "INTERPRETATION", "semantic_support": "SEMANTICALLY_SUPPORTED",
            "evidence_sufficiency": "SUFFICIENT", "qualification": None, "evidence_span": "derived", "claims": [
                {"text": "derived", "statement_type": "INTERPRETATION", "support_ids": [sid]}]}
    assert "PAGELESS_FINAL_SUPPORT" in runner.turn_errors(turn, lee, {sid}, "INTERPRETATION")
    actor = runner.AGENTS["benjamin-artwork-v2"]
    target = lee.store.get("lee-c-transparent")
    cross = {**turn, "text": "critique", "statement_type": "CRITIQUE", "evidence_voice": "AUTHOR",
             "support_ids": [target.statement_id], "pages": [target.page], "evidence_span": target.evidence_span,
             "actor_paper": actor.paper_id, "actor_edition_id": actor.edition_id, "action": "CRITIQUE",
             "claims": [{"text": "critique", "statement_type": "CRITIQUE", "support_ids": [target.statement_id]}]}
    assert "MISSING_ACTOR_SUPPORT" in runner.turn_errors(cross, actor, {target.statement_id}, "CRITIQUE", (lee,))


def test_v6_attribution_axes_separate_answer_form_from_external_owner():
    from paper2humanities.runtime.attribution import infer_attribution_owner, infer_statement_form
    turn = {"statement_type": "INTERPRETATION", "evidence_voice": "EXTERNAL"}
    assert infer_statement_form(turn) == "INTERPRETIVE_STATEMENT"
    assert infer_attribution_owner(turn) == "EXTERNAL"
    quote = {"statement_type": "SOURCE_QUOTE", "evidence_voice": "EXTERNAL"}
    assert infer_statement_form(quote) == "QUOTE"
    assert infer_attribution_owner(quote) == "EXTERNAL"


def test_v6_factual_external_attribution_accepts_interpretive_judgment_form():
    from test_phase3_codex_runner import runner
    actor = runner.AGENTS["lee-aura-2019"]
    source = actor.store.get("lee-q-benjamin-second-tech")
    turn = {"text": "이 문장은 Lee 자신의 주장이 아니라 외부 인용이다.",
            "statement_type": "INTERPRETATION", "evidence_voice": "EXTERNAL",
            "support_ids": [source.statement_id], "pages": [source.page], "relation_type": "QUALIFIES",
            "actor_paper": actor.paper_id, "actor_edition_id": actor.edition_id,
            "action": "EXTERNAL_ATTRIBUTION", "semantic_support": "SEMANTICALLY_SUPPORTED",
            "evidence_sufficiency": "SUFFICIENT", "qualification": None,
            "evidence_span": source.evidence_span,
            "claims": [{"text": "외부 인용으로 귀속된다.", "statement_type": "INTERPRETATION",
                        "support_ids": [source.statement_id]}]}
    response = {"query_id": "q", "source_id": actor.source_id, "outcome": "ACCEPTED",
                "classified_action": "EXTERNAL_ATTRIBUTION", "turn": turn, "gate_errors": [],
                "fresh_context_verifier": True, "independent_model_verifier": True,
                "retrieval_trace": {"selected_statement_ids": [source.statement_id],
                    "allowed_agents": [{"paper_id": actor.paper_id, "edition_id": actor.edition_id}]}}
    gold = {"panel_id": "v6", "panel_type": "HOLDOUT30_V6_GOLD", "records": [{
        "query_id": "q", "task_family": "FACTUAL", "action": "EXTERNAL_ATTRIBUTION",
        "type": "SOURCE_QUOTE", "paper": actor.paper_id, "edition": actor.edition_id,
        "page": source.page, "support": [source.statement_id], "source_id": actor.source_id,
        "statement_form": "INTERPRETIVE_STATEMENT", "attribution_owner": "EXTERNAL"}]}
    report = runner.score_v6_holdout(gold, {"responses": [response]}, {"response_sha256": "x", "gold_available_during_generation": False})
    assert report["factual_task_accuracy"] == 1.0
    assert report["attribution_form_accuracy"] == report["attribution_owner_accuracy"] == 1.0
    assert all(v == 0 for v in report["hard_gate_counts"].values())


def test_v6_scholarly_scoring_allows_alternative_grounded_support_path():
    from test_phase3_codex_runner import runner
    actor = runner.AGENTS["lee-aura-2019"]
    benjamin = runner.AGENTS["benjamin-artwork-v3"]
    lee_source = actor.store.get("lee-c-research-program")
    b_source = benjamin.store.get("b-v3-c-aura-withers")
    supports = [lee_source.statement_id, b_source.statement_id]
    turn = {"text": "두 논의 사이의 판단 기준이 추가 연구 공백이다.",
            "statement_type": "AI_SYNTHESIS", "evidence_voice": lee_source.evidence_voice.value,
            "support_ids": supports, "pages": sorted({lee_source.page, b_source.page}),
            "relation_type": "QUALIFIES", "actor_paper": actor.paper_id, "actor_edition_id": actor.edition_id,
            "action": "RESEARCH_GAP", "semantic_support": "PARTIALLY_SUPPORTED",
            "evidence_sufficiency": "PARTIAL", "qualification": "두 발췌가 직접 동일성을 주장하지는 않는다.",
            "evidence_span": lee_source.evidence_span,
            "claims": [{"text": "추가 연구의 판단 기준이 필요하다.", "statement_type": "AI_SYNTHESIS",
                        "support_ids": supports}]}
    response = {"query_id": "q", "source_id": actor.source_id, "outcome": "ACCEPTED",
                "classified_action": "RESEARCH_GAP", "turn": turn, "gate_errors": [],
                "fresh_context_verifier": True, "independent_model_verifier": True,
                "retrieval_trace": {"selected_statement_ids": supports,
                    "allowed_agents": [{"paper_id": actor.paper_id, "edition_id": actor.edition_id},
                                       {"paper_id": benjamin.paper_id, "edition_id": benjamin.edition_id}]}}
    gold = {"panel_id": "v6", "panel_type": "HOLDOUT30_V6_GOLD", "records": [{
        "query_id": "q", "task_family": "SCHOLARLY", "action": "RESEARCH_GAP",
        "type": "AI_SYNTHESIS", "paper": actor.paper_id, "edition": actor.edition_id,
        "page": 17, "support": ["lee-q-digital-aura", "b-v3-c-aura-withers"],
        "source_id": actor.source_id,
        "required_papers": [{"paper_id": actor.paper_id, "edition_id": actor.edition_id},
                            {"paper_id": benjamin.paper_id, "edition_id": benjamin.edition_id}]}]}
    report = runner.score_v6_holdout(gold, {"responses": [response]}, {"response_sha256": "x", "gold_available_during_generation": False})
    assert report["scholarly_task_validity"] == report["overall_validity"] == 1.0
    assert all(v == 0 for v in report["hard_gate_counts"].values())


def test_v6_factual_scoring_remains_strict_about_support_identity():
    from test_phase3_codex_runner import runner
    actor = runner.AGENTS["benjamin-artwork-v3"]
    actual = actor.store.get("b-v3-c-film-examiner")
    expected = actor.store.get("b-v3-c-distraction")
    turn = {"text": actual.text, "statement_type": "AUTHOR_CLAIM", "evidence_voice": "AUTHOR",
            "support_ids": [actual.statement_id], "pages": [actual.page], "relation_type": "QUALIFIES",
            "actor_paper": actor.paper_id, "actor_edition_id": actor.edition_id, "action": "SOURCE_RETRIEVAL",
            "semantic_support": "SEMANTICALLY_SUPPORTED", "evidence_sufficiency": "SUFFICIENT",
            "qualification": None, "evidence_span": actual.evidence_span,
            "claims": [{"text": actual.text, "statement_type": "AUTHOR_CLAIM", "support_ids": [actual.statement_id]}]}
    response = {"query_id": "q", "source_id": actor.source_id, "outcome": "ACCEPTED",
                "classified_action": "SOURCE_RETRIEVAL", "turn": turn, "gate_errors": [],
                "fresh_context_verifier": True, "independent_model_verifier": True,
                "retrieval_trace": {"selected_statement_ids": [actual.statement_id],
                    "allowed_agents": [{"paper_id": actor.paper_id, "edition_id": actor.edition_id}]}}
    gold = {"panel_id": "v6", "panel_type": "HOLDOUT30_V6_GOLD", "records": [{
        "query_id": "q", "task_family": "FACTUAL", "action": "SOURCE_RETRIEVAL", "type": "AUTHOR_CLAIM",
        "paper": actor.paper_id, "edition": actor.edition_id, "page": expected.page,
        "support": [expected.statement_id], "source_id": actor.source_id,
        "statement_form": "PARAPHRASE", "attribution_owner": "AUTHOR"}]}
    report = runner.score_v6_holdout(gold, {"responses": [response]}, {"response_sha256": "x", "gold_available_during_generation": False})
    assert report["factual_task_accuracy"] == 0.0
    assert report["source_id_accuracy"] == 1.0


def test_v7_unresolved_metalinguistic_forbidden_term_is_not_temporal_contamination():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    turn = {"text": "제공된 근거로 ‘아투라’라는 명제를 확인할 수 없다.",
            "statement_type": "UNRESOLVED", "evidence_voice": "UNKNOWN",
            "support_ids": [], "pages": [], "relation_type": "UNRESOLVED",
            "actor_paper": lee.paper_id, "actor_edition_id": lee.edition_id,
            "action": "SOURCE_RETRIEVAL", "semantic_support": "UNSUPPORTED",
            "evidence_sufficiency": "INSUFFICIENT", "qualification": None,
            "evidence_span": None, "claims": []}
    errors = runner.turn_errors(turn, lee, set(), "SOURCE_RETRIEVAL")
    assert not any("TEMPORAL_CORPUS_CONTAMINATION" in error for error in errors)
    assert errors == []


def test_v7_grounded_forbidden_term_remains_temporal_contamination():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    source = lee.store.get("lee-c-transparent")
    author_turn = {"text": "Lee 2019의 아투라 주장은 다음과 같다.",
                   "statement_type": "AUTHOR_CLAIM", "evidence_voice": "AUTHOR",
                   "support_ids": [source.statement_id], "pages": [source.page],
                   "relation_type": "QUALIFIES", "actor_paper": lee.paper_id,
                   "actor_edition_id": lee.edition_id, "action": "AUTHOR_ATTRIBUTION",
                   "semantic_support": "SEMANTICALLY_SUPPORTED",
                   "evidence_sufficiency": "SUFFICIENT", "qualification": None,
                   "evidence_span": source.evidence_span,
                   "claims": [{"text": "아투라", "statement_type": "AUTHOR_CLAIM",
                               "support_ids": [source.statement_id]}]}
    errors = runner.turn_errors(author_turn, lee, {source.statement_id}, "AUTHOR_ATTRIBUTION")
    assert any("TEMPORAL_CORPUS_CONTAMINATION" in error for error in errors)
    interpretive = {**author_turn, "statement_type": "INTERPRETATION",
                    "action": "INTERPRETATION",
                    "claims": [{"text": "아투라", "statement_type": "INTERPRETATION",
                                "support_ids": [source.statement_id]}]}
    errors = runner.turn_errors(interpretive, lee, {source.statement_id}, "INTERPRETATION")
    assert any("TEMPORAL_CORPUS_CONTAMINATION" in error for error in errors)


def test_v7_unresolved_with_support_still_fails_abstention_shape():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    source = lee.store.get("lee-c-transparent")
    turn = {"text": "근거가 부족하다.", "statement_type": "UNRESOLVED",
            "evidence_voice": "UNKNOWN", "support_ids": [source.statement_id],
            "pages": [], "relation_type": "UNRESOLVED", "actor_paper": lee.paper_id,
            "actor_edition_id": lee.edition_id, "action": "SOURCE_RETRIEVAL",
            "semantic_support": "UNSUPPORTED", "evidence_sufficiency": "INSUFFICIENT",
            "qualification": None, "evidence_span": None, "claims": []}
    errors = runner.turn_errors(turn, lee, {source.statement_id}, "SOURCE_RETRIEVAL")
    assert any("FORMAT:" in error for error in errors)


def test_v7_runtime_failure_is_not_stale_semantic_review():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    response = {"query_id": "q", "source_id": lee.source_id,
                "outcome": "MODEL_RUNTIME_UNAVAILABLE",
                "error": "codex exec invocation failed: TimeoutExpired",
                "gate_errors": ["MODEL_RUNTIME_FAILURE"],
                "generator_subprocess_attempts": 2,
                "verifier_subprocess_attempts": 0}
    gold = {"panel_id": "v7", "panel_type": "HOLDOUT30_V7_GOLD",
            "records": [{"query_id": "q", "task_family": "FACTUAL",
                         "action": "SOURCE_RETRIEVAL", "type": "UNRESOLVED",
                         "expected_outcome": "ABSTAIN", "paper": lee.paper_id,
                         "edition": lee.edition_id, "page": None, "support": [],
                         "source_id": lee.source_id}]}
    report = runner.score_v6_holdout(
        gold, {"responses": [response]},
        {"response_sha256": "x", "gold_available_during_generation": False})
    assert report["hard_gate_counts"]["MODEL_RUNTIME_FAILURE"] == 1
    assert report["hard_gate_counts"]["STALE_SEMANTIC_REVIEW"] == 0


def test_v7_verifier_timeout_is_explicit_runtime_failure():
    from test_phase3_codex_runner import runner, source_turn
    agent = runner.AGENTS["benjamin-artwork-v2"]
    source = next(s for s in agent.store.values()
                  if s.evidence_voice and s.evidence_voice.value == "AUTHOR")
    turn = source_turn(agent, source, "SOURCE_RETRIEVAL")
    trace = {"selected_statement_ids": [source.statement_id]}
    model_result = ModelResult(json.dumps(turn), "test", "gpt-6-sol",
                               {"attempts": 1}, "digest")
    with patch.object(runner, "live_turn", return_value=(turn, trace, model_result)),          patch.object(runner.CodexExecAdapter, "generate_typed_turn",
                      side_effect=runner.ModelRuntimeUnavailable("timeout", 2)):
        result = runner.run_one(object(), agent, "synthetic", "SOURCE_RETRIEVAL")
    assert any("MODEL_RUNTIME_FAILURE" in error for error in result["gate_errors"])
    assert not any("STALE_SEMANTIC_REVIEW" in error for error in result["gate_errors"])


def test_v8_classifier_scholarly_intent_precedence_paraphrase_matrix():
    cases = {
        "이 두 자료를 바탕으로 검증 가능한 연구질문 하나를 만들어라": "RESEARCH_QUESTION",
        "두 주장 사이에 남는 미해결 연구 문제를 제시하라": "RESEARCH_GAP",
        "두 논문의 기술-인간 관계를 대조하라": "CROSS_PAPER_COMPARE",
        "이 이론이 드러내는 이론적 취약점을 논하라": "CRITIQUE",
        "이 주장에 대한 응답을 구성하라": "RESPONSE",
        "두 개념이 어떻게 맞물리는지 해석하라": "INTERPRETATION",
        "외부 인용의 발화 주체가 누구인지 판정하라": "EXTERNAL_ATTRIBUTION",
        "이 명제의 저자 귀속을 판정하라": "AUTHOR_ATTRIBUTION",
        "직접 근거를 찾아라": "SOURCE_RETRIEVAL",
    }
    for query, expected in cases.items():
        assert classify_query(query).value == expected


def test_v8_failed_scholarly_routes_are_recovered_without_query_id_hardcoding():
    cases = {
        "두 문헌의 근거만으로 이론적 취약점을 논하라": "CRITIQUE",
        "인간 투입 최소화 명제와 투명화 개념을 각각의 근거로 대조하라": "CROSS_PAPER_COMPARE",
        "두 설명 사이에 어떤 미해결 연구 문제가 남는지 제시하라": "RESEARCH_GAP",
    }
    for query, expected in cases.items():
        assert classify_query(query).value == expected


def test_v8_external_attribution_alias_recovers_reviewed_benjamin_quote():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    query = "Lee 2019이 벤야민의 기술론을 끌어오는 대목에서 외부 인용으로 표시된 발화가 누구의 것인지 판정하라."
    hits, trace = retrieve(lee, query, action="EXTERNAL_ATTRIBUTION")
    assert "lee-q-benjamin-second-tech" in trace["selected_statement_ids"]
    assert hits


def test_v8_computer_internet_origin_alias_recovers_lee_tech_start():
    from test_phase3_codex_runner import runner
    lee = runner.AGENTS["lee-aura-2019"]
    for query in (
        "Lee 2019의 컴퓨터·인터넷 기점 설정",
        "컴퓨터 인터넷 기점에 대한 Lee의 설명",
    ):
        hits, trace = retrieve(lee, query, action="RESPONSE")
        assert "lee-c-tech-start" in trace["selected_statement_ids"]
        assert hits


def test_v8_cross_paper_response_retrieval_preserves_both_actor_and_target_grounding():
    from test_phase3_codex_runner import runner
    actor = runner.AGENTS["benjamin-artwork-v2"]
    lee = runner.AGENTS["lee-aura-2019"]
    query = "Benjamin V2의 놀이 및 자연-인류 상호작용 명제를 근거로 Lee 2019의 컴퓨터·인터넷 기점 설정에 대한 응답을 구성하라."
    actor_hits, actor_trace = retrieve(actor, query, action="RESPONSE")
    lee_hits, lee_trace = retrieve(lee, query, action="RESPONSE")
    assert {"b-v2-c-play-origin", "b-v2-c-interplay"} & set(actor_trace["selected_statement_ids"])
    assert "lee-c-tech-start" in lee_trace["selected_statement_ids"]
    assert actor_hits and lee_hits


def test_v8_direct_source_retrieval_prefers_author_claim_hint_not_interpretation():
    from paper2humanities.runtime.orchestration import response_type_hint
    query = "Lee 2019에서 투명화가 사용자와 도구, 현실과 가상, 수단과 목적의 구분을 지운다고 설명하는 직접 근거를 찾아라."
    assert response_type_hint(query, "SOURCE_RETRIEVAL") == "AUTHOR_CLAIM"
    assert response_type_hint("두 개념의 구분이 충분한지 비판하라", "CRITIQUE") is None


def test_v8_preregistered_contract_preserves_v7_thresholds_and_runtime_gate():
    from paper2humanities.runtime.pass_contract import load_v7_contract, load_v8_contract
    v7 = load_v7_contract()
    v8 = load_v8_contract()
    assert v8["contract_id"] == "HOLDOUT30_V8_PREREGISTERED_PASS_CONTRACT"
    for key in (
        "minimum_factual_task_accuracy",
        "minimum_scholarly_task_validity",
        "minimum_overall_validity",
        "minimum_source_id_accuracy",
        "minimum_unsupported_premise_rejection",
        "minimum_abstention_precision",
        "hard_gate_maximum",
    ):
        assert v8[key] == v7[key]
    assert "MODEL_RUNTIME_FAILURE" in v8["required_hard_gates"]
    assert set(v8["required_hard_gates"]) == set(v7["required_hard_gates"])
    assert v8["pinned_codex_runtime"]["codex_version"] == "0.155.1"
    assert v8["timeout_retry_policy"]["maximum_retries"] == 1


def test_v8_score_path_uses_v8_contract_without_weakening_actions():
    from test_phase3_codex_runner import runner
    actor = runner.AGENTS["benjamin-artwork-v2"]
    source = actor.store.get("b-v2-c-interplay")
    turn = {
        "text": source.text,
        "statement_type": "AUTHOR_CLAIM",
        "evidence_voice": "AUTHOR",
        "support_ids": [source.statement_id],
        "pages": [source.page],
        "relation_type": "QUALIFIES",
        "actor_paper": actor.paper_id,
        "actor_edition_id": actor.edition_id,
        "action": "SOURCE_RETRIEVAL",
        "semantic_support": "SEMANTICALLY_SUPPORTED",
        "evidence_sufficiency": "SUFFICIENT",
        "qualification": None,
        "evidence_span": source.evidence_span,
        "claims": [{
            "text": source.text,
            "statement_type": "AUTHOR_CLAIM",
            "support_ids": [source.statement_id],
        }],
    }
    response = {
        "query_id": "v8-synthetic",
        "source_id": actor.source_id,
        "outcome": "ACCEPTED",
        "classified_action": "SOURCE_RETRIEVAL",
        "turn": turn,
        "gate_errors": [],
        "fresh_context_verifier": True,
        "independent_model_verifier": True,
        "retrieval_trace": {
            "selected_statement_ids": [source.statement_id],
            "allowed_agents": [{
                "paper_id": actor.paper_id,
                "edition_id": actor.edition_id,
            }],
        },
    }
    gold = {
        "panel_id": "v8-synthetic",
        "panel_type": "HOLDOUT30_V8_GOLD",
        "records": [{
            "query_id": "v8-synthetic",
            "task_family": "FACTUAL",
            "action": "SOURCE_RETRIEVAL",
            "type": "AUTHOR_CLAIM",
            "paper": actor.paper_id,
            "edition": actor.edition_id,
            "page": source.page,
            "support": [source.statement_id],
            "source_id": actor.source_id,
            "statement_form": "PARAPHRASE",
            "attribution_owner": "AUTHOR",
        }],
    }
    report = runner.score_v6_holdout(
        gold,
        {"responses": [response]},
        {"response_sha256": "x", "gold_available_during_generation": False},
    )
    assert report["pass_contract"]["contract_id"] == "HOLDOUT30_V8_PREREGISTERED_PASS_CONTRACT"
    assert report["status"] == "PASS"


def test_v8_direct_factual_turn_normalizes_interpretation_when_all_claims_are_author_claims():
    from paper2humanities.runtime.orchestration import normalize_direct_factual_turn
    turn = {
        "text": "Lee는 투명화를 제3기술의 핵심가치로 직접 설명한다.",
        "statement_type": "INTERPRETATION",
        "statement_form": "INTERPRETIVE_STATEMENT",
        "attribution_owner": "AUTHOR",
        "evidence_voice": "AUTHOR",
        "support_ids": ["lee-c-transparent"],
        "pages": [22],
        "relation_type": "EXTENDS",
        "actor_paper": "lee-aura-2019",
        "actor_edition_id": None,
        "action": "SOURCE_RETRIEVAL",
        "semantic_support": "SEMANTICALLY_SUPPORTED",
        "evidence_sufficiency": "SUFFICIENT",
        "qualification": None,
        "evidence_span": "span",
        "claims": [{
            "text": "Lee는 투명화를 제3기술의 핵심가치로 제시한다.",
            "statement_type": "AUTHOR_CLAIM",
            "support_ids": ["lee-c-transparent"],
        }],
    }
    normalized = normalize_direct_factual_turn(turn, "AUTHOR_CLAIM")
    assert normalized["statement_type"] == "AUTHOR_CLAIM"
    assert normalized["statement_form"] == "PARAPHRASE"
    assert normalized["attribution_owner"] == "AUTHOR"


def test_v8_direct_factual_turn_does_not_normalize_derived_judgment():
    from paper2humanities.runtime.orchestration import normalize_direct_factual_turn
    turn = {
        "statement_type": "INTERPRETATION",
        "statement_form": "INTERPRETIVE_STATEMENT",
        "attribution_owner": "AUTHOR",
        "evidence_voice": "AUTHOR",
        "action": "SOURCE_RETRIEVAL",
        "claims": [
            {"text": "source fact", "statement_type": "AUTHOR_CLAIM", "support_ids": ["s1"]},
            {"text": "derived", "statement_type": "INTERPRETATION", "support_ids": ["s1"]},
        ],
    }
    assert normalize_direct_factual_turn(turn, "AUTHOR_CLAIM") == turn


def test_v8_direct_quote_or_declaration_retrieval_is_not_forced_to_author_claim():
    from paper2humanities.runtime.orchestration import response_type_hint
    assert response_type_hint(
        "Lee 2019이 기술편집시대라고 선언하는 직접 근거 페이지를 찾아라.",
        "SOURCE_RETRIEVAL",
    ) is None
