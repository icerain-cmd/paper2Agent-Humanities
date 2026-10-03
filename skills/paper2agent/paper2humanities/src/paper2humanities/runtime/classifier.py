from __future__ import annotations
from enum import Enum
import re


class QueryClass(str, Enum):
    SOURCE_RETRIEVAL = "SOURCE_RETRIEVAL"
    AUTHOR_ATTRIBUTION = "AUTHOR_ATTRIBUTION"
    EXTERNAL_ATTRIBUTION = "EXTERNAL_ATTRIBUTION"
    INTERPRETATION = "INTERPRETATION"
    CROSS_PAPER_COMPARE = "CROSS_PAPER_COMPARE"
    CRITIQUE = "CRITIQUE"
    RESPONSE = "RESPONSE"
    SYNTHESIS = "SYNTHESIS"
    RESEARCH_GAP = "RESEARCH_GAP"
    RESEARCH_QUESTION = "RESEARCH_QUESTION"
    UNSUPPORTED_PREMISE = "UNSUPPORTED_PREMISE"


PATTERNS = {
    QueryClass.RESEARCH_QUESTION: re.compile(
        r"research question|연구\s*질문|연구질문|검증 가능한 질문|질문 하나", re.I),
    QueryClass.RESEARCH_GAP: re.compile(
        r"research gap|\bgap\b|연구\s*공백|공백|미해결 연구 (?:문제|과제)|"
        r"아직 설명되지 않은|남는 연구 (?:문제|과제)", re.I),
    QueryClass.CROSS_PAPER_COMPARE: re.compile(
        r"cross[- ]paper|compare|comparison|비교|대조|대비하여 비교|"
        r"각 논문.*(?:대조|비교)|두 문헌.*(?:대조|비교)", re.I),
    QueryClass.CRITIQUE: re.compile(
        r"critique|critic(?:ize|ise)|비판|한계|취약점|이론적 취약|문제점을 논|"
        r"어떤 문제를 제기", re.I),
    QueryClass.RESPONSE: re.compile(
        r"respond|response|응답|답하라|반박", re.I),
    QueryClass.INTERPRETATION: re.compile(
        r"interpret|해석|어떤 관계|어떻게 연결|어떻게 맞물", re.I),
    QueryClass.EXTERNAL_ATTRIBUTION: re.compile(
        r"(?:외부|인용|external|quoted|quotation).*(?:누구|귀속|attribut|저자|author|주체)|"
        r"(?:누구|귀속|attribut|저자|author|주체).*(?:외부|인용|external|quoted|quotation)", re.I),
    QueryClass.AUTHOR_ATTRIBUTION: re.compile(
        r"누구|귀속|저자|author|attribut", re.I),
}


def classify(text: str) -> QueryClass:
    """Classify by scholarly intent precedence before generic retrieval cues."""
    s = text.lower()
    if PATTERNS[QueryClass.RESPONSE].search(s) and re.search(r"비판에\s*응답|critique.*respond|respond.*critique", s, re.I):
        return QueryClass.RESPONSE
    for intent in (
        QueryClass.RESEARCH_QUESTION,
        QueryClass.RESEARCH_GAP,
        QueryClass.CROSS_PAPER_COMPARE,
        QueryClass.CRITIQUE,
        QueryClass.RESPONSE,
        QueryClass.INTERPRETATION,
        QueryClass.EXTERNAL_ATTRIBUTION,
        QueryClass.AUTHOR_ATTRIBUTION,
    ):
        if PATTERNS[intent].search(s):
            return intent
    if "synth" in s or "종합" in s:
        return QueryClass.SYNTHESIS
    return QueryClass.SOURCE_RETRIEVAL


def classify_query(query: str) -> QueryClass:
    """Classify the raw question before retrieval or generation."""
    return classify(query)
