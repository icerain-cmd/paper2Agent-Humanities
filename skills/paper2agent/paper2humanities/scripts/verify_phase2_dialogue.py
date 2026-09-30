#!/usr/bin/env python3
"""Verify Phase-2 dialogue hard gates against reviewed source agents and D/E/F artifacts."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from paper2humanities import (
    PaperAgent, PaperEvidenceIndex, SourceEdition, StatementType, validate_against_source,
    review_binding_sha256,
)

LATER_LEE_TERMS=["아투라","기계세","Mechanocene","기술생성시대","공진주체 WE","마찰의 투명성","생성 아우라"]

def load(p): return json.loads(Path(p).read_text())

def build_index(agent, work):
    if agent.edition_id:
        data=load(ROOT/"evals"/"benjamin-source-verification.json")
        src=next(x for x in data["sources"] if x["edition_id"]==agent.edition_id)
        year=1989 if agent.edition_id.endswith("v2") else 1980
        edition=SourceEdition(
            work_id=src["work_id"],edition_id=src["edition_id"],version_label=src["version_label"],
            source_language=src["source_language"],publication_year=year,canonical_source=src["canonical_source"]
        )
        return PaperEvidenceIndex.from_paper2skill_work(work,agent.paper_id,agent.source_id,edition=edition)
    return PaperEvidenceIndex.from_paper2skill_work(work,agent.paper_id,agent.source_id)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--lee-work",required=True)
    ap.add_argument("--v2-work",required=True)
    ap.add_argument("--v3-work",required=True)
    ap.add_argument("--eval-dir",default=str(ROOT/"evals"/"phase2"))
    ap.add_argument("--output",default=str(ROOT/"evals"/"phase2"/"phase2-dialogue-verification.json"))
    args=ap.parse_args()

    lee=PaperAgent.from_json(ROOT/"fixtures"/"lee-aura-2019-phase2-agent.json")
    v2=PaperAgent.from_json(ROOT/"fixtures"/"benjamin-artwork-v2-agent.json")
    v3=PaperAgent.from_json(ROOT/"fixtures"/"benjamin-artwork-v3-agent.json")
    agents={a.paper_id:a for a in [lee,v2,v3]}
    indexes={
        lee.paper_id:build_index(lee,args.lee_work),
        v2.paper_id:build_index(v2,args.v2_work),
        v3.paper_id:build_index(v3,args.v3_work),
    }

    fake_page=0
    for agent in agents.values():
        idx=indexes[agent.paper_id]
        if idx.source_sha256!=agent.source_sha256: raise SystemExit(f"hash mismatch {agent.paper_id}")
        for st in agent.store.values():
            if st.statement_type in {StatementType.AUTHOR_CLAIM,StatementType.SOURCE_QUOTE}:
                try: validate_against_source(st,idx)
                except Exception:
                    fake_page+=1

    eval_dir=Path(args.eval_dir)
    d=load(eval_dir/"test-d-critiques.json")
    e=load(eval_dir/"test-e-lee-responses.json")
    f=load(eval_dir/"test-f-synthesis.json")
    semantic=load(eval_dir/"phase2-semantic-review.json")
    semantic_by={x["turn_id"]:x for x in semantic["reviews"]}

    source_statements={}
    for a in agents.values():
        source_statements.update({s.statement_id:s for s in a.store.values()})

    false_author=external_as_author=cross_edition=unsupported=temporal=0
    stale_review=0
    d_ids={x["turn_id"] for x in d["turns"]}
    e_ids={x["turn_id"] for x in e["turns"]}

    for t in d["turns"]:
        actor=agents[t["actor_paper"]]
        for sid in t["support_ids"]:
            st=source_statements.get(sid)
            if st is None:
                unsupported+=1
                continue
            if st.paper_id!=actor.paper_id or st.source_id!=actor.source_id or st.edition_id!=actor.edition_id:
                cross_edition+=1
            if st.statement_type not in {StatementType.AUTHOR_CLAIM,StatementType.SOURCE_QUOTE}: unsupported+=1
            if st.evidence_voice and st.evidence_voice.value=="EXTERNAL" and st.statement_type==StatementType.AUTHOR_CLAIM:
                external_as_author+=1
        if t["target_statement_id"] not in source_statements: unsupported+=1
        if t["statement_type"]=="AUTHOR_CLAIM": false_author+=1
        rv=semantic_by.get(t["turn_id"])
        if not rv or rv["semantic_support"] in {"OVERSTATED","UNSUPPORTED"} or rv["review_status"]!="REVIEWED":
            unsupported+=1
        if not rv or rv.get("review_binding_sha256")!=review_binding_sha256(t): stale_review+=1

    for t in e["turns"]:
        if t["target_turn_id"] not in d_ids: unsupported+=1
        for sid in t["support_ids"]:
            st=source_statements.get(sid)
            if st is None:
                unsupported+=1
                continue
            actor=agents[t["actor_paper"]]
            if st.paper_id!=actor.paper_id or st.source_id!=actor.source_id or st.edition_id!=actor.edition_id:
                cross_edition+=1
        if t["statement_type"]=="AUTHOR_CLAIM": false_author+=1
        if any(term.lower() in t["text"].lower() for term in LATER_LEE_TERMS): temporal+=1
        rv=semantic_by.get(t["turn_id"])
        if not rv or rv["semantic_support"] in {"OVERSTATED","UNSUPPORTED"} or rv["review_status"]!="REVIEWED":
            unsupported+=1
        if not rv or rv.get("review_binding_sha256")!=review_binding_sha256(t): stale_review+=1

    synthesis_items=f["issues"]+f["research_gaps"]+f["research_questions"]
    all_turn_ids=d_ids|e_ids|{x["turn_id"] for x in synthesis_items}
    for t in synthesis_items:
        if t["statement_type"] not in {"AI_SYNTHESIS","UNRESOLVED"}: false_author+=1
        if not all(sid in all_turn_ids or sid in source_statements for sid in t["support_ids"]): unsupported+=1
        rv=semantic_by.get(t["turn_id"])
        if not rv or rv["semantic_support"] in {"OVERSTATED","UNSUPPORTED"} or rv["review_status"]!="REVIEWED":
            unsupported+=1
        if not rv or rv.get("review_binding_sha256")!=review_binding_sha256(t): stale_review+=1
    for q in f["research_questions"]:
        if q["statement_type"]!="UNRESOLVED" or q.get("human_review_status")!="REVIEWED":
            unsupported+=1
        for key in ["novelty_basis","source_gap"]:
            if not q.get(key): unsupported+=1

    result={
        "TEST_D":"PASS" if len(d["turns"])>=6 and d["v2_count"]>=3 and d["v3_count"]>=3 else "FAIL",
        "DIALOGUE_CRITIQUES":len(d["turns"]),
        "TEST_E":"PASS" if len(e["turns"])==len(d["turns"]) else "FAIL",
        "LEE_SUPPORTED_RESPONSES":sum(x.get("response_status")=="SUPPORTED_RESPONSE" for x in e["turns"]),
        "LEE_PARTIAL_RESPONSES":sum(x.get("response_status")=="PARTIAL_RESPONSE" for x in e["turns"]),
        "LEE_NO_SOURCE_RESPONSES":sum(x.get("response_status")=="NO_SOURCE_SUPPORTED_RESPONSE" for x in e["turns"]),
        "TEST_F":"PASS" if len(f["issues"])>=3 and len(f["research_gaps"])>=3 and len(f["research_questions"])>=3 else "FAIL",
        "CROSS_PAPER_ISSUES":len(f["issues"]),
        "RESEARCH_GAPS":len(f["research_gaps"]),
        "RESEARCH_QUESTIONS":len(f["research_questions"]),
        "FALSE_AUTHOR_CLAIM":false_author,
        "EXTERNAL_AS_AUTHOR_ERROR":external_as_author,
        "CROSS_EDITION_CONTAMINATION":cross_edition,
        "UNSUPPORTED_DIALOGUE_TURN":unsupported,
        "TEMPORAL_CORPUS_CONTAMINATION":temporal,
        "FAKE_PAGE_CITATION":fake_page,
        "SEMANTIC_REVIEW":semantic["status"],
        "SEMANTIC_REVIEW_STALE":stale_review,
        "hard_gates":{
            "FALSE_AUTHOR_CLAIM":false_author==0,
            "EXTERNAL_AS_AUTHOR_ERROR":external_as_author==0,
            "CROSS_EDITION_CONTAMINATION":cross_edition==0,
            "UNSUPPORTED_DIALOGUE_TURN":unsupported==0,
            "TEMPORAL_CORPUS_CONTAMINATION":temporal==0,
            "FAKE_PAGE_CITATION":fake_page==0,
            "SEMANTIC_REVIEW_STALE":stale_review==0,
        }
    }
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if all(result["hard_gates"].values()) and all(result[x]=="PASS" for x in ["TEST_D","TEST_E","TEST_F"]) else 1

if __name__=="__main__": raise SystemExit(main())
