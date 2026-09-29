"""Paper2Agent-Humanities public API."""

from .dialogue import (
    DialogueAction, DialogueTurn, RelationType, SemanticSupportStatus,
    ScholarlyDialogue, review_binding_sha256, validate_turn_for_publication,
)
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
    "RelationType",
    "SemanticSupportStatus",
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
    "validate_turn_for_publication",
    "review_binding_sha256",
]
