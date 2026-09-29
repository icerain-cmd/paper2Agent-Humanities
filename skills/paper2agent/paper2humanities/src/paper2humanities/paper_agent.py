"""A bounded paper agent: retrieval over reviewed, typed propositions."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .provenance import PaperEvidenceIndex, StatementStore, unsupported_author_claims
from .schema import EpistemicStatement, StatementType


class PaperAgent:
    def __init__(
        self,
        paper_id: str,
        title: str,
        author: str,
        source_id: str,
        source_sha256: str,
        concepts: list[str],
        statements: list[EpistemicStatement],
        edition_id: str | None = None,
        forbidden_terms: list[str] | None = None,
    ):
        self.paper_id = paper_id
        self.title = title
        self.author = author
        self.source_id = source_id
        self.source_sha256 = source_sha256
        self.edition_id = edition_id
        self.forbidden_terms = tuple(forbidden_terms or ())
        self.concepts = tuple(concepts)
        self.store = StatementStore(statements)
        self._validate_statement_boundaries()

    @classmethod
    def from_json(cls, path: str | Path) -> "PaperAgent":
        data = json.loads(Path(path).read_text())
        return cls(
            paper_id=data["paper_id"],
            title=data["title"],
            author=data["author"],
            source_id=data["source"]["source_id"],
            source_sha256=data["source"]["sha256"],
            concepts=list(data.get("concepts", [])),
            statements=[EpistemicStatement.from_dict(item) for item in data["statements"]],
            edition_id=data.get("source", {}).get("edition_id") or data.get("edition_id"),
            forbidden_terms=list(data.get("corpus_policy", {}).get("forbidden_terms", [])),
        )


    def _validate_statement_boundaries(self) -> None:
        for statement in self.store.values():
            if statement.statement_type not in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}:
                continue
            if statement.paper_id != self.paper_id or statement.source_id != self.source_id:
                raise ValueError(f"grounded statement crosses PaperAgent source boundary: {statement.statement_id}")
            if self.edition_id is not None and statement.edition_id != self.edition_id:
                raise ValueError(f"grounded statement crosses PaperAgent edition boundary: {statement.statement_id}")
            if self.edition_id is None and statement.edition_id is not None:
                raise ValueError(f"statement declares edition for non-editioned PaperAgent: {statement.statement_id}")

    def validate_output_text(self, text: str) -> None:
        violations = [term for term in self.forbidden_terms if term and term.lower() in text.lower()]
        if self.edition_id == "benjamin-artwork-v3" and re.search(
            r"\b(?:erste|ersten|erster|erstes|zweite|zweiten|zweiter|zweites)\s+Technik\b",
            text, re.IGNORECASE,
        ):
            violations.append("V2 first/second technology terminology")
        if violations:
            raise ValueError(f"temporal/corpus boundary violation for {self.paper_id}: {violations}")

    def retrieve(
        self,
        query: str,
        allowed_types: set[StatementType] | None = None,
        limit: int = 5,
    ) -> list[EpistemicStatement]:
        terms = set(re.findall(r"[0-9A-Za-z가-힣_]+", query.lower()))
        scored = []
        for statement in self.store.values():
            if allowed_types and statement.statement_type not in allowed_types:
                continue
            haystack = " ".join(
                filter(None, [statement.text, statement.section or "", statement.evidence_span or ""])
            ).lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, statement))
        scored.sort(key=lambda pair: (-pair[0], pair[1].statement_id))
        return [statement for _, statement in scored[:limit]]

    def unsupported_author_claim_count(self, index: PaperEvidenceIndex) -> int:
        return len(unsupported_author_claims(self.store.values(), index))

    def source_bound(self, statement_id: str) -> bool:
        statement = self.store.get(statement_id)
        return (
            statement.statement_type in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}
            and statement.paper_id == self.paper_id
            and statement.source_id == self.source_id
            and statement.edition_id == self.edition_id
        )
