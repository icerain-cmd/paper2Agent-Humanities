from __future__ import annotations
from .retrieval import retrieve
from .generator import generate
from .model_adapter import ModelAdapter
def live_turn(adapter:ModelAdapter, agent, research_question:str, action:str, target:dict, history:list[dict]|None=None):
    hits,trace=retrieve(agent,research_question)
    packet={
      "research_question":research_question,"dialogue_action":action,
      "actor_paper":agent.paper_id,"actor_edition_id":agent.edition_id,
      "target":target,"evidence":[h.__dict__ for h in hits],
      "dialogue_history":history or [],
      "output_contract":{"statement_type":"typed","support_ids":"required","pages":"required when grounded",
                         "relation_type":"required","abstain_if_insufficient":True}
    }
    turn,model_result=generate(adapter,packet)
    return turn,trace,model_result
