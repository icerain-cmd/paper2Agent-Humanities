#!/usr/bin/env python3
"""Validate the committed Lee PoC fixture against a real reviewed Paper2Skill work dir."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper2humanities import PaperAgent, PaperEvidenceIndex, evaluate_agent, validate_against_source
from paper2humanities.schema import StatementType


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True, help="Reviewed Paper2Skill work directory")
    args = parser.parse_args()
    fixtures = ROOT / "fixtures"
    agent = PaperAgent.from_json(fixtures / "lee-aura-2019-agent.json")
    index = PaperEvidenceIndex.from_paper2skill_work(args.work, agent.paper_id, agent.source_id)
    if index.source_sha256 != agent.source_sha256:
        raise SystemExit("source SHA-256 does not match the committed Lee Paper Agent fixture")
    for statement in agent.store.values():
        if statement.statement_type in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}:
            validate_against_source(statement, index)
    report = evaluate_agent(agent, index)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["unsupported_author_claim"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
