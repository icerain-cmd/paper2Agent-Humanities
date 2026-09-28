from __future__ import annotations
import json
from .model_adapter import ModelAdapter, require_live_adapter
SYSTEM_CONTRACT="""You are an evidence-bounded scholarly dialogue generator.
Use only supplied evidence for claims attributed to a paper or author. Copy support IDs,
pages, edition and evidence spans only from that evidence. Keep external voice external.
Never role-play the author. Never use memory as source evidence.
The output action MUST exactly copy input dialogue_action. Never use a reason code as action.
If evidence is insufficient, statement_type MUST be UNRESOLVED with support_ids=[],
pages=[], evidence_voice=UNKNOWN, evidence_span=null, semantic_support=UNSUPPORTED,
and relation_type=UNRESOLVED. Keep the input action unchanged.
AUTHOR_CLAIM may cite only the actor paper and edition. Other grounded turn types
may cite explicitly supplied supporting papers and editions.
Return the typed-turn JSON schema directly. Do not include hidden reasoning."""
def generate(adapter:ModelAdapter, payload:dict):
    require_live_adapter(adapter)
    result=adapter.generate_typed_turn(system_contract=SYSTEM_CONTRACT,payload=payload)
    return json.loads(result.text),result
