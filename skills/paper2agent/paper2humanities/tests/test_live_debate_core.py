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
