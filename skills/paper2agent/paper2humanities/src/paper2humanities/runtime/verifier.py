from __future__ import annotations
from ..schema import ProvenanceError
ALLOWED={"SEMANTICALLY_SUPPORTED","PARTIALLY_SUPPORTED","OVERSTATED","UNSUPPORTED"}
def publication_gate(turn:dict, known_support_ids:set[str], actor_paper:str|None=None, actor_edition_id:str|None=None):
    missing=set(turn.get("support_ids",()))-known_support_ids
    if missing: raise ProvenanceError(f"missing support IDs: {sorted(missing)}")
    if actor_paper and turn.get("actor_paper")!=actor_paper: raise ProvenanceError("wrong actor")
    if actor_edition_id is not None and turn.get("actor_edition_id")!=actor_edition_id: raise ProvenanceError("wrong edition")
    semantic=turn.get("semantic_support")
    if semantic not in ALLOWED: raise ProvenanceError("semantic review status required")
    if semantic in {"OVERSTATED","UNSUPPORTED"}: raise ProvenanceError("unsupported generation blocked")
    if semantic=="PARTIALLY_SUPPORTED" and not turn.get("qualification"): raise ProvenanceError("partial support requires qualification")
    if turn.get("statement_type")=="AUTHOR_CLAIM" and turn.get("actor_paper")=="synthesis-agent":
        raise ProvenanceError("synthesis cannot become AUTHOR_CLAIM")
    if turn.get("action")=="RESEARCH_QUESTION" and turn.get("statement_type")=="AUTHOR_CLAIM":
        raise ProvenanceError("research question cannot become author claim")
    return True
