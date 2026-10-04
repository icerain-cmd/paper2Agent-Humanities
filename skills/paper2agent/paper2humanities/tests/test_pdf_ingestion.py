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
