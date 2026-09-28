#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from paper2humanities.runtime.model_adapter import OpenAICompatibleAdapter, ModelRuntimeUnavailable, require_live_adapter

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-url",default="")
    ap.add_argument("--model",default="")
    ap.add_argument("--api-key-env")
    ap.add_argument("--output")
    args=ap.parse_args()
    adapter=OpenAICompatibleAdapter(args.base_url,args.model,args.api_key_env)
    available=adapter.available()
    data={"phase3_runtime_model":"PASS" if available else "BLOCKED_NO_LIVE_MODEL_RUNTIME",
          "provider":adapter.provider if available else None,"model":args.model or None,
          "credentials_discovered_or_scraped":False}
    if args.output: Path(args.output).write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data))
    return 0 if available else 2
if __name__=="__main__": raise SystemExit(main())
