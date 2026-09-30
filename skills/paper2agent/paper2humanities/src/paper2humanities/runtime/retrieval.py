from __future__ import annotations
from dataclasses import dataclass
import math, re
from collections import Counter
from ..paper_agent import PaperAgent
from ..schema import StatementType

TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*|[가-힣]{2,}")
ALIASES = {
    "second technology": {"제2기술","zweite technik","second technology"},
    "third technology": {"제3기술","third technology"},
    "aura": {"아우라","aura"},
    "authenticity": {"진정성","진품성","echtheit","authenticity"},
    "distraction": {"정신분산","zerstreuung","distraction"},
    "immersion": {"정신몰입","몰입","immersion"},
    "play": {"유희","놀이","spiel","play"},
    "trust": {"신뢰화","trust"},
    "transparency": {"투명화","transparency"},
    "film": {"영화", "film", "kino", "cinema"},
    "audience": {"관객", "publikum", "public", "audience"},
    "examiner": {"시험관", "평가자", "examinator", "examiner", "begutachtende"},
    "attention": {"주의집중", "aufmerksamkeit", "attention"},
    "distance": {"거리", "ferne", "distance"},
}
@dataclass(frozen=True)
class RetrievalHit:
    statement_id: str
    score: float
    paper_id: str
    edition_id: str | None
    page: int | None
    evidence_span: str | None

def _terms(text: str) -> set[str]:
    t={m.group(0).lower() for m in TOKEN.finditer(text)}
    low=text.lower()
    for key,vals in ALIASES.items():
        if any(v in low for v in vals):
            t |= vals | {key}
    return t

def retrieve(agent: PaperAgent, query: str, limit: int=6, action: str="SOURCE_RETRIEVAL") -> tuple[list[RetrievalHit], dict]:
    edition = agent.edition_id or ""
    requested = re.findall(r"\b(?:v[23])\b|제[23]판|(?:zweite|dritte) fassung", query.lower())
    requested_edition = {"v2": "v2", "제2판": "v2", "zweite fassung": "v2",
                         "v3": "v3", "제3판": "v3", "dritte fassung": "v3"}
    if edition and requested and any(requested_edition[x] not in edition for x in requested):
        return [], {"query": query, "action": action, "candidate_statement_ids": [],
                    "candidate_scores": {}, "selected_statement_ids": [],
                    "selected_evidence": [], "rejected_candidates": [],
                    "reason": "EDITION_MISMATCH"}
    q=_terms(query)
    rows=[]
    docs=list(agent.store.values())
    df=Counter()
    doc_terms={}
    for s in docs:
        terms=_terms(" ".join(filter(None,[s.text,s.evidence_span,s.section])))
        doc_terms[s.statement_id]=terms
        for x in terms: df[x]+=1
    n=max(1,len(docs))
    for s in docs:
        terms=doc_terms[s.statement_id]
        common=q & terms
        if not common:
            continue
        if action == "AUTHOR_ATTRIBUTION" and s.evidence_voice and s.evidence_voice.value != "AUTHOR":
            continue
        if action == "EXTERNAL_ATTRIBUTION" and s.evidence_voice and s.evidence_voice.value != "EXTERNAL":
            continue
        score=sum(math.log((n+1)/(df[x]+0.5))+1 for x in common)
        if s.statement_type in {StatementType.SOURCE_QUOTE,StatementType.AUTHOR_CLAIM}: score+=0.25
        if score>0:
            rows.append(RetrievalHit(s.statement_id,score,s.paper_id or agent.paper_id,s.edition_id,s.page,s.evidence_span))
    rows.sort(key=lambda h:(-h.score,h.statement_id))
    chosen=rows[:limit]
    trace={
        "query":query,
        "action":action,
        "candidate_statement_ids":[x.statement_id for x in rows],
        "candidate_scores":{x.statement_id:round(x.score,6) for x in rows},
        "selected_statement_ids":[x.statement_id for x in chosen],
        "selected_evidence":[{"statement_id":x.statement_id,"paper_id":x.paper_id,"page":x.page,"evidence_span":x.evidence_span,"edition_id":x.edition_id} for x in chosen],
        "rejected_candidates":[x.statement_id for x in rows[limit:]],
    }
    return chosen,trace
