from pathlib import Path
import json, sys, tempfile
import fitz

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from paper2humanities.onboarding import OnboardingService
from paper2humanities.ingestion import PdfIngestionService

class FakeGenerator:
    def generate(self,pages,metadata):
        p1=pages[0]["text"]
        p2=pages[1]["text"]
        p3=pages[2]["text"]
        def line(text,prefix):
            return next(x.strip() for x in text.splitlines() if x.strip().startswith(prefix))
        return [
            {"statement_type":"AUTHOR_CLAIM","text":"The paper defines synthetic aura as a relation between distance and mediation.","pdf_page":1,
             "evidence_span":line(p1,"This paper defines"),"evidence_voice":"AUTHOR","attributed_author":metadata.get("author"),"confidence":0.96},
            {"statement_type":"EXTERNAL_QUOTE","text":"Benjamin is quoted on the unique appearance of distance.","pdf_page":2,
             "evidence_span":line(p2,"Benjamin writes"),"evidence_voice":"EXTERNAL","attributed_author":"Walter Benjamin","confidence":0.94},
            {"statement_type":"AUTHOR_CLAIM","text":"The paper argues that digital mediation reorganizes distance.","pdf_page":3,
             "evidence_span":line(p3,"We argue"),"evidence_voice":"AUTHOR","attributed_author":metadata.get("author"),"confidence":0.93},
            {"statement_type":"AUTHOR_CLAIM","text":"Invalid invented evidence must be dropped.","pdf_page":3,
             "evidence_span":"THIS STRING DOES NOT EXIST","evidence_voice":"AUTHOR","attributed_author":metadata.get("author"),"confidence":0.99},
        ]

def make_pdf(path:Path):
    doc=fitz.open()
    texts=[
        "Synthetic Aura and Mediation\nTest Scholar\nThis paper defines synthetic aura as a relation between distance and mediation. The argument concerns technical reproduction and changing reception. The article develops a bounded interpretation from textual evidence and distinguishes author claims from quotations. Additional discussion ensures enough text for reliable extraction quality on this page.",
        "Prior Work and Quotation\nBenjamin writes: Aura is the unique appearance of a distance, however near it may be. This sentence is presented here as an external quotation from Walter Benjamin. The paper does not claim that this quotation is the present author's own proposition. Instead, it uses the quotation as a historical reference for the following analysis. Additional text preserves extraction quality.",
        "Digital Transformation\nWe argue that digital mediation reorganizes distance rather than simply restoring an earlier aura. The claim is limited to the conceptual model proposed in this synthetic test paper. It does not establish empirical proof of a new aura. The conclusion proposes comparison with other media theories and keeps the distinction between source evidence and later interpretation explicit.",
    ]
    for text in texts:
        page=doc.new_page(width=595,height=842)
        page.insert_textbox(fitz.Rect(60,60,535,780),text,fontsize=12,fontname="helv",lineheight=1.5)
    doc.set_metadata({"title":"Synthetic Aura and Mediation","author":"Test Scholar"})
    doc.save(path)
    doc.close()

def test_pdf_ingestion_review_build_pipeline():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        pdf=td/"paper.pdf"; make_pdf(pdf)
        onboarding=OnboardingService(td/"store",ROOT/"fixtures")
        svc=PdfIngestionService(td/"store",onboarding,FakeGenerator())
        up=svc.upload_pdf(pdf.read_bytes(),"paper.pdf")
        assert up["status"]=="PDF_UPLOADED"
        ext=svc.extract(up["job_id"])
        assert ext["status"]=="EXTRACTED"
        assert ext["extraction"]["quality"]=="PASS" and ext["extraction"]["pages"]==3
        svc.update_metadata(up["job_id"],{"paper_id":"synthetic-aura-test","year":2026,"journal":"Test Journal"})
        gen=svc.generate_candidates(up["job_id"])
        assert len(gen["candidates"])==3
        assert all(c["evidence_span"] in json.loads((td/"store"/"pdf_jobs"/up["job_id"]/"pages.json").read_text())[c["pdf_page"]-1]["text"] for c in gen["candidates"])
        gen=svc.approve_high_confidence_author_claims(up["job_id"])
        extq=next(c for c in gen["candidates"] if c["statement_type"]=="EXTERNAL_QUOTE")
        svc.update_candidate(up["job_id"],extq["candidate_id"],{"decision":"APPROVED"})
        built=svc.build_agent(up["job_id"])
        assert built["onboarding"]["validation"]["status"]=="PASS"
        oid=built["onboarding"]["onboarding_id"]
        reg=onboarding.register(oid)
        assert reg["active_manifest"]["status"]=="ACTIVE"
        agent=json.loads((onboarding.active_dir/"synthetic-aura-test"/"agent.json").read_text())
        assert len(agent["statements"])==3
        external=next(s for s in agent["statements"] if s["evidence_voice"]=="EXTERNAL")
        assert external["author"]=="Walter Benjamin"

