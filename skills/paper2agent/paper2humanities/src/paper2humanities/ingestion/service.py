from __future__ import annotations
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, uuid, threading, time
from typing import Any

from pypdf import PdfReader

MAX_PDF_BYTES=25*1024*1024
JOB_ID_RE=re.compile(r"^pdfjob-[0-9a-f]{32}$")
CANDIDATE_TYPES={"AUTHOR_CLAIM","SOURCE_QUOTE","EXTERNAL_QUOTE"}
CANDIDATE_DECISIONS={"PENDING","APPROVED","REJECTED"}

def infer_pdf_metadata(pdf_title, pdf_author, first_text):
    # DOI transport metadata may be glued to the visible heading, including
    # invisible HWP characters. Remove only the identifier, retaining its suffix.
    clean=lambda text: re.sub(r"[\u200b-\u200d\ufeff]", "", text or "").strip()
    doi_re=re.compile(r"10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+",re.I)
    title=clean(pdf_title)
    lines=[clean(line) for line in first_text.splitlines() if clean(line)][:20]
    doi_match=doi_re.search(clean(pdf_title)+"\n"+clean(first_text[:2000]))
    doi=doi_match.group(0).rstrip(".,;") if doi_match else None
    identifier=re.compile(r"^(?:https?://|doi\s*:|10\.\d{4,9}/)",re.I)
    if not title or identifier.match(title):
        for line in [title]+lines:
            if identifier.match(line):
                match=doi_re.search(line)
                line=line[match.end():].strip() if match else ""
            if line:
                title=re.sub(r"\*+\s*\d*\)?\s*$", "", line).strip()
                break
        else:
            title=""
    author=clean(pdf_author)
    # A Korean scholarly byline with affiliation is stronger evidence than the
    # PDF software's creator/author field; do not infer from body citations.
    byline=re.search(r"(?:^|\n|[-–—]\s*)([가-힣]{2,5})\s*\(([^)\n]{1,60})\)",clean(first_text[:1200]))
    if byline and any(word in byline.group(2) for word in ("대학","대학교","전주대","연구소")):
        author=byline.group(1)
    if not author and len(lines)>1:
        candidates=[line for line in lines[1:8] if line!=title and len(line)<=200]
        if candidates: author=candidates[0]
    return title[:300],author,doi

class PdfJobStatus(str, Enum):
    PDF_UPLOADED="PDF_UPLOADED"
    EXTRACTED="EXTRACTED"
    EXTRACTION_REJECTED="EXTRACTION_REJECTED"
    GENERATED="GENERATED"
    READY_FOR_BUILD="READY_FOR_BUILD"
    BUILT="BUILT"

