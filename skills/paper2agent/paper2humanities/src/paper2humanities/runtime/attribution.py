"""Orthogonal attribution axes for V6 while preserving legacy statement_type/evidence_voice."""
from __future__ import annotations

STATEMENT_FORMS = {"QUOTE", "PARAPHRASE", "INTERPRETIVE_STATEMENT", "SYNTHESIS"}
ATTRIBUTION_OWNERS = {"AUTHOR", "EXTERNAL", "AI", "UNKNOWN"}

def infer_statement_form(turn: dict) -> str | None:
    explicit = turn.get("statement_form")
    if explicit in STATEMENT_FORMS:
        return explicit
    kind = turn.get("statement_type")
    if kind == "SOURCE_QUOTE":
        return "QUOTE"
    if kind == "AUTHOR_CLAIM":
        return "PARAPHRASE"
    if kind in {"INTERPRETATION", "CRITIQUE"}:
        return "INTERPRETIVE_STATEMENT"
    if kind == "AI_SYNTHESIS":
        return "SYNTHESIS"
    return None

def infer_attribution_owner(turn: dict) -> str:
    explicit = turn.get("attribution_owner")
    if explicit in ATTRIBUTION_OWNERS:
        return explicit
    if turn.get("statement_type") == "AI_SYNTHESIS":
        return "AI"
    voice = turn.get("evidence_voice")
    if voice in {"AUTHOR", "EXTERNAL"}:
        return voice
    return "UNKNOWN"

def enrich_attribution_axes(turn: dict) -> dict:
    enriched = dict(turn)
    if enriched.get("statement_type") != "UNRESOLVED":
        enriched.setdefault("statement_form", infer_statement_form(enriched))
        enriched.setdefault("attribution_owner", infer_attribution_owner(enriched))
    return enriched
