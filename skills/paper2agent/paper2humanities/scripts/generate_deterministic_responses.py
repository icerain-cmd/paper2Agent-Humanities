#!/usr/bin/env python3
"""Generate behavioral responses from query-only panel + reviewed source.

This process never receives a gold path and never loads evaluation gold.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper2humanities.live_eval import generate_responses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    queries = json.loads(Path(args.queries).read_text())
    source = json.loads(Path(args.source).read_text())
    agent = json.loads(Path(args.agent).read_text())
    if agent["source"]["source_id"] != source["source_id"] or agent["source"]["sha256"] != source["source_sha256"]:
        raise SystemExit("Paper Agent source identity does not match reviewed runtime source")
    output = generate_responses(queries, source)
    output["paper_id"] = agent["paper_id"]
    output["agent_source_sha256"] = agent["source"]["sha256"]
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"responses": len(output["responses"]), "generation_method": output["generation_method"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
