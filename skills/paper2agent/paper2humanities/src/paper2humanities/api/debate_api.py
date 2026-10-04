from __future__ import annotations
import base64, hmac, json, os, shutil, threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..debate import AgentRegistry, DebateEngine, DebateSession
from ..runtime.model_adapter import CodexExecAdapter
from ..onboarding import OnboardingService
from ..ingestion import PdfIngestionService, CodexCandidateGenerator
from .store import SessionStore

class CreateSessionRequest(BaseModel):
    agent_ids:list[str]=Field(min_length=2,max_length=3)
    topic:str=Field(min_length=1)
    max_turns:int=Field(default=8,ge=1,le=20)

class InterventionRequest(BaseModel):
    text:str=Field(min_length=1)

class UploadAgentRequest(BaseModel):
    agent:dict
    original_name:str|None=None

class MetadataPatchRequest(BaseModel):
    metadata:dict

class CandidatePatchRequest(BaseModel):
    decision:str|None=None
    text:str|None=None
    attributed_author:str|None=None

class AppState:
    def __init__(self, root:Path, model:str="gpt-6-sol"):
        self.root=root
        data_dir=Path(os.getenv("P2H_DATA_DIR",str(root/"agent_store"))).expanduser()
        self.data_dir=data_dir
        self.onboarding=OnboardingService(data_dir,root/"fixtures")
        codex=shutil.which("codex") or str(Path.home()/".local/bin/codex")
        self.ingestion=PdfIngestionService(data_dir,self.onboarding,CodexCandidateGenerator(model=model,executable=codex))
        self.registry=AgentRegistry(root/"fixtures",self.onboarding.active_dir)
        self.engine=DebateEngine(self.registry,CodexExecAdapter(model=model,executable=codex))
        self.sessions=SessionStore(data_dir/"paper2humanities.db")
        self.runners:set[str]=set()
        self.runner_lock=threading.Lock()
        self.session_locks:dict[str,LockProxy]={}

class LockProxy:
    def __init__(self):
        self.lock=threading.Lock()

