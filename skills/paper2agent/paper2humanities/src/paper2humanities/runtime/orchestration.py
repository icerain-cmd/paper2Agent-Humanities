from __future__ import annotations
from .retrieval import retrieve
from .generator import generate
from .model_adapter import ModelAdapter
from .attribution import enrich_attribution_axes
import re

INTERPRETIVE_REQUEST = re.compile(
    r"같은 저자 목소리|단일 주장|원래 명제|개념적 (?:동일성|간극)|"
    r"비판|한정|충분히|비교|대조|반박|취약점|"
    r"compare|distinguish|critique|rebut|evaluate|same claim|same author voice",
    re.IGNORECASE,
)
DIRECT_FACTUAL_RETRIEVAL = re.compile(
    r"직접 근거|근거(?:를| 페이지를?)? 찾아|해당 근거|근거 페이지|source passage|source page",
    re.IGNORECASE,
)
QUOTE_OR_DECLARATION_REQUEST = re.compile(
    r"직접 인용|인용문|문장|선언|quote|quotation|verbatim", re.IGNORECASE,
)

def response_type_hint(question: str, action: str) -> str | None:
    if action != "SOURCE_RETRIEVAL":
        return None
    if DIRECT_FACTUAL_RETRIEVAL.search(question) and not QUOTE_OR_DECLARATION_REQUEST.search(question):
        return "AUTHOR_CLAIM"
    if INTERPRETIVE_REQUEST.search(question):
        return "INTERPRETATION"
    return None


def normalize_direct_factual_turn(turn: dict, hint: str | None) -> dict:
    """Normalize only source-retrieval turns that contain no derived claim."""
    claims = turn.get("claims") or []
    if (hint == "AUTHOR_CLAIM"
            and turn.get("action") == "SOURCE_RETRIEVAL"
            and turn.get("statement_type") in {"AUTHOR_CLAIM", "INTERPRETATION"}
            and turn.get("evidence_voice") == "AUTHOR"
            and claims
            and all(claim.get("statement_type") == "AUTHOR_CLAIM" for claim in claims)):
        normalized = dict(turn)
        normalized["statement_type"] = "AUTHOR_CLAIM"
        normalized.pop("statement_form", None)
        normalized.pop("attribution_owner", None)
        return enrich_attribution_axes(normalized)
    return turn


def live_turn(adapter:ModelAdapter, agent, research_question:str, action:str, target:dict,
              history:list[dict]|None=None, supporting_agents=()):
    agents=(agent, *supporting_agents)
    identities=[(a.paper_id,a.edition_id) for a in agents]
    if len(identities)!=len(set(identities)):
        raise ValueError("duplicate allowed paper/edition")
    evidence=[]
    retrieval_hints=[]
    traces=[]
    seen_ids=set()
    grounded_counts={}
    for source_agent in agents:
        hits, source_trace=retrieve(source_agent,research_question,action=action)
        publishable_ids=[]
        hint_ids=[]
        for hit in hits:
            if hit.statement_id in seen_ids:
                raise ValueError("ambiguous support ID across selected agents")
            seen_ids.add(hit.statement_id)
            source=source_agent.store.get(hit.statement_id)
            if hit.page is None or not hit.evidence_span:
                hint_ids.append(hit.statement_id)
                retrieval_hints.append({"statement_id":hit.statement_id,"paper_id":hit.paper_id,
                    "edition_id":hit.edition_id,"text":source.text})
                continue
            publishable_ids.append(hit.statement_id)
            evidence.append({**hit.__dict__, "text":source.text,
                "statement_type":source.statement_type.value,
                "evidence_voice":source.evidence_voice.value if source.evidence_voice else "UNKNOWN",
                "citation":source.citation})
        grounded_counts[(source_agent.paper_id,source_agent.edition_id)]=len(publishable_ids)
        source_trace={**source_trace,"publishable_selected_statement_ids":publishable_ids,
                      "hint_statement_ids":hint_ids}
        traces.append(source_trace)
    cross_source_action=action in {"CRITIQUE","RESPONSE","CROSS_PAPER_COMPARE","RESEARCH_GAP","RESEARCH_QUESTION"}
    required_identities=identities if cross_source_action and len(agents)>1 else []
    missing_required=[{"paper_id":p,"edition_id":v} for p,v in required_identities
                      if grounded_counts.get((p,v),0)==0]
    trace={"action":action,"selected_statement_ids":[e["statement_id"] for e in evidence],
           "selected_evidence":[{"statement_id":e["statement_id"],"paper_id":e["paper_id"],
               "edition_id":e["edition_id"],"page":e["page"],"evidence_span":e["evidence_span"]} for e in evidence],
           "retrieval_hints":retrieval_hints,"source_traces":traces,
           "required_source_presence":[{"paper_id":p,"edition_id":v} for p,v in required_identities],
           "missing_required_sources":missing_required,
           "allowed_agents":[{"paper_id":p,"edition_id":v} for p,v in identities]}
    packet={
      "research_question":research_question,"dialogue_action":action,
      "actor_paper":agent.paper_id,"actor_edition_id":agent.edition_id,
      "target":target,"evidence":evidence,
      "dialogue_history":history or [],
      "output_contract":{"action":"copy dialogue_action exactly",
          "response_type_hint":response_type_hint(research_question, action),
          "grounded":"non-UNRESOLVED requires support_ids, pages, evidence_span",
          "required_source_presence":[{"paper_id":p,"edition_id":v} for p,v in required_identities],
          "missing_required_sources":missing_required,
          "missing_source_rule":"if missing_required_sources is non-empty, abstain",
          "abstention":{"statement_type":"UNRESOLVED","support_ids":[],"pages":[],
              "evidence_voice":"UNKNOWN","evidence_span":None,
              "semantic_support":"UNSUPPORTED","relation_type":"UNRESOLVED"}}
    }
    turn,model_result=generate(adapter,packet)
    turn=normalize_direct_factual_turn(turn, packet["output_contract"]["response_type_hint"])
    return turn,trace,model_result
