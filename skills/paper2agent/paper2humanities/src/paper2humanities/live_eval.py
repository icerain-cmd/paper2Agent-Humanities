"""Gold-isolated deterministic behavioral evaluation runtime.

This module intentionally does not load evaluation gold during response generation.
It provides a conservative evidence-first classifier for environments where no
external inference model/runtime is available.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .provenance import canonical_text

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*|[가-힣]{2,}|\d+")
QUOTE_RE = re.compile(r"[‘“\"']([^’”\"']{2,})[’”\"']")

STOP = {
    "이용욱", "논문", "문장", "주장", "보는가", "인가", "라고", "으로", "에서",
    "어떻게", "무엇", "어떤", "자신의", "직접", "근거", "제시", "설명", "개념",
    "등록", "해도", "되는가", "볼", "수", "있는가", "인가", "아닌가", "해석",
    "답해도", "문장의", "문구", "대목", "의미", "시대", "기술",
}
EXTERNAL_MARKERS = (
    "벤야민은", "벤야민이", "발터 벤야민", "그로이스", "볼터와 그루신",
    "볼터", "그루신", "칙센트미하이", "최문규", "와인버거", "마노비치",
    "발레리", "심혜련", "김남시", "허윤정", "임석원", "진중권",
)
INTERPRETIVE_TRIGGERS = (
    "완전히", "동일한", "같은 개념", "규범적으로", "윤리적으로", "바람직",
    "필연적으로", "최종 판정", "더 옳", "폐기", "폐지", "회복", "곧 새로운",
    "단정", "승인", "핵심 수단", "보증", "인과법칙", "전혀 중요하지",
)
ATTRIBUTION_TRIGGERS = (
    "누구의", "자신의 주장", "직접 주장", "독창적", "귀속", "목소리",
    "고유 개념", "자신의 명명", "개념으로 등록",
)


@dataclass(frozen=True)
class SourceItem:
    page: int
    item_id: str
    text: str
    kind: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_runtime_source(work: Path, output: Path) -> dict[str, Any]:
    inv = json.loads((work / "inventory.json").read_text())
    if len(inv["sources"]) != 1:
        raise ValueError("live Phase-2 Lee runtime expects exactly one source")
    src = inv["sources"][0]
    doc = work / "documents" / src["id"]
    pages = []
    for page_file in sorted((doc / "pages").glob("page-*.json")):
        page = json.loads(page_file.read_text())
        if not page.get("reviewed"):
            raise ValueError(f"unreviewed page in live runtime source: {page.get('page')}")
        pages.append({
            "page": page["page"],
            "items": [
                {
                    "item_id": item["id"],
                    "kind": item.get("kind", ""),
                    "text": canonical_text(item.get("markdown", "")),
                }
                for item in page.get("items", [])
                if canonical_text(item.get("markdown", ""))
            ],
        })
    payload = {
        "schema_version": 1,
        "source_id": src["id"],
        "source_sha256": src["sha256"],
        "pages": pages,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in TOKEN_RE.finditer(canonical_text(text)) if len(m.group(0)) >= 2}


def _sentences(text: str) -> list[str]:
    text = canonical_text(text)
    parts = re.split(r"(?<=[.!?다요])\s+|(?<=\.)\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _distinctive_absent_terms(query: str, corpus: str) -> list[str]:
    corpus_lower = corpus.lower()
    absent = []
    quoted = [canonical_text(x) for x in QUOTE_RE.findall(query)]
    for term in quoted:
        if term and term.lower() not in corpus_lower:
            absent.append(term)
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query):
        if token.lower() not in corpus_lower and token.lower() not in {"pdf", "author", "claim"}:
            absent.append(token)
    return sorted(set(absent))


def _score_item(query: str, item: SourceItem) -> tuple[int, int]:
    q = _tokens(query) - STOP
    t = _tokens(item.text)
    overlap = len(q & t)
    quoted_bonus = sum(3 for phrase in QUOTE_RE.findall(query) if canonical_text(phrase) in item.text)
    return overlap + quoted_bonus, -len(item.text)


def _best_evidence(query: str, items: list[SourceItem]) -> tuple[SourceItem | None, str | None, int]:
    ranked = sorted(
        ((_score_item(query, item), item) for item in items),
        key=lambda pair: (pair[0][0], pair[0][1]),
        reverse=True,
    )
    if not ranked or ranked[0][0][0] <= 0:
        return None, None, 0
    score, item = ranked[0][0][0], ranked[0][1]
    qtokens = _tokens(query) - STOP
    candidates = _sentences(item.text) or [item.text]
    sentence = max(candidates, key=lambda s: len(qtokens & _tokens(s)))
    return item, sentence, score


def _voice(item: SourceItem, sentence: str) -> str:
    text = item.text
    sent_pos = text.find(sentence)
    start = max(0, sent_pos - 220) if sent_pos >= 0 else 0
    context = text[start: sent_pos + len(sentence) + 80] if sent_pos >= 0 else text[:320]
    if any(marker in context for marker in EXTERNAL_MARKERS):
        return "EXTERNAL"
    if item.kind == "text" and text.startswith(">"):
        return "EXTERNAL"
    return "AUTHOR"


def classify_query(query: str, source: dict[str, Any]) -> dict[str, Any]:
    items = [
        SourceItem(page["page"], item["item_id"], item["text"], item["kind"])
        for page in source["pages"]
        for item in page["items"]
    ]
    corpus = "\n".join(item.text for item in items)
    absent = _distinctive_absent_terms(query, corpus)
    item, span, retrieval_score = _best_evidence(query, items)

    if absent and item is None:
        return {
            "predicted_type": "UNRESOLVED", "predicted_voice": "UNKNOWN",
            "source_id": source["source_id"], "page": None, "evidence_span": None,
            "decision": "REJECTED_PREMISE", "reason": "distinctive query term absent from reviewed source",
            "absent_terms": absent, "retrieval_score": 0,
        }

    if item is None:
        return {
            "predicted_type": "UNRESOLVED", "predicted_voice": "UNKNOWN",
            "source_id": source["source_id"], "page": None, "evidence_span": None,
            "decision": "UNRESOLVED", "reason": "no source evidence retrieved",
            "absent_terms": absent, "retrieval_score": 0,
        }

    voice = _voice(item, span or item.text)
    lower = query.lower()

    if absent:
        # Conservative boundary: related evidence cannot rescue a premise containing a
        # distinctive concept/name absent from the reviewed paper.
        return {
            "predicted_type": "UNRESOLVED", "predicted_voice": "UNKNOWN",
            "source_id": source["source_id"], "page": None, "evidence_span": None,
            "decision": "REJECTED_PREMISE", "reason": "distinctive query term absent from reviewed source",
            "absent_terms": absent, "retrieval_score": retrieval_score,
        }

    if any(trigger in query for trigger in INTERPRETIVE_TRIGGERS):
        ptype = "INTERPRETATION"
        pvoice = "UNKNOWN"
        decision = "INTERPRETIVE"
    elif any(trigger in query for trigger in ATTRIBUTION_TRIGGERS) or voice == "EXTERNAL":
        ptype = "SOURCE_QUOTE" if voice == "EXTERNAL" else "AUTHOR_CLAIM"
        pvoice = voice
        decision = "SUPPORTED"
    else:
        ptype = "AUTHOR_CLAIM" if voice == "AUTHOR" else "SOURCE_QUOTE"
        pvoice = voice
        decision = "SUPPORTED"

    return {
        "predicted_type": ptype,
        "predicted_voice": pvoice,
        "source_id": source["source_id"],
        "page": item.page,
        "item_id": item.item_id,
        "evidence_span": span,
        "decision": decision,
        "reason": "deterministic lexical retrieval and conservative attribution classification",
        "absent_terms": absent,
        "retrieval_score": retrieval_score,
    }


def generate_responses(query_panel: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "panel_id": query_panel["panel_id"],
        "generation_method": "DETERMINISTIC_RETRIEVAL_CLASSIFICATION_V1",
        "responses": [
            {"query_id": row["query_id"], **classify_query(row["query"], source)}
            for row in query_panel["queries"]
        ],
    }
