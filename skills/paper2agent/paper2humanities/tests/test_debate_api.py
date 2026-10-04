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
            "thesis":"A grounded V2 thesis",
            "target_claim":None if payload.get("opponent_context") is None else "Opponent target claim",
            "stance_update":"MAINTAIN",
            "unresolved_point":"Remaining scholarly issue",
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
    events=c.app.state.debate.sessions.events_after(sid)
    names=[x["event"] for x in events]
    assert names.count("turn_completed")==3
    assert names[-1]=="debate_completed"
    assert "agent_thinking" in names and "evidence_retrieved" in names


def test_onboarding_api_valid_register_and_disable():
    import json, tempfile
    from paper2humanities.onboarding import OnboardingService
    from paper2humanities.debate import AgentRegistry
    app=create_app(ROOT)
    with tempfile.TemporaryDirectory() as td:
        state=app.state.debate
        state.onboarding=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        state.registry=AgentRegistry(ROOT/"fixtures",state.onboarding.active_dir)
        state.engine.registry=state.registry
        c=TestClient(app)
        data=json.loads((ROOT/"fixtures"/"lee-aura-2019-agent.json").read_text())
        data["paper_id"]="api-registered-test"
        data["title"]="API Registered Test"
        data["author"]="API Scholar"
        data["source"]["source_id"]="s-api-registered-test"
        data["source"]["sha256"]="3"*64
        for s in data["statements"]:
            if s.get("paper_id"): s["paper_id"]="api-registered-test"
            if s.get("source_id"): s["source_id"]="s-api-registered-test"
        up=c.post("/api/agents/onboarding/upload",json={"agent":data,"original_name":"test.json"})
        assert up.status_code==200
        oid=up.json()["onboarding_id"]
        val=c.post(f"/api/agents/onboarding/{oid}/validate")
        assert val.status_code==200 and val.json()["validation"]["status"]=="PASS"
        reg=c.post(f"/api/agents/onboarding/{oid}/register")
        assert reg.status_code==200
        agents=c.get("/api/debate/agents").json()["agents"]
        added=next(x for x in agents if x["agent_id"]=="api-registered-test")
        assert added["origin"]=="registered" and added["can_disable"] is True
        disable=c.delete("/api/agents/api-registered-test")
        assert disable.status_code==200 and disable.json()["status"]=="DISABLED"
        assert all(x["agent_id"]!="api-registered-test" for x in c.get("/api/debate/agents").json()["agents"])


def test_onboarding_api_blocks_invalid_and_builtin_disable():
    import json, tempfile
    from paper2humanities.onboarding import OnboardingService
    from paper2humanities.debate import AgentRegistry
    app=create_app(ROOT)
    with tempfile.TemporaryDirectory() as td:
        state=app.state.debate
        state.onboarding=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        state.registry=AgentRegistry(ROOT/"fixtures",state.onboarding.active_dir)
        state.engine.registry=state.registry
        c=TestClient(app)
        data=json.loads((ROOT/"fixtures"/"lee-aura-2019-agent.json").read_text())
        data["paper_id"]="api-invalid-test"
        data["source"]["source_id"]="s-api-invalid-test"
        data["source"]["sha256"]="4"*64
        for s in data["statements"]:
            if s.get("paper_id"): s["paper_id"]="api-invalid-test"
            if s.get("source_id"): s["source_id"]="s-api-invalid-test"
        claim=next(x for x in data["statements"] if x["statement_type"]=="AUTHOR_CLAIM")
        claim["review_status"]="NEEDS_REVIEW"
        up=c.post("/api/agents/onboarding/upload",json={"agent":data}).json()
        val=c.post(f"/api/agents/onboarding/{up['onboarding_id']}/validate")
        assert val.json()["validation"]["status"]=="FAIL"
        blocked=c.post(f"/api/agents/onboarding/{up['onboarding_id']}/register")
        assert blocked.status_code==400
        built=c.delete("/api/agents/benjamin-artwork-v2")
        assert built.status_code==400


