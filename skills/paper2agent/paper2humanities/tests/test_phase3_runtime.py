from pathlib import Path
import pytest

from paper2humanities import PaperAgent
from paper2humanities.runtime.model_adapter import ModelAdapter, ModelRuntimeUnavailable, require_live_adapter
from paper2humanities.runtime.retrieval import retrieve
from paper2humanities.runtime.verifier import publication_gate

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"src"/"paper2humanities"/"runtime"

class MissingAdapter(ModelAdapter):
    provider="none"; model="none"
    def available(self): return False
    def generate_typed_turn(self, **kwargs): raise AssertionError("must not generate")

def test_live_runtime_contains_no_known_phase2_answer_text():
    runtime_text="\n".join(p.read_text() for p in RUNTIME.glob("*.py"))
    phase2=json_load(ROOT/"evals"/"phase2"/"test-d-critiques.json")
    phrases=[]
    for row in phase2.get("turns",phase2 if isinstance(phase2,list) else []):
        text=row.get("text") or row.get("statement",{}).get("text")
        if text: phrases.append(text[:60])
    assert phrases
    assert all(p not in runtime_text for p in phrases)

def json_load(path):
    import json
    return json.loads(path.read_text())

def test_model_adapter_required_no_runtime_is_explicit_block():
    with pytest.raises(ModelRuntimeUnavailable, match="BLOCKED_NO_LIVE_MODEL_RUNTIME"):
        require_live_adapter(MissingAdapter())

def test_generation_module_has_no_gold_access():
    text=(RUNTIME/"generator.py").read_text()+(RUNTIME/"orchestration.py").read_text()
    assert "gold" not in text.lower()
    assert "phase2" not in text.lower()

def test_retrieval_trace_is_inspectable_and_source_bounded():
    agent=PaperAgent.from_json(ROOT/"fixtures"/"benjamin-artwork-v2-agent.json")
    hits,trace=retrieve(agent,"second technology play")
    assert hits
    assert trace["candidate_statement_ids"]
    assert trace["selected_statement_ids"]
    assert all(h.paper_id=="benjamin-artwork-v2" for h in hits)
    assert all(h.edition_id=="benjamin-artwork-v2" for h in hits)

def test_unsupported_generation_blocked():
    turn={"support_ids":["s1"],"actor_paper":"p","actor_edition_id":None,
          "statement_type":"CRITIQUE","action":"CRITIQUE","semantic_support":"UNSUPPORTED"}
    with pytest.raises(Exception):
        publication_gate(turn,{"s1"},actor_paper="p")

def test_partial_support_requires_qualification():
    turn={"support_ids":["s1"],"actor_paper":"p","actor_edition_id":None,
          "statement_type":"CRITIQUE","action":"CRITIQUE","semantic_support":"PARTIALLY_SUPPORTED"}
    with pytest.raises(Exception):
        publication_gate(turn,{"s1"},actor_paper="p")
    turn["qualification"]="Evidence supports only the first clause."
    assert publication_gate(turn,{"s1"},actor_paper="p")

def test_synthesis_cannot_be_author_claim():
    turn={"support_ids":["a","b"],"actor_paper":"synthesis-agent","actor_edition_id":None,
          "statement_type":"AUTHOR_CLAIM","action":"SYNTHESIS","semantic_support":"SEMANTICALLY_SUPPORTED"}
    with pytest.raises(Exception):
        publication_gate(turn,{"a","b"})

def test_research_question_cannot_be_author_claim():
    turn={"support_ids":["a","b"],"actor_paper":"synthesis-agent","actor_edition_id":None,
          "statement_type":"AUTHOR_CLAIM","action":"RESEARCH_QUESTION","semantic_support":"SEMANTICALLY_SUPPORTED"}
    with pytest.raises(Exception):
        publication_gate(turn,{"a","b"})
