from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from paper2humanities.debate import AgentRegistry, DebateEngine, DebateAction
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
            "text":f"{payload['agent_identity']['paper_id']} grounded turn",
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
        return ModelResult(json.dumps(obj,ensure_ascii=False),self.provider,self.model,{}, "x")

def registry():
    return AgentRegistry(ROOT/"fixtures")

def test_registry_is_dynamic_and_has_canonical_agents():
    ids=registry().ids()
    assert "lee-aura-2019" in ids
    assert "benjamin-artwork-v2" in ids
    assert "benjamin-artwork-v3" in ids

def test_two_agent_orchestration_and_own_evidence():
    reg=registry()
    engine=DebateEngine(reg,FakeAdapter())
    s=engine.create_session(["benjamin-artwork-v2","lee-aura-2019"],"아우라 거리와 디지털아우라",6)
    engine.run(s)
    assert len(s.turns)==6 and s.status=="COMPLETED"
    for t in s.turns:
        a=reg.get(t.speaker_agent_id)
        assert all(e["paper_id"]==a.paper_id and e["source_id"]==a.source_id for e in t.evidence)
    assert s.turns[0].action==DebateAction.POSITION
    assert s.turns[1].context_turn_ids==["turn-001"]

def test_three_agent_round_robin():
    reg=registry()
    engine=DebateEngine(reg,FakeAdapter())
    ids=["benjamin-artwork-v2","lee-aura-2019","benjamin-artwork-v3"]
    s=engine.create_session(ids,"아우라와 기술",6)
    engine.run(s)
    assert [t.speaker_agent_id for t in s.turns]==[ids[i%3] for i in range(6)]

def test_user_intervention_updates_active_issue():
    reg=registry(); engine=DebateEngine(reg,FakeAdapter())
    s=engine.create_session(["benjamin-artwork-v2","lee-aura-2019"],"아우라",2)
    engine.intervene(s,"거리 개념으로 좁혀라")
    assert s.active_issue=="거리 개념으로 좁혀라"


def test_registry_discovers_new_canonical_agent_without_code_change():
    import json, tempfile
    from pathlib import Path
    src=ROOT/"fixtures"/"lee-aura-2019-agent.json"
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        data=json.loads(src.read_text())
        data["paper_id"]="generic-test-paper"
        data["title"]="Generic Test Paper"
        data["author"]="Generic Scholar"
        data["source"]["source_id"]="s-generic-test"
        data["source"]["sha256"]="0"*64
        for s in data["statements"]:
            if s.get("paper_id"):
                s["paper_id"]="generic-test-paper"
            if s.get("source_id"):
                s["source_id"]="s-generic-test"
        (d/"generic-test-paper-agent.json").write_text(json.dumps(data,ensure_ascii=False))
        reg=AgentRegistry(d)
        assert reg.ids()==("generic-test-paper",)
        desc=reg.describe()[0]
        assert desc["author"]=="Generic Scholar"
        assert desc["reviewed_grounded_count"]>0


def test_registry_reports_rejected_agent_files():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        (d/"broken-agent.json").write_text("{not json")
        reg=AgentRegistry(d)
        diag=reg.diagnostics()
        assert diag["loaded"]==0
        assert diag["rejected"] and diag["rejected"][0]["file"]=="broken-agent.json"


def test_v2_two_agent_standard_is_balanced():
    reg=registry(); engine=DebateEngine(reg,FakeAdapter())
    ids=["benjamin-artwork-v2","lee-aura-2019"]
    s=engine.create_session(ids,"아우라의 거리와 기술적 복제, 디지털아우라",10)
    assignments=[]
    for _ in range(10):
        speaker,targets,action=engine.orchestrator.next_assignment(s)
        assignments.append((speaker,action))
        engine.step(s)
    assert [a.value for _,a in assignments]==[
        "POSITION","POSITION","CRITIQUE","CRITIQUE","REBUTTAL","REBUTTAL",
        "REVISION","REVISION","CLOSING","CLOSING"]
    assert sum(sp==ids[0] for sp,_ in assignments)==5
    assert sum(sp==ids[1] for sp,_ in assignments)==5
    passed=[t for t in s.turns if t.verification_status=="PASS"]
    assert passed and all(t.thesis for t in passed)
    assert all(t.stance_update in {"MAINTAIN","REVISE","NARROW"} for t in passed)


def test_v2_three_agent_standard_is_balanced():
    reg=registry(); engine=DebateEngine(reg,FakeAdapter())
    ids=["benjamin-artwork-v2","lee-aura-2019","benjamin-artwork-v3"]
    s=engine.create_session(ids,"아우라의 거리, 진정성, 기술적 복제와 디지털 변형",15)
    engine.run(s)
    assert len(s.turns)==15
    assert [sum(t.speaker_agent_id==aid for t in s.turns) for aid in ids]==[5,5,5]
    assert [t.action.value for t in s.turns[-3:]]==["CLOSING","CLOSING","CLOSING"]


def test_v2_deep_adds_cross_examination():
    reg=registry(); engine=DebateEngine(reg,FakeAdapter())
    s=engine.create_session(["benjamin-artwork-v2","lee-aura-2019"],"아우라와 기술적 복제, 거리와 디지털 변형",14)
    engine.run(s)
    actions=[t.action.value for t in s.turns]
    assert actions.count("QUESTION")==2
    assert actions.count("RESPONSE")==2
    assert actions[-2:]==["CLOSING","CLOSING"]