def test_pdf_ingestion_api_pipeline():
    import tempfile, fitz
    from paper2humanities.ingestion import PdfIngestionService
    from paper2humanities.onboarding import OnboardingService
    from paper2humanities.debate import AgentRegistry
    class FakePdfGenerator:
        def generate(self,pages,metadata):
            p=pages[0]
            span=next(x.strip() for x in p["text"].splitlines() if x.strip().startswith("This paper argues"))
            return [{"statement_type":"AUTHOR_CLAIM","text":"The paper argues that mediated distance is transformed.","pdf_page":1,
                     "evidence_span":span,"evidence_voice":"AUTHOR","attributed_author":metadata.get("author"),"confidence":0.97}]
    app=create_app(ROOT)
    with tempfile.TemporaryDirectory() as td:
        state=app.state.debate
        state.onboarding=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        state.ingestion=PdfIngestionService(Path(td)/"store",state.onboarding,FakePdfGenerator())
        state.registry=AgentRegistry(ROOT/"fixtures",state.onboarding.active_dir)
        state.engine.registry=state.registry
        pdf=Path(td)/"api.pdf"
        doc=fitz.open(); pg=doc.new_page()
        text="API PDF Test\nAPI Scholar\nThis paper argues that mediated distance is transformed by digital systems while preserving source boundaries. Additional discussion provides enough content for page extraction quality and validation in this test document. The argument remains limited and does not claim empirical proof."
        pg.insert_textbox(fitz.Rect(60,60,535,780),text,fontsize=12,fontname="helv",lineheight=1.5)
        doc.set_metadata({"title":"API PDF Test","author":"API Scholar"}); doc.save(pdf); doc.close()
        c=TestClient(app)
        with pdf.open("rb") as fh:
            up=c.post("/api/agents/from-pdf/upload",files={"file":("api.pdf",fh,"application/pdf")})
        assert up.status_code==200
        jid=up.json()["job_id"]
        ext=c.post(f"/api/agents/from-pdf/{jid}/extract")
        assert ext.status_code==200 and ext.json()["extraction"]["quality"]=="PASS"
        meta=c.patch(f"/api/agents/from-pdf/{jid}/metadata",json={"metadata":{"paper_id":"api-pdf-agent","year":2026}})
        assert meta.status_code==200
        gen=c.post(f"/api/agents/from-pdf/{jid}/generate-candidates")
        assert gen.status_code==200 and len(gen.json()["candidates"])==1
        cid=gen.json()["candidates"][0]["candidate_id"]
        assert c.patch(f"/api/agents/from-pdf/{jid}/candidates/{cid}",json={"decision":"APPROVED"}).status_code==200
        built=c.post(f"/api/agents/from-pdf/{jid}/build-agent")
        assert built.status_code==200
        oid=built.json()["onboarding"]["onboarding_id"]
        reg=c.post(f"/api/agents/onboarding/{oid}/register")
        assert reg.status_code==200
        assert any(a["agent_id"]=="api-pdf-agent" for a in c.get("/api/debate/agents").json()["agents"])


def test_interrupted_session_can_resume():
    import tempfile, time
    from paper2humanities.api.store import SQLiteSessionStore
    app=create_app(ROOT)
    with tempfile.TemporaryDirectory() as td:
        state=app.state.debate
        state.sessions=SQLiteSessionStore(Path(td)/"resume.db")
        state.engine.adapter=FakeAdapter()
        c=TestClient(app)
        s=c.post("/api/debate/sessions",json={
            "agent_ids":["benjamin-artwork-v2","lee-aura-2019"],
            "topic":"resume test","max_turns":2}).json()
        sid=s["session_id"]
        live=state.sessions.get(sid); live.status="RUNNING"; state.sessions.put(live)
        state.sessions=SQLiteSessionStore(Path(td)/"resume.db")
        assert state.sessions.get(sid).status=="INTERRUPTED"
        r=c.post(f"/api/debate/sessions/{sid}/resume")
        assert r.status_code==200
        for _ in range(100):
            current=c.get(f"/api/debate/sessions/{sid}").json()
            if current["status"]=="COMPLETED": break
            time.sleep(.02)
        assert current["status"]=="COMPLETED" and len(current["turns"])==2
        events=state.sessions.events_after(sid)
        names=[e["event"] for e in events]
        assert "session_interrupted" in names and "session_resumed" in names


