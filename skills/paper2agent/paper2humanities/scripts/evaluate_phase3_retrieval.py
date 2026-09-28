#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from paper2humanities import PaperAgent
from paper2humanities.runtime.retrieval import retrieve

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--panel",default=str(ROOT/"evals"/"lee-aura-2019-adversarial-panel.json"))
    ap.add_argument("--agent",default=str(ROOT/"fixtures"/"lee-aura-2019-agent.json"))
    ap.add_argument("--output")
    args=ap.parse_args()
    gold=json.loads(Path(args.panel).read_text())
    agent=PaperAgent.from_json(args.agent)
    grounded=[r for r in gold["records"] if r["expected_page"] is not None]
    hit=0; traces=[]
    for row in grounded:
        hits,trace=retrieve(agent,row["query"],limit=6)
        pages={h.page for h in hits}
        ok=row["expected_page"] in pages
        hit+=int(ok)
        traces.append({"query_id":row["query_id"],"expected_page":row["expected_page"],"page_recall_hit":ok,**trace})
    report={"evaluation_scope":"FROZEN_REGRESSION50_RETRIEVAL","grounded_queries":len(grounded),
            "page_retrieval_recall_at_6":hit/len(grounded) if grounded else 1.0,"traces":traces}
    if args.output: Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="traces"},ensure_ascii=False))
if __name__=="__main__": main()
