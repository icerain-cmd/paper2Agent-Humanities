from pathlib import Path
import json, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fastapi.testclient import TestClient
from paper2humanities.api import create_app
from paper2humanities.runtime.model_adapter import ModelAdapter, ModelResult

class FakeAdapter(ModelAdapter):
    provider="fake"; model="fake"
    def available(self): return True
    def generate_typed_turn(self, *, system_contract, payload):
        ev=payload["OWN_EVIDENCE"][0]
        action=payload["INPUT_ACTION"]
        st={"CRITIQUE":"CRITIQUE","RESPONSE":"INTERPRETATION",
            "RESEARCH_QUESTION":"AI_SYNTHESIS","SYNTHESIS":"AI_SYNTHESIS"}.get(action,"INTERPRETATION")
        obj={
            "text":f"{payload['agent_identity']['paper_id']} live turn",
            "statement_type":st,"evidence_voice":ev["evidence_voice"],
            "support_ids":[ev["statement_id"]],"pages":[ev["page"]],
            "relation_type":"QUALIFIES","actor_paper":payload["agent_identity"]["paper_id"],
            "actor_edition_id":payload["agent_identity"]["edition_id"],"action":action,
            "semantic_support":"SEMANTICALLY_SUPPORTED","evidence_sufficiency":"SUFFICIENT",
            "qualification":None,"evidence_span":ev["evidence_span"],
            "claims":[{"text":"grounded","statement_type":"INTERPRETATION","support_ids":[ev["statement_id"]]}]
        }
        return ModelResult(json.dumps(obj,ensure_ascii=False),self.provider,self.model,{},"x")

def client():
    app=create_app(ROOT)
    app.state.debate.engine.adapter=FakeAdapter()
    return TestClient(app)

def test_debate_ui_route():
    c=client()
    r=c.get("/debate")
    assert r.status_code==200
    assert "Live Scholarly Debate" in r.text
    js=c.get("/debate-static/app.js")
    assert js.status_code==200 and "EventSource" in js.text


def test_agents_and_session_creation():
    c=client()
    a=c.get("/api/debate/agents")
    assert a.status_code==200 and len(a.json()["agents"])>=3
    assert a.json()["registry"]["loaded"]>=3
    reload_result=c.post("/api/debate/agents/reload")
    assert reload_result.status_code==200
    assert reload_result.json()["registry"]["loaded"]>=3
    r=c.post("/api/debate/sessions",json={
        "agent_ids":["benjamin-artwork-v2","lee-aura-2019"],"topic":"아우라","max_turns":2})
    assert r.status_code==200
    assert r.json()["participant_ids"]==["benjamin-artwork-v2","lee-aura-2019"]

def test_next_and_intervention():
    c=client()
    s=c.post("/api/debate/sessions",json={
        "agent_ids":["benjamin-artwork-v2","lee-aura-2019"],"topic":"아우라","max_turns":2}).json()
    sid=s["session_id"]
    i=c.post(f"/api/debate/sessions/{sid}/intervene",json={"text":"거리 개념으로 좁혀라"})
    assert i.status_code==200 and i.json()["active_issue"]=="거리 개념으로 좁혀라"
    n=c.post(f"/api/debate/sessions/{sid}/next")
    assert n.status_code==200
    assert n.json()["turn"]["speaker_agent_id"]=="benjamin-artwork-v2"

def test_background_start_and_state():
    c=client()
    s=c.post("/api/debate/sessions",json={
        "agent_ids":["benjamin-artwork-v2","lee-aura-2019","benjamin-artwork-v3"],
        "topic":"아우라와 진정성","max_turns":3}).json()
    sid=s["session_id"]
    assert c.post(f"/api/debate/sessions/{sid}/start").status_code==200
    for _ in range(50):
        state=c.get(f"/api/debate/sessions/{sid}").json()
        if state["status"]=="COMPLETED": break
        time.sleep(.02)
    assert state["status"]=="COMPLETED" and len(state["turns"])==3
    events=c.app.state.debate.events[sid]
    names=[x["event"] for x in events]
    assert names.count("turn_completed")==3
    assert names[-1]=="debate_completed"
    assert "agent_thinking" in names and "evidence_retrieved" in names
