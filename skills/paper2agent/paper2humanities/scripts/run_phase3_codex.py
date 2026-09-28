#!/usr/bin/env python3
"""Live Phase 3 generation and separately gated scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paper2humanities import PaperAgent
from paper2humanities.blind_eval import score_panel
from paper2humanities.runtime.model_adapter import (
    CodexExecAdapter, GenerationFormatFailure, ModelRuntimeUnavailable,
    validate_typed_turn,
)
from paper2humanities.runtime.orchestration import live_turn
from paper2humanities.runtime.verifier import publication_gate

GENERATOR_MODEL = "gpt-6-sol"
VERIFIER_MODEL = "gpt-5.6-sol"
FIXTURES = ROOT / "fixtures"
AGENTS = {name: PaperAgent.from_json(FIXTURES / f"{name}-agent.json") for name in
          ("benjamin-artwork-v2", "benjamin-artwork-v3", "lee-aura-2019")}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def agent_for(query: str, default: str = "lee-aura-2019", paper_id: str | None = None) -> PaperAgent:
    if paper_id:
        if paper_id not in AGENTS:
            raise ValueError(f"unknown paper_id in query panel: {paper_id}")
        return AGENTS[paper_id]
    low = query.lower()
    if "v2" in low or "zweite fassung" in low or "제2판" in low:
        return AGENTS["benjamin-artwork-v2"]
    if "v3" in low or "dritte fassung" in low or "제3판" in low:
        return AGENTS["benjamin-artwork-v3"]
    return AGENTS[default]


def turn_errors(turn: dict, agent: PaperAgent, selected: set[str], action: str) -> list[str]:
    errors = []
    try:
        validate_typed_turn(turn)
    except GenerationFormatFailure as exc:
        return [f"FORMAT: {exc}"]
    evidence = {s.statement_id: s for s in agent.store.values()}
    supports = turn["support_ids"]
    abstained = turn["statement_type"] == "UNRESOLVED"
    if turn["actor_paper"] != agent.paper_id or turn["actor_edition_id"] != agent.edition_id:
        errors.append("ACTOR_EDITION_MISMATCH")
    if turn["action"] != action:
        errors.append("ACTION_MISMATCH")
    if action in {"ISSUE", "RESEARCH_GAP", "RESEARCH_QUESTION", "SYNTHESIS"} and turn["statement_type"] not in {"AI_SYNTHESIS", "UNRESOLVED"}:
        errors.append("ACTION_STATEMENT_TYPE_MISMATCH")
    if action == "CRITIQUE" and turn["statement_type"] not in {"CRITIQUE", "UNRESOLVED"}:
        errors.append("ACTION_STATEMENT_TYPE_MISMATCH")
    if action == "RESPONSE" and turn["statement_type"] not in {"INTERPRETATION", "AI_SYNTHESIS", "UNRESOLVED"}:
        errors.append("ACTION_STATEMENT_TYPE_MISMATCH")
    if abstained:
        if supports or turn["pages"] or turn["evidence_span"] is not None or turn["evidence_voice"] != "UNKNOWN" or turn["semantic_support"] != "UNSUPPORTED" or turn["relation_type"] != "UNRESOLVED":
            errors.append("INVALID_ABSTENTION")
    else:
        if not supports or not turn["pages"] or not turn["evidence_span"]:
            errors.append("UNSUPPORTED_DIALOGUE_TURN")
        if len(supports) != len(set(supports)) or not set(supports) <= selected:
            errors.append("UNSELECTED_SUPPORT_ID")
        for sid in supports:
            source = evidence.get(sid)
            if source is None:
                errors.append("UNKNOWN_SUPPORT_ID")
            elif source.paper_id != agent.paper_id or source.edition_id != agent.edition_id:
                errors.append("CROSS_EDITION_CONTAMINATION")
        known = [evidence[sid] for sid in supports if sid in evidence]
        if set(turn["pages"]) != {s.page for s in known}:
            errors.append("FAKE_PAGE_CITATION")
        span_sources = [s for s in known if s.evidence_span == turn["evidence_span"]]
        if not span_sources:
            errors.append("EVIDENCE_SPAN_MISMATCH")
        elif turn["evidence_voice"] not in {(s.evidence_voice.value if s.evidence_voice else "UNKNOWN") for s in span_sources}:
            errors.append("EVIDENCE_VOICE_MISMATCH")
        try:
            publication_gate(turn, selected, agent.paper_id, agent.edition_id)
        except Exception as exc:
            errors.append(f"PUBLICATION_GATE: {exc}")
    try:
        agent.validate_output_text(turn["text"])
    except ValueError as exc:
        errors.append(f"TEMPORAL_CORPUS_CONTAMINATION: {exc}")
    return errors


def run_one(adapter: CodexExecAdapter, agent: PaperAgent, query: str, action: str,
            target: dict | None = None, history: list[dict] | None = None,
            verifier_model: str = VERIFIER_MODEL) -> dict:
    if adapter.model == verifier_model:
        raise ValueError("verifier model must differ from generator model")
    try:
        turn, trace, result = live_turn(adapter, agent, query, action, target or {}, history)
    except (GenerationFormatFailure, ModelRuntimeUnavailable) as exc:
        return {"outcome": getattr(exc, "outcome", "MODEL_RUNTIME_UNAVAILABLE"),
                "error": str(exc), "generator_subprocess_attempts": exc.attempts,
                "verifier_subprocess_attempts": 0}
    selected = set(trace["selected_statement_ids"])
    errors = turn_errors(turn, agent, selected, action)
    evidence = {s.statement_id: s for s in agent.store.values()}
    verifier_packet = {"candidate_turn": turn,
                       "evidence": [evidence[sid].to_dict() for sid in sorted(selected)]}
    verifier_attempts = 0
    try:
        verifier_result = CodexExecAdapter(verifier_model).generate_typed_turn(
            system_contract="Independently check the candidate against only the supplied evidence. Return every candidate field unchanged if valid. Otherwise return an UNRESOLVED turn with empty support_ids and pages, UNKNOWN voice, null evidence_span, UNSUPPORTED semantic_support, and UNRESOLVED relation_type. No external knowledge or dialogue history.",
            payload=verifier_packet)
        verifier_attempts = verifier_result.parameters["attempts"]
        verified = json.loads(verifier_result.text)
        if verified != turn:
            errors.append("VERIFIER_DISAGREEMENT")
    except (GenerationFormatFailure, ModelRuntimeUnavailable, ValueError) as exc:
        verifier_attempts = getattr(exc, "attempts", 0)
        errors.append(f"VERIFIER_FAILURE: {exc}")
    abstained = turn["statement_type"] == "UNRESOLVED"
    return {"outcome": "REJECTED" if errors else "ABSTAINED" if abstained else "ACCEPTED",
            "turn": turn, "gate_errors": errors, "retrieval_trace": trace,
            "model": result.model, "provider": result.provider, "prompt_sha256": result.prompt_sha256,
            "verifier_model": verifier_model, "fresh_context_verifier": True,
            "independent_model_verifier": result.model != verifier_model,
            "generator_subprocess_attempts": result.parameters["attempts"],
            "verifier_subprocess_attempts": verifier_attempts}


def attempts_summary(rows: list[dict]) -> dict:
    return {"generator_subprocess_attempts": sum(r.get("generator_subprocess_attempts", 0) for r in rows),
            "verifier_subprocess_attempts": sum(r.get("verifier_subprocess_attempts", 0) for r in rows)}


def generate_panel(panel_path: Path, output: Path, model: str = GENERATOR_MODEL,
                   verifier_model: str = VERIFIER_MODEL) -> None:
    if model == verifier_model:
        raise ValueError("verifier model must differ from generator model")
    panel = json.loads(panel_path.read_text())
    panel_type = panel.get("panel_type")
    query_only = isinstance(panel.get("queries"), list) and "records" not in panel
    if not query_only or panel_type not in {"HOLDOUT30_QUERY_ONLY", "HOLDOUT30_V2_QUERY_ONLY",
                                             "DEV50_QUERY_ONLY", "QUERY_ONLY",
                                             "BLIND_ADVERSARIAL_PANEL"}:
        raise ValueError("generation requires a recognized query-only panel")
    adapter = CodexExecAdapter(model)
    rows = []
    for row in panel["queries"]:
        agent = agent_for(row["query"], paper_id=row.get("paper_id"))
        rows.append({"query_id": row["query_id"],
                     **run_one(adapter, agent, row["query"], "SOURCE_RETRIEVAL", verifier_model=verifier_model)})
    write_json(output, {"panel_id": panel["panel_id"], "responses": rows,
                        "generator_model": model, "verifier_model": verifier_model,
                        **attempts_summary(rows)})
    manifest = {"query_sha256": sha(panel_path), "response_sha256": sha(output),
                "generator_model": model, "verifier_model": verifier_model,
                "gold_available_during_generation": False, "response_frozen": True,
                **attempts_summary(rows)}
    write_json(output.with_name("manifest.json"), manifest)


def generate_dialogue(output: Path, model: str = GENERATOR_MODEL,
                      verifier_model: str = VERIFIER_MODEL) -> None:
    if model == verifier_model:
        raise ValueError("verifier model must differ from generator model")
    adapter = CodexExecAdapter(model)
    rows: list[dict] = []
    history: list[dict] = []
    phrasings = ("Examine the supplied evidence for {topic} and {goal}.",
                 "Using only retrieved passages about {topic}, {goal}.",
                 "Assess {topic} from this paper's evidence; {goal}.",
                 "For {topic}, {goal} using a specific supplied passage.",
                 "Identify a bounded relation concerning {topic}; {goal}.",
                 "Use the retrieved source claims on {topic} to {goal}.")

    def seek(test: str, agent: PaperAgent, action: str, topic: str, goal: str,
             target: dict | None = None, context: list[dict] | None = None,
             limit: int = 6, **labels) -> dict | None:
        for attempt in range(1, limit + 1):
            query = phrasings[(attempt - 1) % len(phrasings)].format(topic=topic, goal=goal)
            result = run_one(adapter, agent, query, action, target, context, verifier_model)
            result.update({"test": test, "subtype": action if test == "F" else None,
                           "step": labels.get("step"), "edition": agent.edition_id,
                           "attempt": attempt, "topic": topic, **{k: v for k, v in labels.items() if k != "step"}})
            rows.append(result)
            if result["outcome"] == "ACCEPTED":
                return result
        return None

    # Three accepted critiques from each edition; each accepted D gets one accepted E.
    for edition in ("benjamin-artwork-v2", "benjamin-artwork-v3"):
        agent = AGENTS[edition]
        for index, topic in enumerate(("technology and nature", "aura and reproducibility", "film reception and distraction"), 1):
            critique = seek("D", agent, "CRITIQUE", topic, "critique Lee 2019", {"paper_id": "lee-aura-2019"},
                            limit=6, pair_id=f"{edition}-{index}")
            if critique is None:
                continue
            history.append(critique["turn"])
            response = seek("E", AGENTS["lee-aura-2019"], "RESPONSE", topic,
                            "respond to the supplied Benjamin critique", {"paper_id": edition},
                            [critique["turn"]], limit=6, pair_id=f"{edition}-{index}")
            if response:
                history.append(response["turn"])

    for action, label in (("ISSUE", "ISSUE"), ("RESEARCH_GAP", "GAP"),
                          ("RESEARCH_QUESTION", "RESEARCH_QUESTION")):
        accepted = 0
        for attempt in range(1, 13):
            if accepted >= 3:
                break
            name = ("benjamin-artwork-v2", "benjamin-artwork-v3", "lee-aura-2019")[(attempt - 1) % 3]
            topic = ("technology and nature", "aura and reproducibility", "film reception and distraction")[(attempt - 1) % 3]
            query = phrasings[(attempt - 1) % len(phrasings)].format(topic=topic, goal=f"identify one {label.lower().replace('_', ' ')}")
            result = run_one(adapter, AGENTS[name], query, action, {}, history[-4:], verifier_model)
            result.update({"test": "F", "subtype": label, "step": accepted + 1,
                           "edition": AGENTS[name].edition_id, "attempt": attempt, "topic": topic})
            rows.append(result)
            if result["outcome"] == "ACCEPTED":
                accepted += 1
                history.append(result["turn"])

    multi_history: list[dict] = []
    sequence = (("benjamin-artwork-v2", "CRITIQUE"), ("lee-aura-2019", "RESPONSE"),
                ("benjamin-artwork-v3", "CRITIQUE"), ("lee-aura-2019", "RESPONSE"),
                ("lee-aura-2019", "SYNTHESIS"))
    for step, (name, action) in enumerate(sequence, 1):
        prior = multi_history[-4:]
        result = seek("MULTITURN", AGENTS[name], action, "technology art and aura",
                      "continue the evidence-bounded dialogue" if step < 5 else "synthesize and state unresolved questions",
                      context=prior, limit=6, step=step)
        if result is None:
            break
        multi_history.append(result["turn"])

    counts = {test: sum(r["outcome"] == "ACCEPTED" for r in rows if r["test"] == test)
              for test in ("D", "E", "MULTITURN")}
    f_counts = {subtype: sum(r["outcome"] == "ACCEPTED" for r in rows if r["test"] == "F" and r["subtype"] == subtype)
                for subtype in ("ISSUE", "GAP", "RESEARCH_QUESTION")}
    d_by_edition = {edition: sum(r["outcome"] == "ACCEPTED" for r in rows if r["test"] == "D" and r["edition"] == edition)
                    for edition in ("benjamin-artwork-v2", "benjamin-artwork-v3")}
    complete = all(n >= 3 for n in d_by_edition.values()) and counts["E"] == counts["D"] and all(n >= 3 for n in f_counts.values()) and counts["MULTITURN"] == 5
    write_json(output, {"generator_model": model, "verifier_model": verifier_model,
                        "independent_model_verifier": model != verifier_model,
                        "fresh_context_verifier": True, "runs": rows,
                        "accepted": {**counts, "D_by_edition": d_by_edition, "F_by_subtype": f_counts},
                        "status": "PASS" if complete else "INCOMPLETE", **attempts_summary(rows)})


def frozen_response(response_path: Path) -> tuple[dict, dict]:
    manifest = json.loads(response_path.with_name("manifest.json").read_text())
    if manifest.get("response_sha256") != sha(response_path) or manifest.get("response_frozen") is not True:
        raise ValueError("response freeze hash mismatch")
    return manifest, json.loads(response_path.read_text())


def score_dev(gold_path: Path, response_path: Path, output: Path) -> None:
    manifest, raw = frozen_response(response_path)
    gold = json.loads(gold_path.read_text())
    responses = []
    for row in raw["responses"]:
        turn = (row.get("turn") or {}) if row.get("outcome") in {"ACCEPTED", "ABSTAINED"} else {}
        responses.append({"query_id": row["query_id"], "predicted_type": turn.get("statement_type", "UNRESOLVED"),
                          "predicted_voice": turn.get("evidence_voice", "UNKNOWN"),
                          "page": (turn.get("pages") or [None])[0], "evidence_span": turn.get("evidence_span"),
                          "predicted_edition_id": turn.get("actor_edition_id")})
    score = score_panel(gold, {"responses": responses}, evaluation_scope="DEV50_LIVE")
    score["response_sha256"] = manifest["response_sha256"]
    write_json(output, score)


def score_holdout(gold_path: Path, response_path: Path, output: Path) -> None:
    manifest, raw = frozen_response(response_path)
    gold = json.loads(gold_path.read_text())
    records = gold["records"]
    response_list = raw["responses"]
    by_id = {r["query_id"]: r for r in response_list}
    if len(by_id) != len(response_list) or set(by_id) != {r["query_id"] for r in records}:
        raise ValueError("gold and response IDs differ")
    gates = {key: 0 for key in ("FALSE_AUTHOR_CLAIM", "EXTERNAL_AS_AUTHOR_ERROR",
             "CROSS_EDITION_CONTAMINATION", "UNSUPPORTED_DIALOGUE_TURN",
             "TEMPORAL_CORPUS_CONTAMINATION", "FAKE_PAGE_CITATION", "HARDCODED_DIALOGUE_TEXT", "GOLD_LEAKAGE")}
    if manifest.get("gold_available_during_generation") is not False:
        gates["GOLD_LEAKAGE"] += 1
    rows = []
    for rec in records:
        response = by_id[rec["query_id"]]
        turn = response.get("turn") or {}
        accepted = response.get("outcome") == "ACCEPTED"
        errors = list(response.get("gate_errors") or [])
        if accepted:
            actor = AGENTS.get(turn.get("actor_paper"))
            if actor is None:
                errors.append("CROSS_EDITION_CONTAMINATION")
            else:
                selected = set((response.get("retrieval_trace") or {}).get("selected_statement_ids") or [])
                errors.extend(turn_errors(turn, actor, selected, "SOURCE_RETRIEVAL"))
            if response.get("verifier_model") == response.get("model") or response.get("fresh_context_verifier") is not True:
                errors.append("VERIFIER_DISAGREEMENT")
        row_gates = set()
        for key in ("CROSS_EDITION_CONTAMINATION", "UNSUPPORTED_DIALOGUE_TURN",
                    "TEMPORAL_CORPUS_CONTAMINATION", "FAKE_PAGE_CITATION", "HARDCODED_DIALOGUE_TEXT", "GOLD_LEAKAGE"):
            if any(key in error for error in errors):
                row_gates.add(key)
        if any(token in error for error in errors for token in ("UNSELECTED_SUPPORT_ID", "UNKNOWN_SUPPORT_ID", "EVIDENCE_SPAN_MISMATCH", "EVIDENCE_VOICE_MISMATCH", "PUBLICATION_GATE", "VERIFIER_DISAGREEMENT")):
            row_gates.add("UNSUPPORTED_DIALOGUE_TURN")
        if accepted and turn.get("statement_type") == "AUTHOR_CLAIM" and rec["type"] != "AUTHOR_CLAIM":
            row_gates.add("FALSE_AUTHOR_CLAIM")
        if accepted and turn.get("statement_type") == "AUTHOR_CLAIM" and turn.get("evidence_voice") == "EXTERNAL":
            row_gates.add("EXTERNAL_AS_AUTHOR_ERROR")
        if accepted and rec.get("paper") is not None and turn.get("actor_paper") != rec["paper"]:
            row_gates.add("CROSS_EDITION_CONTAMINATION")
        if accepted and rec.get("edition") is not None and turn.get("actor_edition_id") != rec["edition"]:
            row_gates.add("CROSS_EDITION_CONTAMINATION")
        if accepted and rec.get("support") and not set(turn.get("support_ids", [])) & set(rec["support"]):
            row_gates.add("UNSUPPORTED_DIALOGUE_TURN")
        if accepted and rec.get("page") is not None and rec["page"] not in turn.get("pages", []):
            row_gates.add("FAKE_PAGE_CITATION")
        for key in row_gates:
            gates[key] += 1
        match = (accepted and turn.get("statement_type") == rec["type"] and
                 turn.get("actor_paper") == rec.get("paper") and
                 turn.get("actor_edition_id") == rec.get("edition") and
                 rec.get("page") in turn.get("pages", []))
        if rec["type"] == "UNRESOLVED":
            match = response.get("outcome") == "ABSTAINED" and turn.get("statement_type") == "UNRESOLVED"
        rows.append({"query_id": rec["query_id"], "match": bool(match), "outcome": response.get("outcome")})
    report = {"panel_id": gold["panel_id"], "response_sha256": manifest["response_sha256"],
              "accuracy": sum(r["match"] for r in rows) / len(rows), "rows": rows,
              "hard_gate_counts": gates, "status": "PASS" if all(v == 0 for v in gates.values()) else "FAIL"}
    write_json(output, report)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    for command in ("panel", "dialogue"):
        p = sub.add_parser(command)
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--model", default=GENERATOR_MODEL)
        p.add_argument("--verifier-model", default=VERIFIER_MODEL)
        if command == "panel":
            p.add_argument("--queries", type=Path, required=True)
    for command in ("score-dev", "score-holdout"):
        p = sub.add_parser(command)
        p.add_argument("--gold", type=Path, required=True)
        p.add_argument("--responses", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.command == "panel":
        generate_panel(args.queries, args.output, args.model, args.verifier_model)
    elif args.command == "dialogue":
        generate_dialogue(args.output, args.model, args.verifier_model)
    elif args.command == "score-dev":
        score_dev(args.gold, args.responses, args.output)
    else:
        score_holdout(args.gold, args.responses, args.output)


if __name__ == "__main__":
    main()
