"""Deterministic grounding metrics for the humanities layer."""
from __future__ import annotations

from .paper_agent import PaperAgent
from .provenance import PaperEvidenceIndex, validate_against_source
from .schema import ProvenanceError, StatementType


def evaluate_agent(agent: PaperAgent, index: PaperEvidenceIndex) -> dict:
    statements = list(agent.store.values())
    grounded = [
        statement
        for statement in statements
        if statement.statement_type in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}
    ]
    valid = 0
    page_traced = 0
    for statement in grounded:
        try:
            validate_against_source(statement, index)
            valid += 1
            if statement.page:
                page_traced += 1
        except ProvenanceError:
            pass
    unsupported = agent.unsupported_author_claim_count(index)
    author_claims = [
        item for item in statements if item.statement_type == StatementType.AUTHOR_CLAIM
    ]
    return {
        "evaluation_scope": "CURATED_FIXTURE",
        "evaluation_kind": "FIXTURE_VALIDATION",
        "grounded_statement_count": len(grounded),
        "total_statement_count": len(statements),
        "source_attribution_accuracy": valid / len(grounded) if grounded else 1.0,
        "author_ai_separation": 1.0 if unsupported == 0 else 0.0,
        "page_level_traceability": page_traced / len(grounded) if grounded else 1.0,
        "evidence_coverage": valid / len(grounded) if grounded else 1.0,
        "unsupported_claim_rate": unsupported / len(author_claims) if author_claims else 0.0,
        "unsupported_author_claim": unsupported,
        "cross_paper_issue_detection": None,
        "research_question_novelty": None,
    }
