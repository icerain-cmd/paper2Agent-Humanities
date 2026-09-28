from __future__ import annotations
from .retrieval import retrieve
from .generator import generate
from .model_adapter import ModelAdapter
def live_turn(adapter:ModelAdapter, agent, research_question:str, action:str, target:dict,
              history:list[dict]|None=None, supporting_agents=()):
    agents=(agent, *supporting_agents)
    identities=[(a.paper_id,a.edition_id) for a in agents]
    if len(identities)!=len(set(identities)):
        raise ValueError("duplicate allowed paper/edition")
    evidence=[]
    traces=[]
    seen_ids=set()
    for source_agent in agents:
        hits, source_trace=retrieve(source_agent,research_question)
        traces.append(source_trace)
        for hit in hits:
            if hit.statement_id in seen_ids:
                raise ValueError("ambiguous support ID across selected agents")
            seen_ids.add(hit.statement_id)
            source=source_agent.store.get(hit.statement_id)
            evidence.append({**hit.__dict__, "text":source.text,
                "statement_type":source.statement_type.value,
                "evidence_voice":source.evidence_voice.value if source.evidence_voice else "UNKNOWN",
                "citation":source.citation})
    trace={"selected_statement_ids":[e["statement_id"] for e in evidence],
           "selected_evidence":[{"statement_id":e["statement_id"],"paper_id":e["paper_id"],
               "edition_id":e["edition_id"],"page":e["page"],"evidence_span":e["evidence_span"]} for e in evidence],
           "source_traces":traces,"allowed_agents":[{"paper_id":p,"edition_id":v} for p,v in identities]}
    packet={
      "research_question":research_question,"dialogue_action":action,
      "actor_paper":agent.paper_id,"actor_edition_id":agent.edition_id,
      "target":target,"evidence":evidence,
      "dialogue_history":history or [],
      "output_contract":{"action":"copy dialogue_action exactly",
          "grounded":"non-UNRESOLVED requires support_ids, pages, evidence_span",
          "abstention":{"statement_type":"UNRESOLVED","support_ids":[],"pages":[],
              "evidence_voice":"UNKNOWN","evidence_span":None,
              "semantic_support":"UNSUPPORTED","relation_type":"UNRESOLVED"}}
    }
    turn,model_result=generate(adapter,packet)
    return turn,trace,model_result
