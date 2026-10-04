from __future__ import annotations
import difflib, json, re
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
    DebateAction.REVISION:"SYNTHESIS",
    DebateAction.CLOSING:"SYNTHESIS",
}

LENGTH_POLICY={
    DebateAction.POSITION:(180,280,120,340),
    DebateAction.CRITIQUE:(180,280,120,340),
    DebateAction.REBUTTAL:(180,280,120,340),
    DebateAction.RESPONSE:(180,280,120,340),
    DebateAction.QUESTION:(80,140,55,180),
    DebateAction.CLARIFICATION:(140,220,90,280),
    DebateAction.REVISION:(140,220,90,280),
    DebateAction.CLOSING:(300,450,200,540),
}

DEBATE_CONTRACT="""You are a scholarly paper-agent in Debate Protocol V2.
Represent only the position supportable from supplied OWN_EVIDENCE. You are not the historical person.
Opponent statements are conversational targets, never evidence for your claims.

V2 argument discipline:
1. State the turn's central thesis early and clearly.
2. When an opponent exists, directly engage one concrete opponent claim rather than merely summarizing it.
3. Advance the debate: distinguish, qualify, challenge, revise, or narrow a proposition.
4. Do not retreat to 'the evidence cannot decide' as the whole answer. If evidence is limited, first state the strongest defensible proposition, then state the limit.
5. Never repeat your earlier position in substantially the same wording. Add a new distinction, consequence, counterargument, qualification, or research implication.
6. Every substantive claim must be grounded only in OWN_EVIDENCE. Never cite opponent context as support.
7. Use Korean unless the topic requires another language.

Debate metadata:
- thesis: one concise sentence stating the current position.
- target_claim: the specific opponent claim engaged; null only when there is no opponent to target.
- stance_update: MAINTAIN, REVISE, or NARROW. For POSITION use MAINTAIN. For later turns, choose honestly.
- unresolved_point: one concise remaining issue or null if none.

Action discipline:
- POSITION: answer the debate question with a defensible thesis, not a literature summary.
- CRITIQUE: identify the weakest premise or inference in the opponent's claim.
- REBUTTAL/RESPONSE: answer the criticism directly before adding your own distinction.
- RESEARCH_QUESTION: ask one difficult cross-examination question, but first explain why the question matters.
- REVISION: explicitly say how the initial thesis is maintained, revised, or narrowed after debate.
- CLOSING: separate agreement, core disagreement, and remaining research question.

Output action must exactly equal INPUT_ACTION. For grounded turns, support_ids/pages must come only from OWN_EVIDENCE;
evidence_span must copy one supplied span exactly. actor_paper and actor_edition_id must match the agent.
CRITIQUE uses statement_type CRITIQUE; RESPONSE uses INTERPRETATION; RESEARCH_QUESTION and SYNTHESIS use AI_SYNTHESIS;
INTERPRETATION uses INTERPRETATION. Split grounded claims into claim-level entries.
"""

def _eojeol_count(text:str)->int:
    return len([x for x in re.split(r"\s+",text.strip()) if x])

def _similarity(a:str,b:str)->float:
    a=" ".join(a.lower().split()); b=" ".join(b.lower().split())
    if not a or not b: return 0.0
    return difflib.SequenceMatcher(None,a,b).ratio()

def _latest_turn_by(session,agent_ids):
    wanted=set(agent_ids)
    for turn in reversed(session.turns):
        if turn.speaker_agent_id in wanted:
            return turn
    return None

def _latest_own_thesis(session,agent_id):
    for turn in reversed(session.turns):
        if turn.speaker_agent_id==agent_id and turn.thesis:
            return turn.thesis
    return None

