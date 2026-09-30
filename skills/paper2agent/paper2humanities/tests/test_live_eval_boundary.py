import json
from pathlib import Path

from paper2humanities.blind_eval import score_panel
from paper2humanities.live_eval import generate_responses

ROOT = Path(__file__).resolve().parents[1]


def _gold():
    records = []
    for i in range(40):
        records.append({
            "query_id": f"q{i}", "query": "question",
            "expected_type": "AUTHOR_CLAIM", "expected_voice": "AUTHOR",
            "expected_source": "s1", "expected_page": 1,
            "allowed_answer_types": ["AUTHOR_CLAIM"], "forbidden_answer_types": [],
            "gold_evidence_span": "grounded evidence",
            "adversarial_category": "author_claim", "review_status": "REVIEWED",
        })
    return {"panel_type": "BLIND_ADVERSARIAL_PANEL", "query_count": 40, "records": records}


def _responses():
    return {"responses": [
        {"query_id": f"q{i}", "predicted_type": "AUTHOR_CLAIM", "predicted_voice": "AUTHOR",
         "source_id": "s1", "page": 1, "evidence_span": "grounded evidence", "decision": "SUPPORTED"}
        for i in range(40)
    ]}


def test_prewritten_response_scoring_is_not_reported_as_live():
    report = score_panel(_gold(), _responses())
    assert report["evaluation_scope"] == "COMMITTED_BLIND_RESPONSE_SET"


def test_response_generator_cli_has_no_gold_argument():
    text = (ROOT / "scripts" / "generate_deterministic_responses.py").read_text()
    assert 'add_argument("--gold"' not in text
    assert 'Path(args.gold)' not in text


def test_deterministic_generator_uses_query_and_reviewed_source_without_answer_key():
    queries = {"panel_id": "p", "queries": [{"query_id": "q", "query": "기술편집시대"}]}
    source = {
        "source_id": "s1", "source_sha256": "a" * 64,
        "pages": [{"page": 1, "items": [{"item_id": "i1", "kind": "text", "text": "지금은 기술복제를 넘어 기술편집의 시대이다."}]}],
    }
    result = generate_responses(queries, source)
    assert result["generation_method"] == "DETERMINISTIC_RETRIEVAL_CLASSIFICATION_V1"
    assert result["responses"][0]["query_id"] == "q"
    assert result["responses"][0]["source_id"] == "s1"


def test_committed_live_run_manifest_records_gold_isolation_and_not_external_blind():
    live_root = ROOT / "evals" / "live_runs"
    if not live_root.exists():
        return
    manifests = sorted(live_root.glob("*/manifest.json"))
    if not manifests:
        return
    manifest = json.loads(manifests[-1].read_text())
    assert manifest["gold_available_during_response_generation"] is False
    assert manifest["external_blind"] is False
    assert manifest["live_eval_mode"] == "DETERMINISTIC_BEHAVIORAL_EVAL"
    assert all("gold" not in arg.lower() for arg in manifest["generator_command_argv"])
