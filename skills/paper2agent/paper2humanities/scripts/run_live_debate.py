#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from paper2humanities.debate import AgentRegistry, DebateEngine
from paper2humanities.runtime.model_adapter import CodexExecAdapter

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--json-out", type=Path)
    args=ap.parse_args()
    reg=AgentRegistry(ROOT/"fixtures")
    codex=shutil.which("codex") or str(Path.home()/".local/bin/codex")
    engine=DebateEngine(reg,CodexExecAdapter(model=args.model, executable=codex))
    session=engine.create_session(args.agents,args.topic,args.turns)
    def show(turn,session):
        print(f"\n[{session.current_turn}/{session.max_turns}] {turn.speaker_agent_id} · {turn.action.value}")
        print(turn.text)
        if turn.support_ids:
            print("  evidence:", ", ".join(f"{sid}@p{page}" for sid,page in zip(turn.support_ids,turn.pages)))
        else:
            print("  evidence: ABSTAIN")
    engine.run(session,on_turn=show)
    if args.json_out:
        args.json_out.write_text(json.dumps(session.to_dict(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"\nSTATUS={session.status}; TURNS={len(session.turns)}")

if __name__=="__main__":
    main()
