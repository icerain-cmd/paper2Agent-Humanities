from __future__ import annotations
import json, shutil, threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..debate import AgentRegistry, DebateEngine
from ..runtime.model_adapter import CodexExecAdapter
from .store import SessionStore

class CreateSessionRequest(BaseModel):
    agent_ids:list[str]=Field(min_length=2,max_length=3)
    topic:str=Field(min_length=1)
    max_turns:int=Field(default=8,ge=1,le=20)

class InterventionRequest(BaseModel):
    text:str=Field(min_length=1)

class AppState:
    def __init__(self, root:Path, model:str="gpt-6-sol"):
        self.root=root
        self.registry=AgentRegistry(root/"fixtures")
        codex=shutil.which("codex") or str(Path.home()/".local/bin/codex")
        self.engine=DebateEngine(self.registry,CodexExecAdapter(model=model,executable=codex))
        self.sessions=SessionStore()
        self.events:dict[str,list[dict]]={}
        self.event_locks:dict[str,LockProxy]={}
        self.runners:set[str]=set()

class LockProxy:
    def __init__(self):
        self.lock=threading.Lock()

def create_app(root:Path|None=None, model:str="gpt-6-sol"):
    root=root or Path(__file__).resolve().parents[3]
    state=AppState(root,model)
    app=FastAPI(title="Paper2Agent-Humanities Debate API",version="0.1.0")
    app.state.debate=state
    web_dir=root/"web"
    app.mount("/debate-static",StaticFiles(directory=web_dir),name="debate-static")

    @app.get("/debate",include_in_schema=False)
    def debate_ui():
        return FileResponse(web_dir/"index.html")

    def append_event(session_id,event_type,data):
        lock=state.event_locks.setdefault(session_id,LockProxy()).lock
        with lock:
            state.events.setdefault(session_id,[]).append({"event":event_type,"data":data})

    def get_session(session_id):
        try: return state.sessions.get(session_id)
        except KeyError: raise HTTPException(status_code=404,detail="session not found")

    @app.get("/api/debate/agents")
    def agents():
        state.registry.reload()
        return {"agents":state.registry.describe(),"registry":state.registry.diagnostics()}

    @app.post("/api/debate/agents/reload")
    def reload_agents():
        state.registry.reload()
        return {"agents":state.registry.describe(),"registry":state.registry.diagnostics()}

    @app.post("/api/debate/sessions")
    def create_session(req:CreateSessionRequest):
        try:
            session=state.engine.create_session(req.agent_ids,req.topic,req.max_turns)
        except (ValueError,KeyError) as exc:
            raise HTTPException(status_code=400,detail=str(exc))
        state.sessions.put(session)
        state.events[session.session_id]=[]
        return session.to_dict()

    @app.get("/api/debate/sessions/{session_id}")
    def session_state(session_id:str):
        return get_session(session_id).to_dict()

    @app.post("/api/debate/sessions/{session_id}/intervene")
    def intervene(session_id:str,req:InterventionRequest):
        session=get_session(session_id)
        state.engine.intervene(session,req.text)
        append_event(session_id,"user_intervention",{"text":req.text,"at_turn":session.current_turn})
        return session.to_dict()

    def run_background(session_id:str):
        session=get_session(session_id)
        try:
            while session.status!="COMPLETED":
                speaker,targets,action=state.engine.orchestrator.next_assignment(session)
                append_event(session_id,"agent_thinking",{"speaker_agent_id":speaker,"action":action.value,"target_agent_ids":targets})
                result=state.engine.step(session)
                if result is None: break
                turn,trace=result
                append_event(session_id,"evidence_retrieved",{
                    "speaker_agent_id":turn.speaker_agent_id,
                    "statement_ids":trace.get("selected_statement_ids",[]),
                    "grounding_retry_count":trace.get("grounding_retry_count",0)})
                append_event(session_id,"turn_completed",turn.to_dict())
            append_event(session_id,"debate_completed",session.to_dict())
        except Exception as exc:
            session.status="FAILED"
            append_event(session_id,"debate_failed",{"error":f"{type(exc).__name__}: {exc}"})
        finally:
            state.runners.discard(session_id)

    @app.post("/api/debate/sessions/{session_id}/start")
    def start(session_id:str):
        session=get_session(session_id)
        if session.status=="COMPLETED":
            return session.to_dict()
        if session_id not in state.runners:
            state.runners.add(session_id)
            threading.Thread(target=run_background,args=(session_id,),daemon=True).start()
        return {"session_id":session_id,"status":"RUNNING"}

    @app.post("/api/debate/sessions/{session_id}/next")
    def next_turn(session_id:str):
        session=get_session(session_id)
        if session_id in state.runners:
            raise HTTPException(status_code=409,detail="session is already running")
        result=state.engine.step(session)
        if result is None:
            return {"session":session.to_dict(),"turn":None}
        turn,trace=result
        append_event(session_id,"turn_completed",turn.to_dict())
        return {"session":session.to_dict(),"turn":turn.to_dict(),"trace":trace}

    @app.get("/api/debate/sessions/{session_id}/stream")
    def stream(session_id:str):
        get_session(session_id)
        def generate():
            index=0
            while True:
                lock=state.event_locks.setdefault(session_id,LockProxy()).lock
                with lock:
                    events=list(state.events.get(session_id,[]))
                while index<len(events):
                    ev=events[index]; index+=1
                    yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'],ensure_ascii=False)}\n\n"
                session=get_session(session_id)
                if session.status in {"COMPLETED","FAILED"} and index>=len(events):
                    break
                import time; time.sleep(0.15)
        return StreamingResponse(generate(),media_type="text/event-stream")

    return app
