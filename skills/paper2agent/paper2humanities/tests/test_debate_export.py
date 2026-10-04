from pathlib import Path
import json, sys, tempfile
import fitz

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from paper2humanities.api.store import SQLiteSessionStore
from paper2humanities.debate import AgentRegistry
from paper2humanities.debate.models import DebateSession, DebateTurn, DebateAction
from paper2humanities.exporting import DebateExporter

def make_session():
    s=DebateSession(
        topic="아우라는 기술의 산물인가, 인간 인지 감각의 산물인가?",
        participant_ids=["benjamin-artwork-v2","lee-aura-2019"],
        max_turns=10,
        protocol_version="2.0",
        status="COMPLETED",
        current_turn=2,
    )
    s.turns=[
        DebateTurn(
            turn_id="turn-001",speaker_agent_id="benjamin-artwork-v2",
            target_agent_ids=["lee-aura-2019"],action=DebateAction.POSITION,
            text="아우라는 거리와 일회성의 지각 경험이며 기술적 복제는 그 쇠퇴 조건이다.",
            support_ids=["b-v2-c-aura-decay"],pages=[6],
            evidence=[{
                "statement_id":"b-v2-c-aura-decay","paper_id":"benjamin-artwork-v2",
                "source_id":"s001-benjamin-kunstwerk-v2-gs350-384-verified",
                "edition_id":"benjamin-artwork-v2","page":6,
                "statement_type":"AUTHOR_CLAIM","evidence_voice":"AUTHOR",
                "text":"Benjamin defines aura as distance.",
                "evidence_span":"Was ist eigentlich Aura? Ein sonderbares Gespinst aus Raum und Zeit.",
                "citation":"V2 PDF p.6",
            }],
            semantic_support="SEMANTICALLY_SUPPORTED",verification_status="PASS",
            thesis="아우라는 거리와 일회성의 지각 경험이다.",
            target_claim=None,stance_update="MAINTAIN",
            unresolved_point="기술과 지각의 인과관계를 어떻게 구분할 것인가?",
        ),
        DebateTurn(
            turn_id="turn-002",speaker_agent_id="lee-aura-2019",
            target_agent_ids=["benjamin-artwork-v2"],action=DebateAction.CRITIQUE,
            text="디지털 환경에서는 거리 자체보다 거리의 배치와 수용 맥락을 함께 검토해야 한다.",
            support_ids=["lee-c-trust-definition"],pages=[24],
            evidence=[{
                "statement_id":"lee-c-trust-definition","paper_id":"lee-aura-2019",
                "source_id":"s001-lee-aura-2019","edition_id":None,"page":24,
                "statement_type":"AUTHOR_CLAIM","evidence_voice":"AUTHOR",
                "text":"신뢰화는 거리를 조정하는 편집기술이다.",
                "evidence_span":"사용의 맥락과 주체의 욕망에 따라 가상텍스트가 배치되고 거리가 조정된다.",
                "citation":"PDF p.24",
            }],
            semantic_support="SEMANTICALLY_SUPPORTED",verification_status="PASS",
            thesis="디지털 환경의 거리는 편집기술과 수용 맥락의 관계로 봐야 한다.",
            target_claim="아우라는 거리와 일회성의 지각 경험이다.",
            stance_update="NARROW",
            unresolved_point="조정된 거리가 언제 아우라적 외관이 되는가?",
        ),
    ]
    s.interventions=[{"at_turn":1,"text":"거리 개념에 집중해서 논의를 좁혀라."}]
    return s

def test_markdown_json_and_pdf_export():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        store=SQLiteSessionStore(td/"test.db")
        session=make_session()
        store.put(session)
        store.append_event(session.session_id,"turn_completed",session.turns[0].to_dict())
        registry=AgentRegistry(ROOT/"fixtures")
        exporter=DebateExporter(registry,store)

        md=exporter.build_markdown(session)
        assert "# 아우라는 기술의 산물인가" in md
        assert "**Thesis:**" in md
        assert "**Stance update:** NARROW" in md
        assert "User intervention" in md
        assert "lee-c-trust-definition" in md
        assert "PDF p.24" in md

        data=exporter.build_json(session)
        assert data["export_schema"]=="paper2agent-humanities-debate-export-v1"
        assert data["session"]["protocol_version"]=="2.0"
        assert len(data["participants"])==2
        assert len(data["evidence_index"])==2
        assert data["events"][0]["event"]=="turn_completed"

        pdf=exporter.write_pdf(session,td/"debate.pdf")
        assert pdf.is_file() and pdf.stat().st_size>5000
        doc=fitz.open(pdf)
        assert len(doc)>=1
        text="\n".join(page.get_text() for page in doc)
        assert "아우라는 기술의 산물인가" in text
        assert "User intervention" in text
        assert "lee-c-trust-definition" in text
        pix=doc[0].get_pixmap(matrix=fitz.Matrix(1.2,1.2),alpha=False)
        pix.save(td/"page1.png")
        print("PDF",pdf)
        print("PNG",td/"page1.png")
