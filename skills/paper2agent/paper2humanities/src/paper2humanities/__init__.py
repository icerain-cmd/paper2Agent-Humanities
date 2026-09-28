"""Paper2Agent-Humanities public API."""

from .dialogue import DialogueAction, DialogueTurn, ScholarlyDialogue
from .evaluation import evaluate_agent
from .paper_agent import PaperAgent
from .provenance import (
    AttributionFirewall,
    PaperEvidenceIndex,
    StatementStore,
    unsupported_author_claims,
    validate_against_source,
)
from .schema import EpistemicStatement, EvidenceVoice, ProvenanceError, ReviewStatus, SourceEdition, StatementType

__all__ = [
    "AttributionFirewall",
    "DialogueAction",
    "DialogueTurn",
    "EpistemicStatement",
    "EvidenceVoice",
    "PaperAgent",
    "PaperEvidenceIndex",
    "ProvenanceError",
    "ReviewStatus",
    "SourceEdition",
    "ScholarlyDialogue",
    "StatementStore",
    "StatementType",
    "evaluate_agent",
    "unsupported_author_claims",
    "validate_against_source",
]
