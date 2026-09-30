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
    ):
        self.paper_id = paper_id
        self.title = title
        self.author = author
        self.source_id = source_id
        self.source_sha256 = source_sha256
        self.concepts = tuple(concepts)
        self.store = StatementStore(statements)

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
        )

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
        )