def test_low_text_pdf_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        pdf=td/"low.pdf"
        doc=fitz.open(); page=doc.new_page(); page.insert_text((72,72),"tiny"); doc.save(pdf); doc.close()
        onboarding=OnboardingService(td/"store",ROOT/"fixtures")
        svc=PdfIngestionService(td/"store",onboarding,FakeGenerator())
        up=svc.upload_pdf(pdf.read_bytes(),"low.pdf")
        ext=svc.extract(up["job_id"])
        assert ext["status"]=="EXTRACTION_REJECTED"
        assert ext["extraction"]["quality"]=="LOW"
        try:
            svc.generate_candidates(up["job_id"])
            raise AssertionError("generation should be blocked")
        except ValueError:
            pass

def test_non_pdf_rejected():
    with tempfile.TemporaryDirectory() as td:
        onboarding=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        svc=PdfIngestionService(Path(td)/"store",onboarding,FakeGenerator())
        try:
            svc.upload_pdf(b"not pdf","x.pdf")
            raise AssertionError("non-pdf should fail")
        except ValueError:
            pass

def test_doi_glued_heading_is_retained_and_creator_is_not_author():
    from paper2humanities.ingestion.service import infer_pdf_metadata
    first="http://dx.doi.org/\u200b10\u200b.21793\u200b/koreall.2026.133.11기술생성시대의 매체미학*1)\n- 기억, 충동, 가치를 중심으로 -이용욱(전주대)**목 차"
    assert infer_pdf_metadata("","윤화정",first)==("기술생성시대의 매체미학","이용욱","10.21793/koreall.2026.133.11")
    assert infer_pdf_metadata(first.splitlines()[0],"",first)[0]=="기술생성시대의 매체미학"

def test_regular_title_and_author_are_preserved():
    from paper2humanities.ingestion.service import infer_pdf_metadata
    assert infer_pdf_metadata("Synthetic Aura and Mediation","Test Scholar","Page header\nText")==("Synthetic Aura and Mediation","Test Scholar",None)
    assert infer_pdf_metadata("https://doi.org/10.1234/normal.1","Test Scholar","Actual Scholarly Title\nTest Scholar")==("Actual Scholarly Title","Test Scholar","10.1234/normal.1")

