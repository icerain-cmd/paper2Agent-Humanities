"""Evaluate preregistered holdout criteria without generating responses."""
from __future__ import annotations

import json
from pathlib import Path

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "evals" / "phase3" / "holdout30-v5-pass-contract.json"
V6_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "evals" / "phase3" / "holdout30-v6-pass-contract.json"
V7_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "evals" / "phase3" / "holdout30-v7-pass-contract.json"
V8_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "evals" / "phase3" / "holdout30-v8-pass-contract.json"


def load_v5_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())

def load_v6_contract() -> dict:
    return json.loads(V6_CONTRACT_PATH.read_text())

def load_v7_contract() -> dict:
    return json.loads(V7_CONTRACT_PATH.read_text())

def load_v8_contract() -> dict:
    return json.loads(V8_CONTRACT_PATH.read_text())

def evaluate_pass_contract(report: dict, contract: dict) -> dict:
    gates = report["hard_gate_counts"]
    missing = sorted(set(contract["required_hard_gates"]) - set(gates))
    if missing:
        raise ValueError(f"missing hard gates: {missing}")
    checks = {
        "all_hard_gates_zero": all(value == contract["hard_gate_maximum"] for value in gates.values()),
        "exact_match_accuracy": report["accuracy"] >= contract["minimum_exact_match_accuracy"],
        "source_id_accuracy": report["source_id_accuracy"] >= contract["minimum_source_id_accuracy"],
        "unsupported_premise_rejection": report["unsupported_premise_rejection"] >= contract["minimum_unsupported_premise_rejection"],
        "false_author_claim": gates["FALSE_AUTHOR_CLAIM"] <= contract["maximum_false_author_claim"],
        "fake_page_citation": gates["FAKE_PAGE_CITATION"] <= contract["maximum_fake_page_citation"],
    }
    return {"contract_id": contract["contract_id"], "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL"}


def evaluate_v6_pass_contract(report: dict, contract: dict) -> dict:
    gates = report["hard_gate_counts"]
    missing = sorted(set(contract["required_hard_gates"]) - set(gates))
    if missing:
        raise ValueError(f"missing hard gates: {missing}")
    checks = {
        "all_hard_gates_zero": all(gates[name] <= contract["hard_gate_maximum"] for name in contract["required_hard_gates"]),
        "factual_task_accuracy": report["factual_task_accuracy"] >= contract["minimum_factual_task_accuracy"],
        "scholarly_task_validity": report["scholarly_task_validity"] >= contract["minimum_scholarly_task_validity"],
        "overall_validity": report["overall_validity"] >= contract["minimum_overall_validity"],
        "source_id_accuracy": report["source_id_accuracy"] >= contract["minimum_source_id_accuracy"],
        "unsupported_premise_rejection": report["unsupported_premise_rejection"] >= contract["minimum_unsupported_premise_rejection"],
        "abstention_precision": report["abstention_precision"] >= contract["minimum_abstention_precision"],
    }
    return {"contract_id": contract["contract_id"], "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL"}
