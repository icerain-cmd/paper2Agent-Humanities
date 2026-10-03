from pathlib import Path
import copy, json, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from paper2humanities.onboarding import OnboardingService
from paper2humanities.debate import AgentRegistry

def make_agent():
    data=json.loads((ROOT/"fixtures"/"lee-aura-2019-agent.json").read_text())
    data["paper_id"]="registered-test-paper"
    data["title"]="Registered Test Paper"
    data["author"]="Registered Scholar"
    data["source"]["source_id"]="s-registered-test-paper"
    data["source"]["sha256"]="2"*64
    for s in data["statements"]:
        if s.get("paper_id"):
            s["paper_id"]="registered-test-paper"
        if s.get("source_id"):
            s["source_id"]="s-registered-test-paper"
    return data

def test_valid_agent_lifecycle_and_registry_visibility():
    with tempfile.TemporaryDirectory() as td:
        svc=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        up=svc.upload_json(make_agent(),"../../unsafe-name.json")
        assert up["status"]=="UPLOADED"
        assert up["original_name"]=="unsafe-name.json"
        val=svc.validate(up["onboarding_id"])
        assert val["status"]=="READY_FOR_REVIEW"
        assert val["validation"]["status"]=="PASS"
        assert val["validation"]["counts"]["reviewed_grounded"]>0
        reg=svc.register(up["onboarding_id"])
        assert reg["active_manifest"]["status"]=="ACTIVE"
        registry=AgentRegistry(ROOT/"fixtures",svc.active_dir)
        assert "registered-test-paper" in registry.ids()
        desc=next(x for x in registry.describe() if x["agent_id"]=="registered-test-paper")
        assert desc["origin"]=="registered" and desc["can_disable"] is True
        disabled=svc.disable("registered-test-paper")
        assert disabled["status"]=="DISABLED"
        registry.reload()
        assert "registered-test-paper" not in registry.ids()

def test_invalid_agent_is_rejected_and_cannot_register():
    with tempfile.TemporaryDirectory() as td:
        svc=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        data=make_agent()
        claim=next(x for x in data["statements"] if x["statement_type"]=="AUTHOR_CLAIM")
        claim["evidence_voice"]="EXTERNAL"
        up=svc.upload_json(data,"bad.json")
        val=svc.validate(up["onboarding_id"])
        assert val["status"]=="REJECTED"
        assert val["validation"]["status"]=="FAIL"
        assert any("EXTERNAL_AS_AUTHOR" in e for e in val["validation"]["errors"])
        try:
            svc.register(up["onboarding_id"])
            raise AssertionError("register should fail")
        except ValueError:
            pass

def test_duplicate_builtin_id_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        svc=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        data=json.loads((ROOT/"fixtures"/"benjamin-artwork-v2-agent.json").read_text())
        up=svc.upload_json(data,"duplicate.json")
        val=svc.validate(up["onboarding_id"])
        assert "DUPLICATE_PAPER_ID" in val["validation"]["errors"]

def test_builtin_agent_cannot_be_disabled():
    with tempfile.TemporaryDirectory() as td:
        svc=OnboardingService(Path(td)/"store",ROOT/"fixtures")
        try:
            svc.disable("benjamin-artwork-v2")
            raise AssertionError("built-in disable should fail")
        except ValueError as exc:
            assert "built-in" in str(exc)