def create_app(root:Path|None=None, model:str="gpt-6-sol"):
    root=root or Path(__file__).resolve().parents[3]
    state=AppState(root,model)
    app=FastAPI(title="Paper2Agent-Humanities Debate API",version="0.2.0")
    app.state.debate=state
    auth_user=os.getenv("P2H_AUTH_USER")
    auth_password=os.getenv("P2H_AUTH_PASSWORD")

    @app.middleware("http")
    async def owner_auth(request:Request,call_next):
        if not auth_user or not auth_password or request.url.path=="/healthz":
            return await call_next(request)
        header=request.headers.get("authorization","")
        ok=False
        if header.lower().startswith("basic "):
            try:
                decoded=base64.b64decode(header.split(" ",1)[1]).decode("utf-8")
                user,password=decoded.split(":",1)
                ok=hmac.compare_digest(user,auth_user) and hmac.compare_digest(password,auth_password)
            except Exception:
                ok=False
        if not ok:
            return PlainTextResponse("Authentication required",status_code=401,headers={"WWW-Authenticate":"Basic realm=\"Paper2Agent Humanities\""})
        return await call_next(request)

    web_dir=root/"web"
    app.mount("/debate-static",StaticFiles(directory=web_dir),name="debate-static")

    @app.get("/debate",include_in_schema=False)
    def debate_ui():
        return FileResponse(web_dir/"index.html")

    @app.get("/healthz")
    def healthz():
        state.registry.reload()
        return {
            "status":"ok",
            "registry_agents":len(state.registry.ids()),
            "registry_rejected":len(state.registry.diagnostics().get("rejected",[])),
            "database":"ok",
            "session_counts":state.sessions.counts(),
            "model_runtime":"available" if state.engine.adapter.available() else "unavailable",
            "active_sessions":len(state.runners),
        }

    def append_event(session_id,event_type,data):
        return state.sessions.append_event(session_id,event_type,data)

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

    @app.post("/api/agents/onboarding/upload")
    def onboarding_upload(req:UploadAgentRequest):
        try:
            return state.onboarding.upload_json(req.agent,req.original_name)
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.post("/api/agents/onboarding/{onboarding_id}/validate")
    def onboarding_validate(onboarding_id:str):
        try:
            return state.onboarding.validate(onboarding_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="onboarding record not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.get("/api/agents/onboarding/{onboarding_id}")
    def onboarding_state(onboarding_id:str):
        try:
            return state.onboarding.get(onboarding_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="onboarding record not found")

    @app.post("/api/agents/onboarding/{onboarding_id}/register")
    def onboarding_register(onboarding_id:str):
        try:
            result=state.onboarding.register(onboarding_id)
            state.registry.reload()
            return result
        except KeyError:
            raise HTTPException(status_code=404,detail="onboarding record not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.delete("/api/agents/{agent_id}")
    def disable_registered_agent(agent_id:str):
        try:
            result=state.onboarding.disable(agent_id)
            state.registry.reload()
            return result
        except KeyError:
            raise HTTPException(status_code=404,detail="registered agent not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.post("/api/agents/from-pdf/upload")
    async def pdf_upload(file:UploadFile=File(...)):
        try:
            data=await file.read()
            return state.ingestion.upload_pdf(data,file.filename or "paper.pdf")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.post("/api/agents/from-pdf/{job_id}/extract")
    def pdf_extract(job_id:str):
        try:
            return state.ingestion.extract(job_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.get("/api/agents/from-pdf/{job_id}")
    def pdf_job(job_id:str):
        try:
            return state.ingestion.get(job_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job not found")

    @app.patch("/api/agents/from-pdf/{job_id}/metadata")
    def pdf_metadata(job_id:str,req:MetadataPatchRequest):
        try:
            return state.ingestion.update_metadata(job_id,req.metadata)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.post("/api/agents/from-pdf/{job_id}/generate-candidates")
    def pdf_generate_candidates(job_id:str):
        try:
            return state.ingestion.generate_candidates(job_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job not found")
        except (ValueError,RuntimeError) as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.patch("/api/agents/from-pdf/{job_id}/candidates/{candidate_id}")
    def pdf_update_candidate(job_id:str,candidate_id:str,req:CandidatePatchRequest):
        try:
            patch={k:v for k,v in req.model_dump().items() if v is not None}
            return state.ingestion.update_candidate(job_id,candidate_id,patch)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job or candidate not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.post("/api/agents/from-pdf/{job_id}/approve-high-confidence")
    def pdf_approve_high(job_id:str):
        try:
            return state.ingestion.approve_high_confidence_author_claims(job_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job not found")

    @app.post("/api/agents/from-pdf/{job_id}/build-agent")
    def pdf_build_agent(job_id:str):
        try:
            return state.ingestion.build_agent(job_id)
        except KeyError:
            raise HTTPException(status_code=404,detail="pdf job not found")
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))

    @app.post("/api/debate/sessions")
    def create_session(req:CreateSessionRequest):
        try:
            session=state.engine.create_session(req.agent_ids,req.topic,req.max_turns)
        except (ValueError,KeyError) as exc:
            raise HTTPException(status_code=400,detail=str(exc))
        state.sessions.put(session)
        append_event(session.session_id,"session_created",session.to_dict())
        return session.to_dict()

    @app.get("/api/debate/sessions")
    def list_sessions(limit:int=50):
        return {"sessions":[s.to_dict() for s in state.sessions.list(max(1,min(limit,200)))]}

    @app.get("/api/debate/sessions/{session_id}")
    def session_state(session_id:str):
        return get_session(session_id).to_dict()

    @app.post("/api/debate/sessions/{session_id}/intervene")
    def intervene(session_id:str,req:InterventionRequest):
        lock=state.session_locks.setdefault(session_id,LockProxy()).lock
        with lock:
            session=get_session(session_id)
            if session.status in {"COMPLETED","FAILED"}:
                raise HTTPException(status_code=409,detail="session is not active")
            state.engine.intervene(session,req.text)
            state.sessions.put(session)
            append_event(session_id,"user_intervention",{"text":req.text,"at_turn":session.current_turn})
            return session.to_dict()

    def persist_generated_turn(session_id,generated_session,turn,trace):
        lock=state.session_locks.setdefault(session_id,LockProxy()).lock
        with lock:
            latest=get_session(session_id)
            if latest.current_turn!=generated_session.current_turn-1:
                raise RuntimeError("session turn advanced concurrently")
            latest.turns=list(generated_session.turns)
            latest.current_turn=generated_session.current_turn
            latest.status=generated_session.status
            state.sessions.put(latest)
            append_event(session_id,"evidence_retrieved",{
                "speaker_agent_id":turn.speaker_agent_id,
                "statement_ids":trace.get("selected_statement_ids",[]),
                "grounding_retry_count":trace.get("grounding_retry_count",0)})
            append_event(session_id,"turn_completed",turn.to_dict())
            return latest

    def run_background(session_id:str):
        try:
            while True:
                session=get_session(session_id)
                if session.status=="COMPLETED":
                    append_event(session_id,"debate_completed",session.to_dict())
                    break
                if session.status not in {"RUNNING","INTERRUPTED","READY"}:
                    break
                session.status="RUNNING"
                state.sessions.put(session)
                speaker,targets,action=state.engine.orchestrator.next_assignment(session)
                append_event(session_id,"agent_thinking",{"speaker_agent_id":speaker,"action":action.value,"target_agent_ids":targets})
                generated=DebateSession.from_dict(session.to_dict())
                result=state.engine.step(generated)
                if result is None:
                    generated.status="COMPLETED"
                    state.sessions.put(generated)
                    append_event(session_id,"debate_completed",generated.to_dict())
                    break
                turn,trace=result
                latest=persist_generated_turn(session_id,generated,turn,trace)
                if latest.current_turn>=latest.max_turns:
                    latest.status="COMPLETED"
                    state.sessions.put(latest)
                    append_event(session_id,"debate_completed",latest.to_dict())
                    break
        except Exception as exc:
            try:
                session=get_session(session_id)
                session.status="FAILED"
                state.sessions.put(session)
            except Exception:
                pass
            append_event(session_id,"debate_failed",{"error":f"{type(exc).__name__}: {exc}"})
        finally:
            with state.runner_lock:
                state.runners.discard(session_id)

    def launch_session(session_id:str):
        session=get_session(session_id)
        if session.status=="COMPLETED":
            return session.to_dict()
        if session.status=="FAILED":
            raise HTTPException(status_code=409,detail="failed session cannot be resumed")
        previous_status=session.status
        with state.runner_lock:
            if session_id in state.runners:
                return {"session_id":session_id,"status":"RUNNING"}
            state.runners.add(session_id)
        session.status="RUNNING"
        state.sessions.put(session)
        event_type="session_resumed" if previous_status=="INTERRUPTED" else "session_started"
        append_event(session_id,event_type,{"current_turn":session.current_turn})
        threading.Thread(target=run_background,args=(session_id,),daemon=True).start()
        return {"session_id":session_id,"status":"RUNNING","current_turn":session.current_turn}

    @app.post("/api/debate/sessions/{session_id}/start")
    def start(session_id:str):
        return launch_session(session_id)

    @app.post("/api/debate/sessions/{session_id}/resume")
    def resume(session_id:str):
        session=get_session(session_id)
        if session.status!="INTERRUPTED":
            raise HTTPException(status_code=409,detail="only INTERRUPTED sessions can be resumed")
        return launch_session(session_id)

    @app.post("/api/debate/sessions/{session_id}/next")
    def next_turn(session_id:str):
        with state.runner_lock:
            if session_id in state.runners:
                raise HTTPException(status_code=409,detail="session is already running")
        session=get_session(session_id)
        generated=DebateSession.from_dict(session.to_dict())
        result=state.engine.step(generated)
        if result is None:
            generated.status="COMPLETED"; state.sessions.put(generated)
            return {"session":generated.to_dict(),"turn":None}
        turn,trace=result
        latest=persist_generated_turn(session_id,generated,turn,trace)
        return {"session":latest.to_dict(),"turn":turn.to_dict(),"trace":trace}

    @app.get("/api/debate/sessions/{session_id}/stream")
    def stream(session_id:str,request:Request):
        get_session(session_id)
        def generate():
            try:
                after_id=max(0,int(request.headers.get("last-event-id","0") or 0))
            except ValueError:
                after_id=0
            import time
            while True:
                events=state.sessions.events_after(session_id,after_id)
                for ev in events:
                    after_id=ev["id"]
                    yield f"id: {after_id}\nevent: {ev['event']}\ndata: {json.dumps(ev['data'],ensure_ascii=False)}\n\n"
                session=get_session(session_id)
                if session.status in {"COMPLETED","FAILED"} and not state.sessions.events_after(session_id,after_id):
                    break
                time.sleep(0.15)
        return StreamingResponse(generate(),media_type="text/event-stream")

    return app
