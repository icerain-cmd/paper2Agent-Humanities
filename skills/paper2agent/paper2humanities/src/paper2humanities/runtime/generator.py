from __future__ import annotations
import json
from .model_adapter import ModelAdapter, require_live_adapter
SYSTEM_CONTRACT="""You are an evidence-bounded scholarly dialogue generator.
Use only supplied evidence for claims attributed to a paper or author. Copy support IDs,
pages, edition and evidence spans only from that evidence. Keep external voice external.
For every grounded turn, evidence_span MUST be copied exactly from one selected evidence item,
and evidence_voice MUST exactly equal that same item's evidence_voice. pages MUST equal the
unique page values of all support_ids used. For CRITIQUE, use an actor-paper passage as the
anchor evidence_span whenever the actor paper has relevant supplied evidence; therefore its
anchor voice is AUTHOR. CRITIQUE action requires statement_type=CRITIQUE. RESPONSE requires
statement_type=INTERPRETATION or AI_SYNTHESIS. ISSUE, RESEARCH_GAP, RESEARCH_QUESTION, and
SYNTHESIS require statement_type=AI_SYNTHESIS. Set evidence_sufficiency to SUFFICIENT, PARTIAL,
INSUFFICIENT, or CONFLICTING from the supplied evidence packet. If support is only partial,
semantic_support MUST be PARTIALLY_SUPPORTED and qualification MUST contain a concise explicit
boundary statement; relation_type should normally be QUALIFIES. For fully supported turns set
qualification=null. If evidence is insufficient or conflicting for the requested substantive claim,
abstain rather than overstate.
Never role-play the author. Never use memory as source evidence.
The output action MUST exactly copy input dialogue_action. Never use a reason code as action.
If evidence is insufficient, statement_type MUST be UNRESOLVED with support_ids=[],
pages=[], evidence_voice=UNKNOWN, evidence_span=null, semantic_support=UNSUPPORTED,
evidence_sufficiency=INSUFFICIENT or CONFLICTING, qualification=null,
and relation_type=UNRESOLVED. Keep the input action unchanged.
AUTHOR_CLAIM may cite only the actor paper and edition. Other grounded turn types
may cite explicitly supplied supporting papers and editions.
Return the typed-turn JSON schema directly. Do not include hidden reasoning."""
def generate(adapter:ModelAdapter, payload:dict):
    require_live_adapter(adapter)
    result=adapter.generate_typed_turn(system_contract=SYSTEM_CONTRACT,payload=payload)
    return json.loads(result.text),result