def generate_debate_turn(adapter, agent, session, action: DebateAction, targets: list[str]):
    opponent=_latest_turn_by(session,targets) or (session.turns[-1] if session.turns else None)
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
            context_turn_ids=[opponent.turn_id] if opponent else [],verification_status="ABSTAINED",
            thesis=None,target_claim=opponent_text,stance_update="NARROW",unresolved_point=session.active_issue or session.topic,
        ),trace

    target_lo,target_hi,accept_lo,accept_hi=LENGTH_POLICY[action]
    own_recent=[t.text for t in session.turns if t.speaker_agent_id==agent.paper_id][-3:]
    previous_thesis=_latest_own_thesis(session,agent.paper_id)
    payload={
        "agent_identity":{"paper_id":agent.paper_id,"author":agent.author,"title":agent.title,
                          "edition_id":agent.edition_id},
        "topic":session.topic,"active_issue":session.active_issue,
        "debate_action":action.value,"INPUT_ACTION":input_action,
        "opponent_context":None if opponent is None else {
            "turn_id":opponent.turn_id,"speaker_agent_id":opponent.speaker_agent_id,
            "text":opponent.text,"thesis":opponent.thesis},
        "previous_own_thesis":previous_thesis,
        "recent_own_turns":own_recent,
        "OWN_EVIDENCE":evidence,
        "length_guidance":{
            "unit":"Korean eojeol/space-separated words",
            "target_min":target_lo,"target_max":target_hi,
            "priority":"argument quality over filler; do not pad by repeating evidence"
        },
        "instruction":"Advance the argument under Debate Protocol V2. Lead with a clear thesis and directly engage the target claim."
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
        thesis=(raw.get("thesis") or "").strip()
        target_claim=(raw.get("target_claim") or "").strip()
        stance=raw.get("stance_update")
        if not thesis:
            raise ValueError("V2 thesis required")
        if action!=DebateAction.POSITION and opponent is not None and not target_claim:
            raise ValueError("V2 target_claim required")
        if stance not in {"MAINTAIN","REVISE","NARROW"}:
            raise ValueError("V2 stance_update required")
        count=_eojeol_count(raw["text"])
        if getattr(adapter,"provider","")!="fake":
            if count<accept_lo or count>accept_hi:
                raise ValueError(f"V2 length out of range: {count} words, accepted {accept_lo}-{accept_hi}")
            if any(_similarity(raw["text"],old)>=0.72 for old in own_recent):
                raise ValueError("V2 excessive repetition of own prior turn")
        agent.validate_output_text(raw["text"])
        return raw,[allowed[s] for s in raw["support_ids"]],count

    try:
        raw,ev,word_count=call_and_validate(payload)
        trace={**trace,"grounding_retry_count":0,"v2_word_count":word_count}
    except Exception as first_exc:
        retry_payload={**payload,
            "STRICT_GROUNDING_RETRY":True,
            "allowed_support_ids":list(allowed),
            "instruction":(
                "Retry the same V2 debate turn. Correct the failure. Use ONLY allowed_support_ids. "
                "Keep pages exact. Provide thesis/target_claim/stance_update/unresolved_point. "
                f"Write within the accepted length range {accept_lo}-{accept_hi} words without padding or repetition. "
                "If evidence is limited, make the strongest defensible thesis first and then qualify it."
            )}
        try:
            raw,ev,word_count=call_and_validate(retry_payload)
            trace={**trace,"grounding_retry_count":1,"v2_word_count":word_count,
                   "first_grounding_error":f"{type(first_exc).__name__}: {first_exc}"}
        except Exception as exc:
            trace={**trace,"grounding_retry_count":1,
                   "first_grounding_error":f"{type(first_exc).__name__}: {first_exc}",
                   "generation_or_verification_error":f"{type(exc).__name__}: {exc}"}
            return DebateTurn(
                turn_id=f"turn-{session.current_turn+1:03d}",speaker_agent_id=agent.paper_id,
                target_agent_ids=targets,action=action,
                text="이 턴은 V2 논증·근거 검증을 통과하지 못해 발언을 보류합니다.",
                support_ids=[],pages=[],evidence=[],semantic_support="UNSUPPORTED",
                qualification=str(exc),context_turn_ids=[opponent.turn_id] if opponent else [],
                verification_status="REJECTED",thesis=None,target_claim=opponent_text,
                stance_update="NARROW",unresolved_point=session.active_issue or session.topic,
            ),trace

    return DebateTurn(
        turn_id=f"turn-{session.current_turn+1:03d}",speaker_agent_id=agent.paper_id,
        target_agent_ids=targets,action=action,text=raw["text"],
        support_ids=list(raw["support_ids"]),pages=list(raw["pages"]),evidence=ev,
        semantic_support=raw["semantic_support"],qualification=raw.get("qualification"),
        context_turn_ids=[opponent.turn_id] if opponent else [],verification_status="PASS",
        thesis=raw.get("thesis"),target_claim=raw.get("target_claim"),
        stance_update=raw.get("stance_update"),unresolved_point=raw.get("unresolved_point"),
    ),trace