def test_basic_auth_when_configured():
    import os
    old_user=os.environ.get("P2H_AUTH_USER"); old_pass=os.environ.get("P2H_AUTH_PASSWORD")
    try:
        os.environ["P2H_AUTH_USER"]="owner"; os.environ["P2H_AUTH_PASSWORD"]="secret-test"
        app=create_app(ROOT)
        c=TestClient(app)
        assert c.get("/healthz").status_code==200
        assert c.get("/debate").status_code==401
        assert c.get("/debate",auth=("owner","wrong")).status_code==401
        assert c.get("/debate",auth=("owner","secret-test")).status_code==200
    finally:
        if old_user is None: os.environ.pop("P2H_AUTH_USER",None)
        else: os.environ["P2H_AUTH_USER"]=old_user
        if old_pass is None: os.environ.pop("P2H_AUTH_PASSWORD",None)
        else: os.environ["P2H_AUTH_PASSWORD"]=old_pass


def test_concurrent_sessions_are_isolated():
    import tempfile, time
    from paper2humanities.api.store import SQLiteSessionStore
    app=create_app(ROOT)
    with tempfile.TemporaryDirectory() as td:
        state=app.state.debate
        state.sessions=SQLiteSessionStore(Path(td)/"concurrent.db")
        state.engine.adapter=FakeAdapter()
        c=TestClient(app)
        s1=c.post("/api/debate/sessions",json={"agent_ids":["benjamin-artwork-v2","lee-aura-2019"],"topic":"session one","max_turns":3}).json()
        s2=c.post("/api/debate/sessions",json={"agent_ids":["lee-aura-2019","benjamin-artwork-v3"],"topic":"session two","max_turns":3}).json()
        assert c.post(f"/api/debate/sessions/{s1['session_id']}/start").status_code==200
        assert c.post(f"/api/debate/sessions/{s2['session_id']}/start").status_code==200
        for _ in range(100):
            a=c.get(f"/api/debate/sessions/{s1['session_id']}").json()
            b=c.get(f"/api/debate/sessions/{s2['session_id']}").json()
            if a["status"]=="COMPLETED" and b["status"]=="COMPLETED": break
            time.sleep(.02)
        assert a["status"]=="COMPLETED" and b["status"]=="COMPLETED"
        assert len(a["turns"])==3 and len(b["turns"])==3
        assert a["topic"]=="session one" and b["topic"]=="session two"
        assert a["participant_ids"]!=b["participant_ids"]
        ea=state.sessions.events_after(s1["session_id"])
        eb=state.sessions.events_after(s2["session_id"])
        assert all(e["data"].get("session_id",s1["session_id"])!=s2["session_id"] for e in ea)
        assert all(e["data"].get("session_id",s2["session_id"])!=s1["session_id"] for e in eb)


def test_sse_last_event_id_resumes_without_replay():
    import tempfile
    from paper2humanities.api.store import SQLiteSessionStore
    app=create_app(ROOT)
    with tempfile.TemporaryDirectory() as td:
        state=app.state.debate
        state.sessions=SQLiteSessionStore(Path(td)/"sse.db")
        state.engine.adapter=FakeAdapter()
        c=TestClient(app)
        s=c.post("/api/debate/sessions",json={"agent_ids":["benjamin-artwork-v2","lee-aura-2019"],"topic":"sse","max_turns":1}).json()
        sid=s["session_id"]
        c.post(f"/api/debate/sessions/{sid}/next")
        events=state.sessions.events_after(sid)
        first_id=events[0]["id"]
        with c.stream("GET",f"/api/debate/sessions/{sid}/stream",headers={"Last-Event-ID":str(first_id)}) as resp:
            text="".join(resp.iter_text())
        assert f"id: {first_id}\n" not in text
        assert "event: turn_completed" in text
