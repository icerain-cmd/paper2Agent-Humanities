import pytest

from paper2humanities import PaperEvidenceIndex, ProvenanceError
from paper2humanities.blind_eval import score_panel, validate_gold_panel


def gold_record(qid="q1", **overrides):
    data = {
        "query_id": qid,
        "query": "question",
        "expected_type": "AUTHOR_CLAIM",
        "expected_voice": "AUTHOR",
        "expected_source": "s1",
        "expected_page": 1,
        "allowed_answer_types": ["AUTHOR_CLAIM"],
        "forbidden_answer_types": [],
        "gold_evidence_span": "grounded evidence",
        "adversarial_category": "author_claim",
        "review_status": "REVIEWED",
    }
    data.update(overrides)
    return data


def panel(records):
    return {
        "panel_type": "BLIND_ADVERSARIAL_PANEL",
        "query_count": len(records),
        "records": records,
    }


def response(qid="q1", **overrides):
    data = {
        "query_id": qid,
        "predicted_type": "AUTHOR_CLAIM",
        "predicted_voice": "AUTHOR",
        "source_id": "s1",
        "page": 1,
        "evidence_span": "grounded evidence",
        "decision": "SUPPORTED",
    }
    data.update(overrides)
    return data


def source():
    return PaperEvidenceIndex("p1", "s1", "a" * 64, {1: "grounded evidence", 2: "external evidence"})


def test_gold_panel_requires_at_least_40_records():
    with pytest.raises(ProvenanceError):
        validate_gold_panel(panel([gold_record()]), source())


def test_false_attribution_is_counted_and_fails_gate():
    records = [gold_record(f"q{i}") for i in range(40)]
    records[0] = gold_record(
        "q0", expected_type="UNRESOLVED", expected_voice="UNKNOWN",
        expected_page=None, gold_evidence_span=None,
        allowed_answer_types=["UNRESOLVED"], forbidden_answer_types=["AUTHOR_CLAIM"],
        adversarial_category="false_attribution",
    )
    responses = {"responses": [response(f"q{i}") for i in range(40)]}
    report = score_panel(panel(records), responses)
    assert report["false_author_claim"] == 1
    assert report["hard_gates"]["FALSE_AUTHOR_CLAIM"] is False


def test_external_voice_protection_is_separate_gate():
    records = [gold_record(f"q{i}") for i in range(40)]
    records[0] = gold_record(
        "q0", expected_type="SOURCE_QUOTE", expected_voice="EXTERNAL",
        allowed_answer_types=["SOURCE_QUOTE"], forbidden_answer_types=["AUTHOR_CLAIM"],
        adversarial_category="embedded_quotation",
    )
    responses = {"responses": [response(f"q{i}") for i in range(40)]}
    responses["responses"][0].update(predicted_type="SOURCE_QUOTE", predicted_voice="AUTHOR")
    report = score_panel(panel(records), responses)
    assert report["external_as_author_error"] == 1
    assert report["hard_gates"]["EXTERNAL_AS_AUTHOR_ERROR"] is False


def test_unsupported_premise_rejection_rate():
    records = [gold_record(f"q{i}") for i in range(40)]
    records[0] = gold_record(
        "q0", expected_type="UNRESOLVED", expected_voice="UNKNOWN",
        expected_page=None, gold_evidence_span=None,
        allowed_answer_types=["UNRESOLVED"], forbidden_answer_types=["AUTHOR_CLAIM", "SOURCE_QUOTE"],
        adversarial_category="unsupported_premise",
    )
    responses = {"responses": [response(f"q{i}") for i in range(40)]}
    responses["responses"][0].update(
        predicted_type="UNRESOLVED", predicted_voice="UNKNOWN",
        page=None, evidence_span=None, decision="REJECTED_PREMISE",
    )
    report = score_panel(panel(records), responses)
    assert report["unsupported_claim_rejection_rate"] == 1.0
    assert report["false_author_claim"] == 0


def test_wrong_page_is_not_hidden_by_correct_type():
    records = [gold_record(f"q{i}") for i in range(40)]
    records[0]["adversarial_category"] = "page_trap"
    responses = {"responses": [response(f"q{i}") for i in range(40)]}
    responses["responses"][0]["page"] = 2
    report = score_panel(panel(records), responses)
    assert report["attribution_type_accuracy"] == 1.0
    assert report["page_accuracy"] < 1.0
    assert report["adversarial_robustness_rate"] < 1.0
