from __future__ import annotations
from enum import Enum
import re
class QueryClass(str,Enum):
    SOURCE_RETRIEVAL="SOURCE_RETRIEVAL"; AUTHOR_ATTRIBUTION="AUTHOR_ATTRIBUTION"
    EXTERNAL_ATTRIBUTION="EXTERNAL_ATTRIBUTION"; INTERPRETATION="INTERPRETATION"
    CROSS_PAPER_COMPARE="CROSS_PAPER_COMPARE"; CRITIQUE="CRITIQUE"; RESPONSE="RESPONSE"
    SYNTHESIS="SYNTHESIS"; RESEARCH_GAP="RESEARCH_GAP"; RESEARCH_QUESTION="RESEARCH_QUESTION"
    UNSUPPORTED_PREMISE="UNSUPPORTED_PREMISE"
def classify(text:str)->QueryClass:
    s=text.lower()
    if re.search(r"외부|인용|external|quoted|quotation",s) and re.search(r"누구|귀속|attribut|저자|author",s):return QueryClass.EXTERNAL_ATTRIBUTION
    if "respond" in s or "응답" in s:return QueryClass.RESPONSE
    if "critique" in s or "비판" in s or "긴장" in s:return QueryClass.CRITIQUE
    if "research question" in s or "연구질문" in s:return QueryClass.RESEARCH_QUESTION
    if "gap" in s or "공백" in s:return QueryClass.RESEARCH_GAP
    if "synth" in s or "종합" in s:return QueryClass.SYNTHESIS
    if "compare" in s or "비교" in s:return QueryClass.CROSS_PAPER_COMPARE
    if "누구" in s or "귀속" in s or "저자" in s or "author" in s:return QueryClass.AUTHOR_ATTRIBUTION
    if "해석" in s or "interpret" in s:return QueryClass.INTERPRETATION
    return QueryClass.SOURCE_RETRIEVAL

def classify_query(query: str) -> QueryClass:
    """Classify the raw question before retrieval or generation."""
    return classify(query)
