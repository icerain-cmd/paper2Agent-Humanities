from __future__ import annotations
from .models import DebateAction, DebateSession

TWO_AGENT_PLAN=[
    DebateAction.POSITION, DebateAction.RESPONSE, DebateAction.CRITIQUE,
    DebateAction.RESPONSE, DebateAction.QUESTION, DebateAction.RESPONSE,
    DebateAction.REBUTTAL, DebateAction.CLOSING,
]
THREE_AGENT_PLAN=[
    DebateAction.POSITION, DebateAction.RESPONSE, DebateAction.RESPONSE,
    DebateAction.CRITIQUE, DebateAction.CRITIQUE, DebateAction.QUESTION,
    DebateAction.RESPONSE, DebateAction.RESPONSE, DebateAction.CLOSING,
]

class DebateOrchestrator:
    def next_assignment(self, session: DebateSession):
        n=len(session.participant_ids)
        if n not in (2,3): raise ValueError("Milestone 1 supports exactly 2 or 3 agents")
        idx=session.current_turn
        plan=TWO_AGENT_PLAN if n==2 else THREE_AGENT_PLAN
        action=plan[min(idx,len(plan)-1)]
        speaker=session.participant_ids[idx % n]
        if n==2:
            targets=[session.participant_ids[(idx+1)%2]]
        else:
            targets=session.participant_ids[1:] if idx==0 else [session.participant_ids[(idx-1)%n]]
        return speaker,targets,action
