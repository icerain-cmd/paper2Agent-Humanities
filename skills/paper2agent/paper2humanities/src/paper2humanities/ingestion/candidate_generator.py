from __future__ import annotations
from pathlib import Path
import json, os, signal, shutil, subprocess, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

SCHEMA_PATH=Path(__file__).with_name("candidate_batch.schema.json")

SYSTEM="""You extract grounded scholarly statement candidates from PDF page text.
Use only the supplied page text. Never invent a page, quotation, author, or evidence span.
For each candidate:
- evidence_span MUST be copied verbatim as a contiguous substring of that page text.
- AUTHOR_CLAIM: a proposition attributable to the paper's author, paraphrased conservatively.
- SOURCE_QUOTE: a direct quotation in the paper that is the paper author's own voice.
- EXTERNAL_QUOTE: a quotation or proposition explicitly attributed to another named author/source.
For EXTERNAL_QUOTE set evidence_voice=EXTERNAL and attributed_author when identifiable.
For all others evidence_voice=AUTHOR.
Return only useful scholarly claims. Prefer 1-4 candidates per page; skip pages without substantive claims.
Do not output interpretations beyond the source text."""

class CodexCandidateGenerator:
    supports_progress=True
    def __init__(self,model:str="gpt-6-sol",executable:str|None=None,timeout:int=180,batch_pages:int=8,max_workers:int=4):
        self.model=model
        self.executable=executable or shutil.which("codex") or str(Path.home()/".local/bin/codex")
        self.timeout=timeout
        self.batch_pages=batch_pages
        self.max_workers=max_workers
        if batch_pages<1 or max_workers<1 or timeout<=0:
            raise ValueError("batch_pages, max_workers and timeout must be positive")

    def available(self):
        return Path(self.executable).is_file() and os.access(self.executable,os.X_OK) and SCHEMA_PATH.is_file()

    def generate(self,pages:list[dict],metadata:dict,on_progress=None)->list[dict]:
        if not self.available(): raise RuntimeError("candidate model runtime unavailable")
        batches=[pages[start:start+self.batch_pages] for start in range(0,len(pages),self.batch_pages)]
        cancelled=threading.Event()
        lock=threading.Lock()
        processes=set()
        started=time.monotonic()
        progress={"total_batches":len(batches),"completed_batches":0,"active_batches":0,
                  "peak_parallel":0,"failed_batches":[],"timed_out_batches":[]}

        def publish():
            if on_progress: on_progress({**progress,"elapsed_seconds":round(time.monotonic()-started,2)})

        def stop_process(process):
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass

        def run_batch(batch_index:int,batch:list[dict])->tuple[int,list[dict]]:
            if cancelled.is_set(): raise RuntimeError("candidate generation cancelled")
            payload={
                "system_contract":SYSTEM,
                "metadata":{k:metadata.get(k) for k in ("title","author","year","journal","language")},
                "pages":[{"pdf_page":p["pdf_page"],"text":p["text"][:18000]} for p in batch if p["text"].strip()],
            }
            if not payload["pages"]:
                with lock:
                    progress["completed_batches"]+=1
                    publish()
                return batch_index,[]
            prompt=json.dumps(payload,ensure_ascii=False,sort_keys=True)
            with tempfile.TemporaryDirectory(prefix="p2h-pdf-candidates-") as td:
                output=Path(td)/"candidates.json"
                argv=[self.executable,"exec","--ephemeral","--skip-git-repo-check",
                      "--ignore-user-config","--ignore-rules","-s","read-only","-m",self.model,
                      "--output-schema",str(SCHEMA_PATH),"-o",str(output),
                      prompt+"\nReturn exactly one object matching the schema. No tools or session state."]
                try:
                    # Codex's Node launcher spawns the native runtime. A process
                    # group ensures timeout/cancellation also stops that child.
                    with lock:
                        if cancelled.is_set(): raise RuntimeError("candidate generation cancelled")
                        process=subprocess.Popen(argv,cwd=td,stdin=subprocess.DEVNULL,
                                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                                 start_new_session=True)
                        processes.add(process)
                        progress["active_batches"]+=1
                        progress["peak_parallel"]=max(progress["peak_parallel"],progress["active_batches"])
                        publish()
                    stdout,stderr=process.communicate(timeout=self.timeout)
                except subprocess.TimeoutExpired as exc:
                    stop_process(process)
                    process.communicate()
                    with lock: progress["timed_out_batches"].append(batch_index+1)
                    raise RuntimeError(f"candidate batch {batch_index+1}/{len(batches)} timed out after {self.timeout}s") from exc
                except Exception:
                    if 'process' in locals():
                        stop_process(process)
                        process.communicate()
                    raise
                finally:
                    if 'process' in locals():
                        with lock:
                            processes.discard(process)
                            progress["active_batches"]-=1
                if process.returncode!=0:
                    raise RuntimeError(
                        f"candidate batch {batch_index+1}/{len(batches)} failed with exit {process.returncode}: {stderr[-500:]}"
                    )
                if not output.is_file():
                    raise RuntimeError(f"candidate batch {batch_index+1}/{len(batches)} produced no output")
                data=json.loads(output.read_text(encoding="utf-8"))
                if not isinstance(data,dict) or not isinstance(data.get("candidates"),list):
                    raise RuntimeError(f"candidate batch {batch_index+1}/{len(batches)} returned invalid candidates")
                with lock:
                    progress["completed_batches"]+=1
                    publish()
                return batch_index,data.get("candidates") or []

        results={}
        workers=max(1,min(self.max_workers,len(batches)))
        with ThreadPoolExecutor(max_workers=workers,thread_name_prefix="p2h-candidates") as pool:
            futures={pool.submit(run_batch,i,b):i for i,b in enumerate(batches)}
            try:
                for future in as_completed(futures):
                    i,items=future.result()
                    results[i]=items
            except Exception:
                cancelled.set()
                with lock:
                    progress["failed_batches"].append(futures[future]+1)
                    for process in list(processes): stop_process(process)
                    publish()
                for pending in futures: pending.cancel()
                raise
        out=[]
        for i in range(len(batches)):
            out.extend(results.get(i,[]))
        return out
