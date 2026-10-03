from __future__ import annotations
from ..runtime.retrieval import retrieve

def build_retrieval_query(topic: str, active_issue: str|None, opponent_text: str|None, action: str) -> str:
    parts=[topic]
    if active_issue: parts.append(active_issue)
    if opponent_text: parts.append(opponent_text)
    parts.append(action)
    return "\n".join(p for p in parts if p)

def retrieve_own_evidence(agent, query: str, limit: int=6):
    hits,trace=retrieve(agent,query,limit=limit,action="SOURCE_RETRIEVAL")
    evidence=[]
    for h in hits:
        s=agent.store.get(h.statement_id)
        if h.page is None or not h.evidence_span: continue
        if s.paper_id != agent.paper_id or s.source_id != agent.source_id or s.edition_id != agent.edition_id:
            continue
        evidence.append({"statement_id":h.statement_id,"paper_id":s.paper_id,"source_id":s.source_id,
                         "edition_id":s.edition_id,"page":s.page,"text":s.text,
                         "evidence_span":s.evidence_span,"citation":s.citation,
                         "statement_type":s.statement_type.value,
                         "evidence_voice":s.evidence_voice.value if s.evidence_voice else "UNKNOWN"})
    return evidence,trace
