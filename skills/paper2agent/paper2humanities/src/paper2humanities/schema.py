"""Epistemic statement schema for attribution-aware humanities paper agents."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class StatementType(str, Enum):
    SOURCE_QUOTE = "SOURCE_QUOTE"
    AUTHOR_CLAIM = "AUTHOR_CLAIM"
    INTERPRETATION = "INTERPRETATION"
    AI_SYNTHESIS = "AI_SYNTHESIS"
    CRITIQUE = "CRITIQUE"
    UNRESOLVED = "UNRESOLVED"


class EvidenceVoice(str, Enum):
    AUTHOR = "AUTHOR"
    EXTERNAL = "EXTERNAL"
    UNKNOWN = "UNKNOWN"


class ReviewStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    REVIEWED = "REVIEWED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ProvenanceError(ValueError):
    """Raised when a statement violates an epistemic provenance invariant."""


def _clean(value: str | None) -> str:
    return (value or "").strip()


@dataclass(frozen=True, slots=True)
class EpistemicStatement:
    statement_id: str
    statement_type: StatementType
    text: str
    paper_id: str | None = None
    source_id: str | None = None
    author: str | None = None
    page: int | None = None
    section: str | None = None
    evidence_span: str | None = None
    citation: str | None = None
    evidence_voice: EvidenceVoice | None = None
    derived_from: tuple[str, ...] = field(default_factory=tuple)
    target_statement: str | None = None
    target_paper: str | None = None
    confidence: float | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        if not _clean(self.statement_id):
            raise ProvenanceError("statement_id is required")
        if not _clean(self.text):
            raise ProvenanceError("text is required")
        if self.page is not None and (not isinstance(self.page, int) or self.page < 1):
            raise ProvenanceError("page must be a positive integer")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ProvenanceError("confidence must be between 0 and 1")

        grounded = {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}
        if self.statement_type in grounded:
            missing = [
                name for name, value in (
                    ("paper_id", self.paper_id),
                    ("source_id", self.source_id),
                    ("page", self.page),
                    ("evidence_span", self.evidence_span),
                    ("citation", self.citation),
                )
                if value is None or (isinstance(value, str) and not value.strip())
            ]
            if missing:
                raise ProvenanceError(
                    f"{self.statement_type.value} requires source evidence: {', '.join(missing)}"
                )

        if self.statement_type in grounded and self.evidence_voice is None:
            raise ProvenanceError(f"{self.statement_type.value} requires evidence_voice")
        if self.statement_type == StatementType.AUTHOR_CLAIM and self.evidence_voice != EvidenceVoice.AUTHOR:
            raise ProvenanceError("AUTHOR_CLAIM requires AUTHOR evidence_voice")

        if self.statement_type == StatementType.SOURCE_QUOTE:
            if " ".join(self.text.split()) != " ".join(_clean(self.evidence_span).split()):
                raise ProvenanceError("SOURCE_QUOTE text must equal its evidence_span")

        if self.statement_type in {StatementType.INTERPRETATION, StatementType.AI_SYNTHESIS}:
            if not self.derived_from:
                raise ProvenanceError(f"{self.statement_type.value} requires derived_from")

        if self.statement_type == StatementType.CRITIQUE:
            if not (self.target_statement or self.target_paper):
                raise ProvenanceError("CRITIQUE requires target_statement or target_paper")
            if not self.derived_from:
                raise ProvenanceError("CRITIQUE requires evidence in derived_from")

        if self.statement_type == StatementType.UNRESOLVED and not _clean(self.unresolved_reason):
            raise ProvenanceError("UNRESOLVED requires unresolved_reason")

    def to_dict(self) -> dict[str, Any]:
        data = {
            "statement_id": self.statement_id,
            "statement_type": self.statement_type.value,
            "text": self.text,
            "paper_id": self.paper_id,
            "source_id": self.source_id,
            "author": self.author,
            "page": self.page,
            "section": self.section,
            "evidence_span": self.evidence_span,
            "citation": self.citation,
            "evidence_voice": self.evidence_voice.value if self.evidence_voice else None,
            "derived_from": list(self.derived_from),
            "target_statement": self.target_statement,
            "target_paper": self.target_paper,
            "confidence": self.confidence,
            "review_status": self.review_status.value,
            "unresolved_reason": self.unresolved_reason,
        }
        return {key: value for key, value in data.items() if value not in (None, [], ())}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpistemicStatement":
        values = dict(data)
        values["statement_type"] = StatementType(values["statement_type"])
        values["review_status"] = ReviewStatus(values.get("review_status", "UNREVIEWED"))
        if values.get("evidence_voice") is not None:
            values["evidence_voice"] = EvidenceVoice(values["evidence_voice"])
        values["derived_from"] = tuple(values.get("derived_from", ()))
        return cls(**values)

    def with_review_status(self, status: ReviewStatus) -> "EpistemicStatement":
        return replace(self, review_status=status)
