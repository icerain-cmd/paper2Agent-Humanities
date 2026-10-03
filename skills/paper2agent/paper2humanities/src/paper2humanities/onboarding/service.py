from __future__ import annotations
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, uuid

from ..paper_agent import PaperAgent
from ..schema import ReviewStatus, StatementType, EvidenceVoice

MAX_UPLOAD_BYTES=10*1024*1024
AGENT_ID_RE=re.compile(r"^[A-Za-z0-9._-]{3,160}$")

class OnboardingStatus(str, Enum):
    UPLOADED="UPLOADED"
    VALIDATED="VALIDATED"
    READY_FOR_REVIEW="READY_FOR_REVIEW"
    ACTIVE="ACTIVE"
    REJECTED="REJECTED"
    DISABLED="DISABLED"

class OnboardingService:
    def __init__(self, root: str|Path, built_in_dir: str|Path):
        self.root=Path(root)
        self.built_in_dir=Path(built_in_dir)
        self.staging_dir=self.root/"staging"
        self.active_dir=self.root/"active"
        self.disabled_dir=self.root/"disabled"
        for p in (self.staging_dir,self.active_dir,self.disabled_dir):
            p.mkdir(parents=True,exist_ok=True)

    def _sha(self,b:bytes)->str:
        return hashlib.sha256(b).hexdigest()

    def _now(self)->str:
        return datetime.now(timezone.utc).isoformat()

    def _safe_id(self)->str:
        return f"onb-{uuid.uuid4().hex}"

    def _record_dir(self,onboarding_id:str)->Path:
        if not AGENT_ID_RE.fullmatch(onboarding_id):
            raise ValueError("invalid onboarding id")
        return self.staging_dir/onboarding_id

    def _manifest_path(self,onboarding_id:str)->Path:
        return self._record_dir(onboarding_id)/"manifest.json"

    def _agent_path(self,onboarding_id:str)->Path:
        return self._record_dir(onboarding_id)/"agent.json"

    def _read_manifest(self,onboarding_id:str)->dict:
        p=self._manifest_path(onboarding_id)
        if not p.is_file():
            raise KeyError(onboarding_id)
        return json.loads(p.read_text(encoding="utf-8"))

    def _write_manifest(self,onboarding_id:str,data:dict)->None:
        p=self._manifest_path(onboarding_id)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    def upload_json(self,agent_data:dict,original_name:str|None=None)->dict:
        raw=json.dumps(agent_data,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        if len(raw)>MAX_UPLOAD_BYTES:
            raise ValueError("agent JSON exceeds 10MB limit")
        oid=self._safe_id()
        d=self._record_dir(oid); d.mkdir(parents=True,exist_ok=False)
        pretty=json.dumps(agent_data,ensure_ascii=False,indent=2).encode("utf-8")+b"\n"
        (d/"agent.json").write_bytes(pretty)
        manifest={
            "onboarding_id":oid,
            "status":OnboardingStatus.UPLOADED.value,
            "created_at":self._now(),
            "updated_at":self._now(),
            "original_name":Path(original_name or "agent.json").name,
            "agent_sha256":self._sha(pretty),
            "validation":None,
            "registered_agent_id":None,
        }
        self._write_manifest(oid,manifest)
        return self.get(oid)

    def _built_in_ids(self)->set[str]:
        ids=set()
        for p in self.built_in_dir.glob("*-agent.json"):
            if p.name.endswith("-phase2-agent.json"):
                continue
            try:
                ids.add(json.loads(p.read_text(encoding="utf-8"))["paper_id"])
            except Exception:
                continue
        return ids

    def _active_ids(self)->set[str]:
        ids=set()
        for p in self.active_dir.glob("*/agent.json"):
            try:
                ids.add(json.loads(p.read_text(encoding="utf-8"))["paper_id"])
            except Exception:
                continue
        return ids

    def validate(self,onboarding_id:str)->dict:
        manifest=self._read_manifest(onboarding_id)
        errors=[]; warnings=[]
        agent_data=None; agent=None
        try:
            agent_data=json.loads(self._agent_path(onboarding_id).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"INVALID_JSON: {type(exc).__name__}: {exc}")
        if isinstance(agent_data,dict):
            paper_id=agent_data.get("paper_id")
            title=agent_data.get("title")
            author=agent_data.get("author")
            source=agent_data.get("source") or {}
            if not isinstance(paper_id,str) or not AGENT_ID_RE.fullmatch(paper_id):
                errors.append("INVALID_PAPER_ID")
            if not isinstance(title,str) or not title.strip():
                errors.append("MISSING_TITLE")
            if not isinstance(author,str) or not author.strip():
                errors.append("MISSING_AUTHOR")
            if not isinstance(source.get("source_id"),str) or not source.get("source_id"):
                errors.append("MISSING_SOURCE_ID")
            sha=source.get("sha256")
            if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-fA-F]{64}",sha):
                errors.append("INVALID_SOURCE_SHA256")
            if isinstance(paper_id,str) and paper_id in (self._built_in_ids()|self._active_ids()):
                errors.append("DUPLICATE_PAPER_ID")
            for item in agent_data.get("statements") or []:
                sid=item.get("statement_id","<unknown>")
                st=item.get("statement_type")
                if st in {"SOURCE_QUOTE","AUTHOR_CLAIM"}:
                    if item.get("review_status")!="REVIEWED":
                        errors.append(f"UNREVIEWED_GROUNDED:{sid}")
                    if not isinstance(item.get("page"),int) or item.get("page",0)<1:
                        errors.append(f"MISSING_PAGE:{sid}")
                    if not item.get("evidence_span"):
                        errors.append(f"MISSING_EVIDENCE_SPAN:{sid}")
                    if st=="AUTHOR_CLAIM" and item.get("evidence_voice")=="EXTERNAL":
                        errors.append(f"EXTERNAL_AS_AUTHOR:{sid}")
            try:
                agent=PaperAgent.from_json(self._agent_path(onboarding_id))
            except Exception as exc:
                errors.append(f"PAPER_AGENT_INVALID: {type(exc).__name__}: {exc}")
        if agent is not None:
            grounded=[]
            for s in agent.store.values():
                if s.statement_type not in {StatementType.SOURCE_QUOTE,StatementType.AUTHOR_CLAIM}:
                    continue
                grounded.append(s)
                if s.review_status!=ReviewStatus.REVIEWED:
                    errors.append(f"UNREVIEWED_GROUNDED:{s.statement_id}")
                if not s.page or s.page<1:
                    errors.append(f"MISSING_PAGE:{s.statement_id}")
                if not s.evidence_span:
                    errors.append(f"MISSING_EVIDENCE_SPAN:{s.statement_id}")
                if s.paper_id!=agent.paper_id or s.source_id!=agent.source_id:
                    errors.append(f"SOURCE_BOUNDARY:{s.statement_id}")
                if s.edition_id!=agent.edition_id:
                    errors.append(f"EDITION_MISMATCH:{s.statement_id}")
                if s.statement_type==StatementType.AUTHOR_CLAIM and s.evidence_voice==EvidenceVoice.EXTERNAL:
                    errors.append(f"EXTERNAL_AS_AUTHOR:{s.statement_id}")
            if not grounded:
                errors.append("NO_GROUNDED_STATEMENTS")
            if any(s.review_status!=ReviewStatus.REVIEWED for s in agent.store.values()
                   if s.statement_type not in {StatementType.SOURCE_QUOTE,StatementType.AUTHOR_CLAIM}):
                warnings.append("NON_GROUNDED_ITEMS_NEED_REVIEW")
        errors=sorted(set(errors)); warnings=sorted(set(warnings))
        counts={}
        if agent is not None:
            vals=list(agent.store.values())
            grounded=[s for s in vals if s.statement_type in {StatementType.SOURCE_QUOTE,StatementType.AUTHOR_CLAIM}]
            counts={
                "statements":len(vals),
                "grounded":len(grounded),
                "reviewed_grounded":sum(s.review_status==ReviewStatus.REVIEWED for s in grounded),
                "quotes":sum(s.statement_type==StatementType.SOURCE_QUOTE for s in grounded),
                "author_claims":sum(s.statement_type==StatementType.AUTHOR_CLAIM for s in grounded),
                "external_voice":sum(s.evidence_voice==EvidenceVoice.EXTERNAL for s in grounded),
            }
        result={
            "status":"PASS" if not errors else "FAIL",
            "errors":errors,
            "warnings":warnings,
            "counts":counts,
            "preview":None if agent is None else {
                "agent_id":agent.paper_id,
                "author":agent.author,
                "title":agent.title,
                "edition_id":agent.edition_id,
                "source_id":agent.source_id,
                "concepts":list(agent.concepts),
                "sample_statements":[
                    {
                        "statement_id":s.statement_id,
                        "statement_type":s.statement_type.value,
                        "page":s.page,
                        "text":s.text,
                        "evidence_voice":s.evidence_voice.value if s.evidence_voice else None,
                    } for s in list(agent.store.values())[:6]
                ],
            }
        }
        manifest["validation"]=result
        manifest["status"]=OnboardingStatus.READY_FOR_REVIEW.value if not errors else OnboardingStatus.REJECTED.value
        manifest["updated_at"]=self._now()
        self._write_manifest(onboarding_id,manifest)
        return self.get(onboarding_id)

    def register(self,onboarding_id:str)->dict:
        manifest=self._read_manifest(onboarding_id)
        if manifest.get("status")!=OnboardingStatus.READY_FOR_REVIEW.value:
            raise ValueError("agent is not READY_FOR_REVIEW")
        validation=manifest.get("validation") or {}
        if validation.get("status")!="PASS":
            raise ValueError("validation has not passed")
        agent_data=json.loads(self._agent_path(onboarding_id).read_text(encoding="utf-8"))
        agent_id=agent_data["paper_id"]
        if agent_id in (self._built_in_ids()|self._active_ids()):
            raise ValueError("duplicate paper_id")
        target=self.active_dir/agent_id
        target.mkdir(parents=True,exist_ok=False)
        agent_bytes=self._agent_path(onboarding_id).read_bytes()
        (target/"agent.json").write_bytes(agent_bytes)
        active_manifest={
            "agent_id":agent_id,
            "registered_at":self._now(),
            "agent_sha256":self._sha(agent_bytes),
            "source_sha256":agent_data["source"]["sha256"],
            "source_id":agent_data["source"]["source_id"],
            "edition_id":agent_data.get("source",{}).get("edition_id") or agent_data.get("edition_id"),
            "validation_status":"PASS",
            "reviewed_grounded_count":validation.get("counts",{}).get("reviewed_grounded",0),
            "source_file":manifest.get("original_name"),
            "status":OnboardingStatus.ACTIVE.value,
        }
        (target/"manifest.json").write_text(json.dumps(active_manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        manifest["status"]=OnboardingStatus.ACTIVE.value
        manifest["registered_agent_id"]=agent_id
        manifest["updated_at"]=self._now()
        self._write_manifest(onboarding_id,manifest)
        return {"onboarding":self.get(onboarding_id),"active_manifest":active_manifest}

    def disable(self,agent_id:str)->dict:
        if not AGENT_ID_RE.fullmatch(agent_id):
            raise ValueError("invalid agent id")
        if agent_id in self._built_in_ids():
            raise ValueError("built-in agents cannot be disabled")
        src=self.active_dir/agent_id
        if not src.is_dir():
            raise KeyError(agent_id)
        dst=self.disabled_dir/agent_id
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src),str(dst))
        mp=dst/"manifest.json"
        data=json.loads(mp.read_text(encoding="utf-8"))
        data["status"]=OnboardingStatus.DISABLED.value
        data["disabled_at"]=self._now()
        mp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return data

    def get(self,onboarding_id:str)->dict:
        return self._read_manifest(onboarding_id)
