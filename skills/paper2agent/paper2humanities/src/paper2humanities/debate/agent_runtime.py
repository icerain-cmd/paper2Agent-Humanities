from __future__ import annotations
import json
from .models import DebateAction, DebateTurn
from .evidence import build_retrieval_query,retrieve_own_evidence
from ..runtime.model_adapter import validate_typed_turn

ACTION_MAP={
    DebateAction.POSITION:"INTERPRETATION",
    DebateAction.RESPONSE:"RESPONSE",
    DebateAction.CRITIQUE:"CRITIQUE",
    DebateAction.QUESTION:"RESEARCH_QUESTION",
    DebateAction.REBUTTAL:"RESPONSE",
    DebateAction.CLARIFICATION:"INTERPRETATION",
    DebateAction.CLOSING:"SYNTHESIS",
}

DEBATE_CONTRACT="""You are a scholarly paper-agent in a live academic debate.
Represent only the position supportable from the supplied OWN_EVIDENCE. You are not the historical
person and must not claim personal memories, intentions, or knowledge beyond the source. You may
directly address the opposing scholarly agent and respond to its most recent statement, but the
opponent statement is conversational context, never source evidence for your own claims.
Every substantive claim must be grounded only in OWN_EVIDENCE. Never cite opponent context as support.
When evidence is partial, state the limit explicitly. When evidence is insufficient, abstain.
Use Korean for the debate text unless the topic requires otherwise.
The output action must exactly equal INPUT_ACTION. Return exactly one typed-turn JSON object.
For grounded turns, support_ids and pages must come only from OWN_EVIDENCE; evidence_span must copy one
supplied evidence span exactly. actor_paper and actor_edition_id must equal the supplied agent identity.
CRITIQUE uses statement_type CRITIQUE; RESPONSE uses INTERPRETATION; RESEARCH_QUESTION and SYNTHESIS use
AI_SYNTHESIS; INTERPRETATION uses INTERPRETATION. Split grounded claims into claim-level entries.
"""

def generate_debate_turn(adapter, agent, session, action: DebateAction, targets: list[str]):
    opponent=session.turns[-1] if session.turns else None
    opponent_text=opponent.text if opponent else None
    query=build_retrieval_query(session.topic,session.active_issue,opponent_text,action.value)
    evidence,trace=retrieve_own_evidence(agent,query)
    input_action=ACTION_MAP[action]
    if not evidence:
        return DebateTurn(
            turn_id=f"turn-{session.current_turn+1:03d}",speaker_agent_id=agent.paper_id,
            target_agent_ids=targets,action=action,
            text="현재 제 corpus 안에서는 이 논점에 충분한 근거가 없습니다.",
            support_ids=[],pages=[],evidence=[],semantic_support="UNSUPPORTED",
            context_turn_ids=[opponent.turn_id] if opponent else [],verification_status="ABSTAINED"
        ),trace
    payload={
        "agent_identity":{"paper_id":agent.paper_id,"author":agent.author,"title":agent.title,
                          "edition_id":agent.edition_id},
        "topic":session.topic,"active_issue":session.active_issue,
        "debate_action":action.value,"INPUT_ACTION":input_action,
        "opponent_context":None if opponent is None else {
            "turn_id":opponent.turn_id,"speaker_agent_id":opponent.speaker_agent_id,
            "text":opponent.text},
        "OWN_EVIDENCE":evidence,
        "instruction":"Advance the debate. Engage the opponent's last point when one exists."
    }
    allowed={e["statement_id"]:e for e in evidence}

    def call_and_validate(call_payload):
        result=adapter.generate_typed_turn(system_contract=DEBATE_CONTRACT,payload=call_payload)
        raw=validate_typed_turn(json.loads(result.text))
        if raw["action"]!=input_action:
            raise ValueError("model action mismatch")
        if raw["actor_paper"]!=agent.paper_id or raw["actor_edition_id"]!=agent.edition_id:
            raise ValueError("actor identity mismatch")
        if not set(raw["support_ids"])<=set(allowed):
            raise ValueError("support outside own evidence")
        pages=sorted({allowed[s]["page"] for s in raw["support_ids"]})
        if sorted(raw["pages"])!=pages:
            raise ValueError("page/support mismatch")
        agent.validate_output_text(raw["text"])
        return raw,[allowed[s] for s in raw["support_ids"]]

    try:
        raw,ev=call_and_validate(payload)
        trace={**trace,"grounding_retry_count":0}
    except Exception as first_exc:
        retry_payload={**payload,
            "STRICT_GROUNDING_RETRY":True,
            "allowed_support_ids":list(allowed),
            "instruction":(
                "Retry this same debate turn. Use ONLY the listed allowed_support_ids; "
                "do not invent or recall any other statement_id. Pages must exactly match "
                "the chosen allowed evidence. If that cannot support the turn, abstain."
            )}
        try:
            raw,ev=call_and_validate(retry_payload)
            trace={**trace,"grounding_retry_count":1,
                   "first_grounding_error":f"{type(first_exc).__name__}: {first_exc}"}
        except Exception as exc:
            trace={**trace,"grounding_retry_count":1,
                   "first_grounding_error":f"{type(first_exc).__name__}: {first_exc}",
                   "generation_or_verification_error":f"{type(exc).__name__}: {exc}"}
            return DebateTurn(
                turn_id=f"turn-{session.current_turn+1:03d}",speaker_agent_id=agent.paper_id,
                target_agent_ids=targets,action=action,
                text="이 턴은 근거 검증을 통과하지 못해 발언을 보류합니다.",
                support_ids=[],pages=[],evidence=[],semantic_support="UNSUPPORTED",
                qualification=str(exc),context_turn_ids=[opponent.turn_id] if opponent else [],
                verification_status="REJECTED"
            ),trace
    return DebateTurn(
        turn_id=f"turn-{session.current_turn+1:03d}",speaker_agent_id=agent.paper_id,
        target_agent_ids=targets,action=action,text=raw["text"],
        support_ids=list(raw["support_ids"]),pages=list(raw["pages"]),evidence=ev,
        semantic_support=raw["semantic_support"],qualification=raw.get("qualification"),
        context_turn_ids=[opponent.turn_id] if opponent else [],verification_status="PASS"
    ),trace
