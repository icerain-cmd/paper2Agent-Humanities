#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from paper2humanities.runtime.model_adapter import CodexExecAdapter, ModelRuntimeUnavailable

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="gpt-6-sol")
    ap.add_argument("--output")
    args=ap.parse_args()
    adapter=CodexExecAdapter(args.model)
    try:
        result=adapter.generate_typed_turn(system_contract="Return UNRESOLVED with no evidence, UNKNOWN voice, empty support_ids and pages, null evidence_span, relation_type UNRESOLVED, action SOURCE_RETRIEVAL, semantic_support UNSUPPORTED, actor_paper lee-aura-2019 and null actor_edition_id.",payload={"research_question":"No evidence is supplied.","evidence":[]})
        available=True; error=None
    except (ModelRuntimeUnavailable, ValueError) as exc:
        available=False; error=f"{type(exc).__name__}: {exc}"
    data={"PC2_RUNTIME":"PASS" if available else "BLOCKED", "RUNTIME_KIND":"CODEX_EXEC",
          "GENERATOR_MODEL":args.model,"REAL_MODEL_SMOKE":"PASS" if available else "BLOCKED",
          "CODEX_EXEC_ADAPTER":"PASS" if adapter.available() else "UNAVAILABLE",
          "phase3_runtime_model":"PASS" if available else "BLOCKED_NO_LIVE_MODEL_RUNTIME",
          "error":error,"credentials_discovered_or_scraped":False}
    if args.output: Path(args.output).write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data))
    return 0 if available else 2
if __name__=="__main__": raise SystemExit(main())
