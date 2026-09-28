#!/usr/bin/env python3
"""Run a gold-isolated deterministic behavioral evaluation.

Response generation receives only the query panel and reviewed source snapshot.
Gold is opened only after the response artifact has been frozen and hashed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper2humanities import PaperEvidenceIndex
from paper2humanities.blind_eval import score_panel, validate_gold_panel
from paper2humanities.live_eval import build_runtime_source, sha256_file


def digest(path: Path) -> str:
    return sha256_file(path)


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True)
    parser.add_argument("--queries", default=str(ROOT / "evals" / "lee-aura-2019-blind-panel.json"))
    parser.add_argument("--gold", default=str(ROOT / "evals" / "lee-aura-2019-adversarial-panel.json"))
    parser.add_argument("--agent", default=str(ROOT / "fixtures" / "lee-aura-2019-agent.json"))
    parser.add_argument("--run-root", default=str(ROOT / "evals" / "live_runs"))
    args = parser.parse_args()

    work = Path(args.work).resolve()
    query_path = Path(args.queries).resolve()
    gold_path = Path(args.gold).resolve()
    agent_path = Path(args.agent).resolve()
    repo = ROOT.parents[2]

    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    run_id = timestamp.strftime("lee-aura-live-%Y%m%dT%H%M%SZ")
    run_dir = Path(args.run_root).resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory(prefix="p2h-live-runtime-") as temp_name:
        runtime = Path(temp_name)
        (runtime / "source").mkdir()
        (runtime / "agent").mkdir()
        (runtime / "output").mkdir()

        query_copy = runtime / "query-panel.json"
        agent_copy = runtime / "agent" / "paper-agent.json"
        source_copy = runtime / "source" / "reviewed-source.json"
        response_temp = runtime / "output" / "responses.json"
        shutil.copy2(query_path, query_copy)
        shutil.copy2(agent_path, agent_copy)
        source_payload = build_runtime_source(work, source_copy)

        generator = ROOT / "scripts" / "generate_deterministic_responses.py"
        command = [
            sys.executable, "-I", str(generator),
            "--queries", str(query_copy),
            "--source", str(source_copy),
            "--agent", str(agent_copy),
            "--output", str(response_temp),
        ]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            "P2H_GOLD_AVAILABLE_DURING_RESPONSE_GENERATION": "false",
        }
        completed = subprocess.run(
            command, cwd=runtime, env=env, text=True,
            capture_output=True, check=True,
        )

        # Freeze before gold is opened.
        response_copy = run_dir / "responses.json"
        shutil.copy2(response_temp, response_copy)
        response_sha = digest(response_copy)

        runtime_manifest = {
            "run_id": run_id,
            "timestamp": timestamp.isoformat(),
            "git_commit": git_value(repo, "rev-parse", "HEAD"),
            "query_panel_sha256": digest(query_copy),
            "source_sha256": source_payload["source_sha256"],
            "agent_artifact_sha256": digest(agent_copy),
            "response_artifact_sha256": response_sha,
            "runtime": f"python {sys.version.split()[0]}",
            "model_or_host_agent": "none — deterministic provenance classifier v1",
            "live_eval_mode": "DETERMINISTIC_BEHAVIORAL_EVAL",
            "gold_available_during_response_generation": False,
            "external_blind": False,
            "generation_method": "query-only + reviewed source lexical retrieval/conservative classification",
            "generator_command_argv": command,
            "generator_stdout": completed.stdout.strip(),
            "gold_unsealed_after_response_sha256": True,
        }
        (run_dir / "manifest.json").write_text(
            json.dumps(runtime_manifest, ensure_ascii=False, indent=2) + "\n"
        )

    # Gold unseal: only after frozen response exists and manifest has recorded false.
    gold = json.loads(gold_path.read_text())
    responses = json.loads((run_dir / "responses.json").read_text())
    index = PaperEvidenceIndex.from_paper2skill_work(work, gold["paper_id"])
    validate_gold_panel(gold, index)
    score = score_panel(gold, responses, evaluation_scope="LIVE_BLIND_RUN")
    score["run_id"] = run_id
    score["response_artifact_sha256"] = response_sha
    (run_dir / "score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"run_dir": str(run_dir), **score}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