class PdfIngestionService:
    def __init__(self, root: str|Path, onboarding_service, candidate_generator=None):
        self.root=Path(root)
        self.onboarding=onboarding_service
        self.candidate_generator=candidate_generator
        self._generation_lock=threading.Lock()
        self._generating=set()
        self.jobs_dir=self.root/"pdf_jobs"
        self.sources_dir=self.root/"sources"
        self.jobs_dir.mkdir(parents=True,exist_ok=True)
        self.sources_dir.mkdir(parents=True,exist_ok=True)
        # Background threads cannot survive a backend restart. Surface a retryable
        # failure instead of leaving an on-disk job permanently RUNNING.
        for path in self.jobs_dir.glob("pdfjob-*/manifest.json"):
            if not JOB_ID_RE.fullmatch(path.parent.name): continue
            try: manifest=self._read(path)
            except (OSError,json.JSONDecodeError): continue
            if (manifest.get("generation") or {}).get("status")=="RUNNING":
                manifest["generation"].update(status="FAILED",active_batches=0,
                                             error="candidate generation interrupted by backend restart; retry generation")
                self._save_manifest(path.parent.name,manifest)

    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _sha(self,b:bytes): return hashlib.sha256(b).hexdigest()
    def _job_dir(self,job_id:str)->Path:
        if not JOB_ID_RE.fullmatch(job_id): raise ValueError("invalid pdf job id")
        return self.jobs_dir/job_id
    def _manifest_path(self,job_id:str): return self._job_dir(job_id)/"manifest.json"
    def _pages_path(self,job_id:str): return self._job_dir(job_id)/"pages.json"
    def _candidates_path(self,job_id:str): return self._job_dir(job_id)/"candidates.json"
    def _read(self,p:Path): return json.loads(p.read_text(encoding="utf-8"))
    def _write(self,p:Path,data:Any):
        p.parent.mkdir(parents=True,exist_ok=True)
        temporary=p.with_name(p.name+"."+uuid.uuid4().hex+".tmp")
        try:
            temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            temporary.replace(p)
        finally:
            temporary.unlink(missing_ok=True)
    def _manifest(self,job_id:str):
        p=self._manifest_path(job_id)
        if not p.is_file(): raise KeyError(job_id)
        return self._read(p)
    def _save_manifest(self,job_id:str,m:dict):
        m["updated_at"]=self._now(); self._write(self._manifest_path(job_id),m)

    def upload_pdf(self,pdf_bytes:bytes,original_name:str)->dict:
        if not pdf_bytes or len(pdf_bytes)>MAX_PDF_BYTES:
            raise ValueError("PDF must be between 1 byte and 25MB")
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("file is not a PDF")
        sha=self._sha(pdf_bytes)
        source_dir=self.sources_dir/sha
        source_dir.mkdir(parents=True,exist_ok=True)
        original=source_dir/"original.pdf"
        if not original.exists(): original.write_bytes(pdf_bytes)
        job_id=f"pdfjob-{uuid.uuid4().hex}"
        job=self._job_dir(job_id); job.mkdir(parents=True,exist_ok=False)
        m={
            "job_id":job_id,"status":PdfJobStatus.PDF_UPLOADED.value,
            "created_at":self._now(),"updated_at":self._now(),
            "original_name":Path(original_name).name,
            "source_pdf_sha256":sha,"source_path":str(original),
            "extraction":None,"metadata":None,"candidate_summary":None,
            "onboarding_id":None,
        }
        self._write(self._manifest_path(job_id),m)
        return m

    def extract(self,job_id:str)->dict:
        m=self._manifest(job_id)
        source=Path(m["source_path"])
        try:
            reader=PdfReader(str(source))
            if reader.is_encrypted:
                try:
                    ok=reader.decrypt("")
                except Exception:
                    ok=0
                if not ok: raise ValueError("PASSWORD_PROTECTED_PDF")
            pages=[]
            corruption=0; chars=0
            meta=reader.metadata or {}
            for i,page in enumerate(reader.pages,1):
                text=(page.extract_text() or "").replace("\x00","")
                corruption += text.count("\ufffd")
                chars += len(text)
                pages.append({"pdf_page":i,"text":text})
        except Exception as exc:
            m["status"]=PdfJobStatus.EXTRACTION_REJECTED.value
            m["extraction"]={"quality":"FAIL","error":f"{type(exc).__name__}: {exc}"}
            self._save_manifest(job_id,m); return m
        total=len(pages)
        text_pages=sum(bool(p["text"].strip()) for p in pages)
        empty=total-text_pages
        avg=(chars/total) if total else 0
        corr_rate=(corruption/max(1,chars))
        quality="PASS" if total>0 and text_pages/max(1,total)>=0.8 and avg>=80 and corr_rate<0.01 else "LOW"
        report={
            "quality":quality,"pages":total,"text_pages":text_pages,"empty_pages":empty,
            "characters":chars,"average_chars_per_page":round(avg,2),
            "corruption_rate":round(corr_rate,6),
        }
        self._write(self._pages_path(job_id),pages)
        title,author,doi=infer_pdf_metadata(
            getattr(meta,"title",None) or meta.get("/Title") or "",
            getattr(meta,"author",None) or meta.get("/Author") or "",
            pages[0]["text"] if pages else "",
        )
        metadata={
            "title":title,"author":author,"year":None,"journal":None,"doi":doi,
            "language":"ko" if any("가"<=c<="힣" for p in pages[:2] for c in p["text"]) else "unknown",
            "paper_id":None,
        }
        m["extraction"]=report; m["metadata"]=metadata
        m["status"]=PdfJobStatus.EXTRACTED.value if quality=="PASS" else PdfJobStatus.EXTRACTION_REJECTED.value
        self._save_manifest(job_id,m); return m

    def get(self,job_id:str)->dict:
        m=self._manifest(job_id)
        if self._candidates_path(job_id).is_file():
            m={**m,"candidates":self._read(self._candidates_path(job_id))}
        return m

    def update_metadata(self,job_id:str,patch:dict)->dict:
        self._require_idle(job_id)
        m=self._manifest(job_id)
        allowed={"title","author","year","journal","doi","language","paper_id"}
        meta=dict(m.get("metadata") or {})
        for k,v in patch.items():
            if k in allowed: meta[k]=v
        m["metadata"]=meta; self._save_manifest(job_id,m); return m

    def generate_candidates(self,job_id:str)->dict:
        self._reserve_generation(job_id)
        return self._run_generation(job_id,raise_errors=True)

    def _require_idle(self,job_id):
        with self._generation_lock:
            if job_id in self._generating: raise ValueError("candidate generation is running")

    def _reserve_generation(self,job_id,join_existing=False):
        with self._generation_lock:
            if job_id in self._generating:
                if join_existing: return False
                raise ValueError("candidate generation is running")
            m=self._manifest(job_id)
            if m.get("status") not in {PdfJobStatus.EXTRACTED.value,PdfJobStatus.GENERATED.value,PdfJobStatus.READY_FOR_BUILD.value}:
                raise ValueError("PDF extraction quality has not passed")
            if self.candidate_generator is None: raise ValueError("candidate generator unavailable")
            count=len(self._read(self._pages_path(job_id)))
            size=getattr(self.candidate_generator,"batch_pages",8)
            m["generation"]={"status":"RUNNING","started_at":self._now(),"total_batches":(count+size-1)//size,
                             "completed_batches":0,"active_batches":0,"elapsed_seconds":0,
                             "peak_parallel":0,"failed_batches":[],"timed_out_batches":[]}
            self._save_manifest(job_id,m)
            self._generating.add(job_id)
            return True

    def start_generation(self,job_id):
        if not self._reserve_generation(job_id,join_existing=True): return self.get(job_id)
        threading.Thread(target=self._run_generation,args=(job_id,),daemon=True,
                         name="p2h-pdf-"+job_id).start()
        return self.get(job_id)

    def _run_generation(self,job_id,raise_errors=False):
        started=time.monotonic()
        try:
            self._generate_candidates(job_id)
            with self._generation_lock:
                m=self._manifest(job_id)
                m["generation"].update(status="SUCCEEDED",active_batches=0,
                                       elapsed_seconds=round(time.monotonic()-started,2))
                self._save_manifest(job_id,m)
            return self.get(job_id)
        except Exception as exc:
            with self._generation_lock:
                m=self._manifest(job_id)
                m["generation"].update(status="FAILED",active_batches=0,error=str(exc),
                                       elapsed_seconds=round(time.monotonic()-started,2))
                self._save_manifest(job_id,m)
            if raise_errors: raise
        finally:
            with self._generation_lock: self._generating.discard(job_id)

    def _generate_candidates(self,job_id:str)->dict:
        m=self._manifest(job_id)
        if m.get("status") not in {PdfJobStatus.EXTRACTED.value,PdfJobStatus.GENERATED.value,PdfJobStatus.READY_FOR_BUILD.value}:
            raise ValueError("PDF extraction quality has not passed")
        if self.candidate_generator is None: raise ValueError("candidate generator unavailable")
        pages=self._read(self._pages_path(job_id))
        def progress(update):
            with self._generation_lock:
                current=self._manifest(job_id)
                current["generation"].update(update)
                self._save_manifest(job_id,current)
        if getattr(self.candidate_generator,"supports_progress",False):
            raw=self.candidate_generator.generate(pages,m.get("metadata") or {},on_progress=progress)
        else:
            raw=self.candidate_generator.generate(pages,m.get("metadata") or {})
        # Keep the live per-batch progress when saving the final candidates.
        m=self._manifest(job_id)
        validated=[]
        page_map={p["pdf_page"]:p["text"] for p in pages}
        for idx,item in enumerate(raw,1):
            c=dict(item)
            c["candidate_id"]=c.get("candidate_id") or f"cand-{idx:04d}"
            c["decision"]="PENDING"
            ctype=c.get("statement_type")
            pg=c.get("pdf_page")
            span=c.get("evidence_span") or ""
            if ctype not in CANDIDATE_TYPES: continue
            if not isinstance(pg,int) or pg not in page_map: continue
            if not span or span not in page_map[pg]: continue
            if ctype=="EXTERNAL_QUOTE":
                c["evidence_voice"]="EXTERNAL"
            elif not c.get("evidence_voice"):
                c["evidence_voice"]="AUTHOR"
            c["confidence"]=float(c.get("confidence",0))
            validated.append(c)
        self._write(self._candidates_path(job_id),validated)
        m["candidate_summary"]={"total":len(validated),"pending":len(validated),"approved":0,"rejected":0}
        m["status"]=PdfJobStatus.GENERATED.value
        self._save_manifest(job_id,m); return self.get(job_id)

    def update_candidate(self,job_id:str,candidate_id:str,patch:dict)->dict:
        self._require_idle(job_id)
        candidates=self._read(self._candidates_path(job_id))
        found=None
        for c in candidates:
            if c["candidate_id"]==candidate_id:
                found=c; break
        if found is None: raise KeyError(candidate_id)
        if "decision" in patch:
            if patch["decision"] not in CANDIDATE_DECISIONS: raise ValueError("invalid candidate decision")
            found["decision"]=patch["decision"]
        for k in ("text","attributed_author"):
            if k in patch and isinstance(patch[k],str): found[k]=patch[k]
        self._write(self._candidates_path(job_id),candidates)
        m=self._manifest(job_id)
        counts={d.lower():sum(c["decision"]==d for c in candidates) for d in CANDIDATE_DECISIONS}
        m["candidate_summary"]={"total":len(candidates),**counts}
        m["status"]=PdfJobStatus.READY_FOR_BUILD.value if counts["approved"]>0 else PdfJobStatus.GENERATED.value
        self._save_manifest(job_id,m); return self.get(job_id)

    def approve_high_confidence_author_claims(self,job_id:str,threshold:float=0.9)->dict:
        self._require_idle(job_id)
        candidates=self._read(self._candidates_path(job_id))
        for c in candidates:
            if c["statement_type"]=="AUTHOR_CLAIM" and c.get("confidence",0)>=threshold and c["decision"]=="PENDING":
                c["decision"]="APPROVED"
        self._write(self._candidates_path(job_id),candidates)
        m=self._manifest(job_id)
        counts={d.lower():sum(c["decision"]==d for c in candidates) for d in CANDIDATE_DECISIONS}
        m["candidate_summary"]={"total":len(candidates),**counts}
        m["status"]=PdfJobStatus.READY_FOR_BUILD.value if counts["approved"]>0 else PdfJobStatus.GENERATED.value
        self._save_manifest(job_id,m); return self.get(job_id)

    def build_agent(self,job_id:str)->dict:
        self._require_idle(job_id)
        m=self._manifest(job_id)
        meta=m.get("metadata") or {}
        if not meta.get("title") or not meta.get("author") or not meta.get("paper_id"):
            raise ValueError("title, author, and paper_id are required")
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,160}",str(meta["paper_id"])):
            raise ValueError("invalid paper_id")
        candidates=self._read(self._candidates_path(job_id))
        approved=[c for c in candidates if c.get("decision")=="APPROVED"]
        if not approved: raise ValueError("at least one approved candidate is required")
        statements=[]
        for i,c in enumerate(approved,1):
            ctype=c["statement_type"]
            stype="SOURCE_QUOTE" if ctype in {"SOURCE_QUOTE","EXTERNAL_QUOTE"} else "AUTHOR_CLAIM"
            voice="EXTERNAL" if ctype=="EXTERNAL_QUOTE" else "AUTHOR"
            statements.append({
                "statement_id":f"{meta['paper_id']}-s{i:03d}",
                "statement_type":stype,
                "text":c["evidence_span"] if stype=="SOURCE_QUOTE" else c["text"],
                "paper_id":meta["paper_id"],
                "source_id":f"pdf-{m['source_pdf_sha256'][:16]}",
                "author":c.get("attributed_author") or meta["author"],
                "page":c["pdf_page"],
                "section":None,
                "evidence_span":c["evidence_span"],
                "citation":f"PDF p.{c['pdf_page']}",
                "edition_id":None,
                "evidence_voice":voice,
                "review_status":"REVIEWED",
            })
        concepts=[]
        for c in approved:
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}|[가-힣]{2,}",c["text"]):
                if token not in concepts: concepts.append(token)
                if len(concepts)>=20: break
            if len(concepts)>=20: break
        agent={
            "schema_version":2,
            "paper_id":meta["paper_id"],
            "title":meta["title"],
            "author":meta["author"],
            "publication":{"journal":meta.get("journal"),"year":meta.get("year"),"doi":meta.get("doi")},
            "source":{
                "source_id":f"pdf-{m['source_pdf_sha256'][:16]}",
                "sha256":m["source_pdf_sha256"],
                "origin":"pdf-onboarding",
                "paper2skill_verification":"user_reviewed_pdf_candidates",
                "pdf_pages":m.get("extraction",{}).get("pages"),
            },
            "concepts":concepts,
            "statements":statements,
            "corpus_policy":{"forbidden_terms":[]},
        }
        onboarding=self.onboarding.upload_json(agent,m["original_name"].rsplit(".",1)[0]+"-agent.json")
        validation=self.onboarding.validate(onboarding["onboarding_id"])
        if validation["validation"]["status"]!="PASS":
            raise ValueError("built agent failed onboarding validation: "+",".join(validation["validation"]["errors"]))
        m["onboarding_id"]=onboarding["onboarding_id"]; m["status"]=PdfJobStatus.BUILT.value
        self._save_manifest(job_id,m)
        return {"job":m,"agent":agent,"onboarding":validation}
