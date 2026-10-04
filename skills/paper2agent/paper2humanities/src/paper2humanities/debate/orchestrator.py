from __future__ import annotations
from .models import DebateAction, DebateSession

def _two_agent_plan(max_turns:int):
    short=[
        (0,DebateAction.POSITION,[1]), (1,DebateAction.POSITION,[0]),
        (0,DebateAction.CRITIQUE,[1]), (1,DebateAction.CRITIQUE,[0]),
        (0,DebateAction.CLOSING,[1]), (1,DebateAction.CLOSING,[0]),
    ]
    standard=[
        (0,DebateAction.POSITION,[1]), (1,DebateAction.POSITION,[0]),
        (0,DebateAction.CRITIQUE,[1]), (1,DebateAction.CRITIQUE,[0]),
        (0,DebateAction.REBUTTAL,[1]), (1,DebateAction.REBUTTAL,[0]),
        (0,DebateAction.REVISION,[1]), (1,DebateAction.REVISION,[0]),
        (0,DebateAction.CLOSING,[1]), (1,DebateAction.CLOSING,[0]),
    ]
    deep=[
        (0,DebateAction.POSITION,[1]), (1,DebateAction.POSITION,[0]),
        (0,DebateAction.CRITIQUE,[1]), (1,DebateAction.CRITIQUE,[0]),
        (0,DebateAction.REBUTTAL,[1]), (1,DebateAction.REBUTTAL,[0]),
        (0,DebateAction.QUESTION,[1]), (1,DebateAction.RESPONSE,[0]),
        (1,DebateAction.QUESTION,[0]), (0,DebateAction.RESPONSE,[1]),
        (0,DebateAction.REVISION,[1]), (1,DebateAction.REVISION,[0]),
        (0,DebateAction.CLOSING,[1]), (1,DebateAction.CLOSING,[0]),
    ]
    return short if max_turns<=6 else standard if max_turns<=10 else deep

def _three_agent_plan(max_turns:int):
    short=[
        (0,DebateAction.POSITION,[1,2]), (1,DebateAction.POSITION,[0,2]), (2,DebateAction.POSITION,[0,1]),
        (0,DebateAction.CRITIQUE,[1]), (1,DebateAction.CRITIQUE,[2]), (2,DebateAction.CRITIQUE,[0]),
        (0,DebateAction.CLOSING,[1,2]), (1,DebateAction.CLOSING,[0,2]), (2,DebateAction.CLOSING,[0,1]),
    ]
    standard=[
        (0,DebateAction.POSITION,[1,2]), (1,DebateAction.POSITION,[0,2]), (2,DebateAction.POSITION,[0,1]),
        (0,DebateAction.CRITIQUE,[1]), (1,DebateAction.CRITIQUE,[2]), (2,DebateAction.CRITIQUE,[0]),
        (0,DebateAction.REBUTTAL,[2]), (1,DebateAction.REBUTTAL,[0]), (2,DebateAction.REBUTTAL,[1]),
        (0,DebateAction.REVISION,[1,2]), (1,DebateAction.REVISION,[0,2]), (2,DebateAction.REVISION,[0,1]),
        (0,DebateAction.CLOSING,[1,2]), (1,DebateAction.CLOSING,[0,2]), (2,DebateAction.CLOSING,[0,1]),
    ]
    deep=[
        (0,DebateAction.POSITION,[1,2]), (1,DebateAction.POSITION,[0,2]), (2,DebateAction.POSITION,[0,1]),
        (0,DebateAction.CRITIQUE,[1]), (1,DebateAction.CRITIQUE,[2]), (2,DebateAction.CRITIQUE,[0]),
        (0,DebateAction.REBUTTAL,[2]), (1,DebateAction.REBUTTAL,[0]), (2,DebateAction.REBUTTAL,[1]),
        (0,DebateAction.QUESTION,[1]), (1,DebateAction.QUESTION,[2]), (2,DebateAction.QUESTION,[0]),
        (0,DebateAction.RESPONSE,[2]), (1,DebateAction.RESPONSE,[0]), (2,DebateAction.RESPONSE,[1]),
        (0,DebateAction.REVISION,[1,2]), (1,DebateAction.REVISION,[0,2]), (2,DebateAction.REVISION,[0,1]),
        (0,DebateAction.CLOSING,[1,2]), (1,DebateAction.CLOSING,[0,2]), (2,DebateAction.CLOSING,[0,1]),
    ]
    return short if max_turns<=9 else standard if max_turns<=15 else deep

class DebateOrchestrator:
    def next_assignment(self, session: DebateSession):
        n=len(session.participant_ids)
        if n not in (2,3):
            raise ValueError("Debate Protocol V2 supports exactly 2 or 3 agents")
        plan=_two_agent_plan(session.max_turns) if n==2 else _three_agent_plan(session.max_turns)
        idx=session.current_turn
        if idx<len(plan):
            speaker_idx,action,target_indices=plan[idx]
        else:
            speaker_idx=idx%n
            action=DebateAction.CLOSING
            target_indices=[i for i in range(n) if i!=speaker_idx]
        speaker=session.participant_ids[speaker_idx]
        targets=[session.participant_ids[i] for i in target_indices]
        return speaker,targets,action
