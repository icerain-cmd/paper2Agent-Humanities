#!/usr/bin/env python3
"""Validate and score the Lee blind/adversarial evaluation panel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper2humanities import PaperEvidenceIndex
from paper2humanities.blind_eval import score_panel, validate_gold_panel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True)
    parser.add_argument("--gold", default=str(ROOT / "evals" / "lee-aura-2019-adversarial-panel.json"))
    parser.add_argument("--responses", default=str(ROOT / "evals" / "lee-aura-2019-behavioral-responses.json"))
    parser.add_argument("--report", default=str(ROOT / "evals" / "lee-aura-2019-evaluation-report.json"))
    args = parser.parse_args()

    gold = json.loads(Path(args.gold).read_text())
    responses = json.loads(Path(args.responses).read_text())
    index = PaperEvidenceIndex.from_paper2skill_work(args.work, gold["paper_id"])
    if index.source_sha256 != gold["source_sha256"]:
        raise SystemExit("source SHA-256 does not match gold panel")

    gold_report = validate_gold_panel(gold, index)
    report = score_panel(gold, responses)
    report["gold_review"] = gold_report
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    gates = report["hard_gates"]
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
