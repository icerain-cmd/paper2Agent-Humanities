from __future__ import annotations
from .models import DebateSession
from .orchestrator import DebateOrchestrator
from .agent_runtime import generate_debate_turn

class DebateEngine:
    def __init__(self, registry, adapter, orchestrator=None):
        self.registry=registry
        self.adapter=adapter
        self.orchestrator=orchestrator or DebateOrchestrator()

    def create_session(self, participant_ids, topic, max_turns=10):
        if len(participant_ids) not in (2,3): raise ValueError("select exactly 2 or 3 agents")
        if len(set(participant_ids))!=len(participant_ids): raise ValueError("duplicate agent")
        for aid in participant_ids: self.registry.get(aid)
        return DebateSession(topic=topic,participant_ids=list(participant_ids),max_turns=max_turns)

    def intervene(self, session, text):
        session.interventions.append({"at_turn":session.current_turn,"text":text})
        session.active_issue=text

    def step(self, session):
        if session.current_turn>=session.max_turns:
            session.status="COMPLETED"; return None
        speaker,targets,action=self.orchestrator.next_assignment(session)
        agent=self.registry.get(speaker)
        session.status="RUNNING"
        turn,trace=generate_debate_turn(self.adapter,agent,session,action,targets)
        session.turns.append(turn); session.current_turn+=1
        if session.current_turn>=session.max_turns: session.status="COMPLETED"
        return turn,trace

    def run(self, session, on_turn=None):
        while session.status!="COMPLETED":
            result=self.step(session)
            if result is None: break
            if on_turn: on_turn(result[0],session)
        return session
