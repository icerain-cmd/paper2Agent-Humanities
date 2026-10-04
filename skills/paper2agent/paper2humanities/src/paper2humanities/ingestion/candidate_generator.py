from __future__ import annotations
from pathlib import Path
import json, shutil, subprocess, tempfile\nfrom concurrent.futures import ThreadPoolExecutor, as_completed

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
    def __init__(self,model:str="gpt-6-sol",executable:str|None=None,timeout:int=180,batch_pages:int=8,max_workers:int=4):
        self.model=model
        self.executable=executable or shutil.which("codex") or str(Path.home()/".local/bin/codex")
        self.timeout=timeout
        self.batch_pages=batch_pages\n        self.max_workers=max_workers

    def available(self):
        return Path(self.executable).exists() and SCHEMA_PATH.is_file()

    def generate(self,pages:list[dict],metadata:dict)->list[dict]:
        if not self.available(): raise RuntimeError("candidate model runtime unavailable")
        batches=[pages[start:start+self.batch_pages] for start in range(0,len(pages),self.batch_pages)]

        def run_batch(batch_index:int,batch:list[dict])->tuple[int,list[dict]]:
            payload={
                "system_contract":SYSTEM,
                "metadata":{k:metadata.get(k) for k in ("title","author","year","journal","language")},
                "pages":[{"pdf_page":p["pdf_page"],"text":p["text"][:18000]} for p in batch if p["text"].strip()],
            }
            if not payload["pages"]: return batch_index,[]
            prompt=json.dumps(payload,ensure_ascii=False,sort_keys=True)
            with tempfile.TemporaryDirectory(prefix="p2h-pdf-candidates-") as td:
                output=Path(td)/"candidates.json"
                argv=[self.executable,"exec","--ephemeral","--skip-git-repo-check",
                      "--ignore-user-config","--ignore-rules","-s","read-only","-m",self.model,
                      "--output-schema",str(SCHEMA_PATH),"-o",str(output),
                      prompt+"\nReturn exactly one object matching the schema. No tools or session state."]
                try:
                    cp=subprocess.run(argv,cwd=td,stdin=subprocess.DEVNULL,capture_output=True,text=True,
                                      timeout=self.timeout,check=False)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError(f"candidate batch {batch_index+1}/{len(batches)} timed out after {self.timeout}s") from exc
                if cp.returncode!=0:
                    raise RuntimeError(
                        f"candidate batch {batch_index+1}/{len(batches)} failed with exit {cp.returncode}: {cp.stderr[-500:]}"
                    )
                if not output.is_file():
                    raise RuntimeError(f"candidate batch {batch_index+1}/{len(batches)} produced no output")
                data=json.loads(output.read_text(encoding="utf-8"))
                return batch_index,data.get("candidates") or []

        results={}
        workers=max(1,min(self.max_workers,len(batches)))
        with ThreadPoolExecutor(max_workers=workers,thread_name_prefix="p2h-candidates") as pool:
            futures={pool.submit(run_batch,i,b):i for i,b in enumerate(batches)}
            for future in as_completed(futures):
                i,items=future.result()
                results[i]=items
        out=[]
        for i in range(len(batches)):
            out.extend(results.get(i,[]))
        return out
