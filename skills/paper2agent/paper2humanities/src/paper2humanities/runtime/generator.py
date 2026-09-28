from __future__ import annotations
import json
from .model_adapter import ModelAdapter, require_live_adapter
SYSTEM_CONTRACT="""You are an evidence-bounded scholarly dialogue generator.
Use only supplied evidence for claims attributed to a paper or author.
Never role-play the author. Never use memory as source evidence.
If evidence is insufficient, output UNRESOLVED, INSUFFICIENT_EVIDENCE,
ATTRIBUTION_UNCLEAR, EDITION_CONFLICT, or NO_SOURCE_SUPPORTED_RESPONSE.
Return one JSON object only. Do not include hidden reasoning."""
def generate(adapter:ModelAdapter, payload:dict):
    require_live_adapter(adapter)
    result=adapter.generate_typed_turn(system_contract=SYSTEM_CONTRACT,payload=payload)
    return json.loads(result.text),result
