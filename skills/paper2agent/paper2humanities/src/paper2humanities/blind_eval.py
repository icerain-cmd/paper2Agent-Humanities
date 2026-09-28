"""Blind/adversarial evaluation utilities for Paper2Agent-Humanities."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .provenance import PaperEvidenceIndex, canonical_text
from .schema import ProvenanceError

REQUIRED_GOLD_FIELDS = {
    "query_id", "query", "expected_type", "expected_voice", "expected_source",
    "expected_page", "allowed_answer_types", "forbidden_answer_types",
    "gold_evidence_span", "adversarial_category", "review_status",
}
KNOWN_CATEGORIES = {
    "author_claim", "false_attribution", "embedded_quotation",
    "interpretation_promotion", "concept_neighbor", "page_trap",
    "unsupported_premise", "mixed_voice", "ambiguous_attribution",
}


def validate_gold_panel(panel: dict[str, Any], index: PaperEvidenceIndex) -> dict[str, Any]:
    if panel.get("panel_type") != "BLIND_ADVERSARIAL_PANEL":
        raise ProvenanceError("gold panel must declare BLIND_ADVERSARIAL_PANEL")
    records = panel.get("records")
    if not isinstance(records, list) or len(records) < 40:
        raise ProvenanceError("gold panel requires at least 40 records")
    if panel.get("query_count") != len(records):
        raise ProvenanceError("query_count does not match records")
    ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    for rec in records:
        if set(rec) < REQUIRED_GOLD_FIELDS:
            missing = REQUIRED_GOLD_FIELDS - set(rec)
            raise ProvenanceError(f"gold record missing fields: {sorted(missing)}")
        qid = rec["query_id"]
        if not isinstance(qid, str) or not qid or qid in ids:
            raise ProvenanceError("gold query_id values must be unique and nonempty")
        ids.add(qid)
        if rec["review_status"] != "REVIEWED":
            raise ProvenanceError(f"gold record is not reviewed: {qid}")
        category = rec["adversarial_category"]
        if category not in KNOWN_CATEGORIES:
            raise ProvenanceError(f"unknown adversarial category: {category}")
        category_counts[category] += 1
        if rec["expected_source"] != index.source_id:
            raise ProvenanceError(f"gold source mismatch: {qid}")
        page, span = rec["expected_page"], rec["gold_evidence_span"]
        if (page is None) != (span is None):
            raise ProvenanceError(f"page/span must both be present or absent: {qid}")
        if page is not None:
            if not isinstance(page, int) or page < 1 or not index.contains(page, span):
                raise ProvenanceError(f"gold evidence does not resolve to source page: {qid}")
        elif rec["expected_type"] != "UNRESOLVED":
            raise ProvenanceError(f"non-UNRESOLVED gold record lacks source evidence: {qid}")
        if rec["expected_type"] == "AUTHOR_CLAIM" and rec["expected_voice"] != "AUTHOR":
            raise ProvenanceError(f"AUTHOR_CLAIM gold requires AUTHOR voice: {qid}")
        if rec["expected_voice"] == "EXTERNAL" and rec["expected_type"] == "AUTHOR_CLAIM":
            raise ProvenanceError(f"external voice cannot be AUTHOR_CLAIM: {qid}")
        if rec["expected_type"] not in rec["allowed_answer_types"]:
            raise ProvenanceError(f"expected type must be allowed: {qid}")
        if rec["expected_type"] in rec["forbidden_answer_types"]:
            raise ProvenanceError(f"expected type cannot be forbidden: {qid}")
    return {
        "gold_review": "PASS",
        "panel_size": len(records),
        "category_counts": dict(sorted(category_counts.items())),
        "source_sha256": index.source_sha256,
    }


def score_panel(gold: dict[str, Any], responses: dict[str, Any]) -> dict[str, Any]:
    records = gold["records"]
    response_list = responses.get("responses")
    if not isinstance(response_list, list):
        raise ProvenanceError("responses must be an array")
    by_id = {item.get("query_id"): item for item in response_list}
    if len(by_id) != len(response_list):
        raise ProvenanceError("response query_id values must be unique")
    gold_ids = {rec["query_id"] for rec in records}
    if set(by_id) != gold_ids:
        raise ProvenanceError("response IDs must exactly match gold panel IDs")

    type_ok = voice_ok = page_ok = span_ok = robust = 0
    page_total = span_total = 0
    unsupported_total = unsupported_rejected = 0
    false_author_claim = external_as_author = interpretation_promotion = 0
    failures: list[dict[str, Any]] = []

    for rec in records:
        pred = by_id[rec["query_id"]]
        type_match = pred.get("predicted_type") == rec["expected_type"]
        voice_match = pred.get("predicted_voice") == rec["expected_voice"]
        type_ok += int(type_match)
        voice_ok += int(voice_match)

        page_match = True
        if rec["expected_page"] is not None:
            page_total += 1
            page_match = pred.get("page") == rec["expected_page"]
            page_ok += int(page_match)

        span_match = True
        if rec["gold_evidence_span"] is not None:
            span_total += 1
            span_match = (
                canonical_text(pred.get("evidence_span") or "")
                == canonical_text(rec["gold_evidence_span"])
            )
            span_ok += int(span_match)

        if rec["expected_type"] == "UNRESOLVED":
            unsupported_total += 1
            unsupported_rejected += int(pred.get("predicted_type") == "UNRESOLVED")

        if pred.get("predicted_type") == "AUTHOR_CLAIM" and rec["expected_type"] != "AUTHOR_CLAIM":
            false_author_claim += 1
        if rec["expected_voice"] == "EXTERNAL" and pred.get("predicted_voice") == "AUTHOR":
            external_as_author += 1
        if rec["expected_type"] == "INTERPRETATION" and pred.get("predicted_type") == "AUTHOR_CLAIM":
            interpretation_promotion += 1

        row_ok = type_match and voice_match and page_match and span_match
        robust += int(row_ok)
        if not row_ok:
            failures.append({
                "query_id": rec["query_id"],
                "category": rec["adversarial_category"],
                "type_match": type_match,
                "voice_match": voice_match,
                "page_match": page_match,
                "span_match": span_match,
            })

    total = len(records)
    report = {
        "evaluation_scope": "BLIND_ADVERSARIAL_PANEL",
        "panel_size": total,
        "attribution_type_accuracy": type_ok / total,
        "evidence_voice_accuracy": voice_ok / total,
        "page_accuracy": page_ok / page_total if page_total else 1.0,
        "evidence_span_accuracy": span_ok / span_total if span_total else 1.0,
        "unsupported_claim_rejection_rate": (
            unsupported_rejected / unsupported_total if unsupported_total else 1.0
        ),
        "false_author_claim": false_author_claim,
        "external_as_author_error": external_as_author,
        "interpretation_promotion_error": interpretation_promotion,
        "adversarial_robustness_rate": robust / total,
        "failures": failures,
        "hard_gates": {
            "FALSE_AUTHOR_CLAIM": false_author_claim == 0,
            "EXTERNAL_AS_AUTHOR_ERROR": external_as_author == 0,
        },
    }
    return report