def test_root_contract_redirects_without_bypassing_auth(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from paper2humanities.api import create_app
    monkeypatch.setenv("P2H_DATA_DIR",str(tmp_path))
    monkeypatch.setenv("P2H_AUTH_USER","owner")
    monkeypatch.setenv("P2H_AUTH_PASSWORD","test-password")
    c=TestClient(create_app(ROOT))
    assert c.get("/").status_code==401
    r=c.get("/",auth=("owner","test-password"),follow_redirects=False)
    assert r.status_code==307 and r.headers["location"]=="/debate"
    assert "Live Scholarly Debate" in c.get("/",auth=("owner","test-password")).text


def test_candidate_batches_parallel_order_and_unique_outputs(tmp_path):
    from paper2humanities.ingestion.candidate_generator import CodexCandidateGenerator
    executable=tmp_path/'codex-fixture'
    trace=tmp_path/'trace'
    executable.write_text('''#!/usr/bin/python3
import json,sys,time,pathlib
payload=json.loads(sys.argv[-1].split('\\nReturn exactly')[0]); page=payload['pages'][0]['pdf_page']
output=pathlib.Path(sys.argv[sys.argv.index('-o')+1])
with pathlib.Path(TRACE).open('a') as f: f.write(str(output)+'\\n')
time.sleep(.08 if page==1 else .01)
output.write_text(json.dumps({'candidates':[{'pdf_page':page}]}))
'''.replace('TRACE',repr(str(trace))))
    executable.chmod(0o700)
    updates=[]
    gen=CodexCandidateGenerator(executable=str(executable),batch_pages=1,max_workers=2)
    result=gen.generate([{'pdf_page':1,'text':'first'},{'pdf_page':2,'text':'second'}],{},updates.append)
    assert [c['pdf_page'] for c in result]==[1,2]
    assert updates[-1]['completed_batches']==2 and updates[-1]['peak_parallel']==2
    assert len(set(trace.read_text().splitlines()))==2


def test_candidate_failure_cancels_queue_and_timeout_kills_children(tmp_path):
    import os,time,pytest
    from paper2humanities.ingestion.candidate_generator import CodexCandidateGenerator
    executable=tmp_path/'codex-fixture'; child_pid=tmp_path/'child-pid'
    executable.write_text('''#!/usr/bin/python3
import json,sys,time,subprocess,pathlib
payload=json.loads(sys.argv[-1].split('\\nReturn exactly')[0]); page=payload['pages'][0]['pdf_page']
if page==1:
 time.sleep(.05); sys.exit(2)
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
pathlib.Path(PID).write_text(str(child.pid))
time.sleep(30)
'''.replace('PID',repr(str(child_pid))))
    executable.chmod(0o700)
    gen=CodexCandidateGenerator(executable=str(executable),batch_pages=1,max_workers=2,timeout=.5)
    started=time.monotonic()
    with pytest.raises(RuntimeError,match='failed with exit'):
        gen.generate([{'pdf_page':n,'text':'grounded'} for n in range(1,10)],{})
    assert time.monotonic()-started<2
    if child_pid.exists():
        stat=Path('/proc')/child_pid.read_text()/'stat'
        assert not stat.exists() or stat.read_text().split()[2]=='Z'
    updates=[]
    with pytest.raises(RuntimeError,match='timed out'):
        gen.generate([{'pdf_page':2,'text':'grounded'}],{},updates.append)
    assert updates[-1]['timed_out_batches']==[1]
    stat=Path('/proc')/child_pid.read_text()/'stat'
    assert not stat.exists() or stat.read_text().split()[2]=='Z'


def test_background_generation_progress_duplicate_guard_and_failure(tmp_path,monkeypatch):
    import threading,time
    from fastapi.testclient import TestClient
    from paper2humanities.api import create_app
    from paper2humanities.ingestion.candidate_generator import CodexCandidateGenerator
    monkeypatch.setenv('P2H_DATA_DIR',str(tmp_path/'store'))
    app=create_app(ROOT);svc=app.state.debate.ingestion
    entered=threading.Event();release=threading.Event()
    class DelayedGenerator(FakeGenerator):
        supports_progress=True
        batch_pages=1
        def generate(self,pages,metadata,on_progress):
            entered.set();on_progress({'total_batches':3,'completed_batches':1,'active_batches':1,'peak_parallel':1})
            release.wait(3)
            return super().generate(pages,metadata)
    svc.candidate_generator=DelayedGenerator()
    pdf=tmp_path/'paper.pdf';make_pdf(pdf)
    job=svc.upload_pdf(pdf.read_bytes(),'paper.pdf');jid=job['job_id'];svc.extract(jid)
    c=TestClient(app)
    r=c.post(f'/api/agents/from-pdf/{jid}/generate-candidates?background=true')
    assert r.status_code==202 and entered.wait(1)
    assert c.get(f'/api/agents/from-pdf/{jid}').json()['generation']['completed_batches']==1
    assert c.post(f'/api/agents/from-pdf/{jid}/generate-candidates?background=true').status_code==202
    assert c.post(f'/api/agents/from-pdf/{jid}/generate-candidates').status_code==400
    assert c.patch(f'/api/agents/from-pdf/{jid}/metadata',json={'metadata':{'title':'race'}}).status_code==400
    release.set()
    for _ in range(100):
        final=c.get(f'/api/agents/from-pdf/{jid}').json()
        if final['generation']['status']!='RUNNING':break
        time.sleep(.01)
    assert final['generation']['status']=='SUCCEEDED' and final['candidate_summary']['total']==3
    class FailingGenerator:
        def generate(self,pages,metadata):raise RuntimeError('candidate batch 1 failed')
    svc.candidate_generator=FailingGenerator()
    assert c.post(f'/api/agents/from-pdf/{jid}/generate-candidates?background=true').status_code==202
    for _ in range(100):
        final=svc.get(jid)
        if final['generation']['status']!='RUNNING':break
        time.sleep(.01)
    assert final['generation']['status']=='FAILED' and 'batch 1 failed' in final['generation']['error']
    # Failed regeneration retains the prior reviewed candidates and can be retried.
    assert len(final['candidates'])==3


def test_interrupted_generation_is_reported_and_retryable(tmp_path):
    onboarding=OnboardingService(tmp_path/'store',ROOT/'fixtures')
    svc=PdfIngestionService(tmp_path/'store',onboarding,FakeGenerator())
    pdf=tmp_path/'paper.pdf';make_pdf(pdf)
    job=svc.upload_pdf(pdf.read_bytes(),'paper.pdf');jid=job['job_id'];svc.extract(jid)
    manifest=svc._manifest(jid);manifest['generation']={'status':'RUNNING'};svc._save_manifest(jid,manifest)
    restarted=PdfIngestionService(tmp_path/'store',onboarding,FakeGenerator())
    assert restarted.get(jid)['generation']['status']=='FAILED'
    assert 'restart' in restarted.get(jid)['generation']['error']
    assert restarted.generate_candidates(jid)['generation']['status']=='SUCCEEDED'


def test_korean_ui_default_id_satisfies_build_contract():
    import subprocess,re
    source=(ROOT/'web/app.js').read_text().rsplit('\ninit();',1)[0]
    code="const vm=require('vm');const ctx={};vm.createContext(ctx);vm.runInContext("+json.dumps(source)+",ctx);console.log(JSON.stringify(vm.runInContext(\"[pdfAgentId({author:'이용욱',title:'기술생성시대의 매체미학'},'e538b7cd3af7190f'),pdfAgentId({author:'Test Scholar',title:'Synthetic Aura'},'e538b7cd3af7190f')]\",ctx)));"
    result=json.loads(subprocess.check_output(['node','-e',code],text=True))
    assert re.fullmatch(r'[A-Za-z0-9._-]{3,160}',result[0])
    assert result[0]=='paper-e538b7cd3af7190f'
    assert result[1]=='test-scholar-synthetic-aura'


def test_progress_callback_failure_does_not_orphan_runtime(tmp_path,monkeypatch):
    import pytest,subprocess
    from paper2humanities.ingestion.candidate_generator import CodexCandidateGenerator
    executable=tmp_path/'codex-fixture';executable.write_text('#!/usr/bin/python3\nimport time\ntime.sleep(30)\n');executable.chmod(0o700)
    processes=[];original=subprocess.Popen
    def capture(*args,**kwargs):
        process=original(*args,**kwargs);processes.append(process);return process
    monkeypatch.setattr(subprocess,'Popen',capture)
    def broken_progress(update):raise OSError('progress persistence unavailable')
    with pytest.raises(OSError,match='progress persistence'):
        CodexCandidateGenerator(executable=str(executable)).generate([{'pdf_page':1,'text':'grounded'}],{},broken_progress)
    assert processes and all(p.poll() is not None for p in processes)
