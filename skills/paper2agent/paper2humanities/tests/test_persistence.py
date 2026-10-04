from pathlib import Path
import tempfile, sys, json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from paper2humanities.api.store import SQLiteSessionStore
from paper2humanities.debate.models import DebateSession, DebateTurn, DebateAction

def test_sqlite_session_roundtrip_and_events():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"p2h.db"
        store=SQLiteSessionStore(db)
        s=DebateSession(topic="test",participant_ids=["a","b"],max_turns=2)
        s.turns.append(DebateTurn("turn-001","a",["b"],DebateAction.POSITION,"hello",["s1"],[1],[],"SEMANTICALLY_SUPPORTED"))
        s.current_turn=1; s.status="READY"; s.interventions=[{"at_turn":1,"text":"focus"}]; s.active_issue="focus"
        store.put(s)
        store.append_event(s.session_id,"turn_completed",s.turns[0].to_dict())
        got=store.get(s.session_id)
        assert got.to_dict()==s.to_dict()
        events=store.events_after(s.session_id)
        assert len(events)==1 and events[0]["event"]=="turn_completed"
        assert store.counts()["READY"]==1

def test_running_becomes_interrupted_on_restart():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"p2h.db"
        first=SQLiteSessionStore(db)
        s=DebateSession(topic="restart",participant_ids=["a","b"],max_turns=4,status="RUNNING")
        first.put(s)
        second=SQLiteSessionStore(db)
        got=second.get(s.session_id)
        assert got.status=="INTERRUPTED"
        events=second.events_after(s.session_id)
        assert any(e["event"]=="session_interrupted" for e in events)

def test_completed_survives_restart_unchanged():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"p2h.db"
        first=SQLiteSessionStore(db)
        s=DebateSession(topic="done",participant_ids=["a","b"],max_turns=1,status="COMPLETED",current_turn=1)
        first.put(s)
        second=SQLiteSessionStore(db)
        got=second.get(s.session_id)
        assert got.status=="COMPLETED" and got.current_turn==1
        assert second.counts()["COMPLETED"]==1
