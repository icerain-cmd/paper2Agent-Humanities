"""Source verification and the attribution firewall."""
from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from .schema import EpistemicStatement, ProvenanceError, StatementType


def canonical_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


class PaperEvidenceIndex:
    """Page-indexed evidence exported from a reviewed Paper2Skill work directory."""

    def __init__(self, paper_id: str, source_id: str, source_sha256: str, pages: dict[int, str]):
        self.paper_id = paper_id
        self.source_id = source_id
        self.source_sha256 = source_sha256
        self.pages = dict(pages)

    @classmethod
    def from_paper2skill_work(
        cls, work_dir: str | Path, paper_id: str, source_id: str | None = None
    ) -> "PaperEvidenceIndex":
        work = Path(work_dir)
        inventory = json.loads((work / "inventory.json").read_text())
        sources = inventory["sources"]
        if source_id is None:
            if len(sources) != 1:
                raise ProvenanceError("source_id is required for multi-source Paper2Skill bundles")
            source_id = sources[0]["id"]
        source = next((item for item in sources if item["id"] == source_id), None)
        if not source:
            raise ProvenanceError(f"unknown Paper2Skill source_id: {source_id}")
        doc = work / "documents" / source_id
        pages: dict[int, str] = {}
        for page_file in sorted((doc / "pages").glob("page-*.json")):
            state = json.loads(page_file.read_text())
            if not state.get("reviewed"):
                raise ProvenanceError(f"unreviewed Paper2Skill page: {state.get('page')}")
            pages[int(state["page"])] = "\n".join(
                item.get("markdown", "") for item in state.get("items", []) if item.get("markdown")
            )
        if not pages:
            raise ProvenanceError("no reviewed Paper2Skill pages found")
        return cls(paper_id, source_id, source["sha256"], pages)

    @classmethod
    def from_dict(cls, data: dict) -> "PaperEvidenceIndex":
        return cls(
            data["paper_id"],
            data["source_id"],
            data["source_sha256"],
            {int(page): text for page, text in data["pages"].items()},
        )

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "pages": {str(page): text for page, text in sorted(self.pages.items())},
        }

    def contains(self, page: int, evidence_span: str) -> bool:
        haystack = canonical_text(self.pages.get(page, ""))
        needle = canonical_text(evidence_span)
        return bool(needle) and needle in haystack


class StatementStore:
    def __init__(self, statements: Iterable[EpistemicStatement] = ()):
        self._items: dict[str, EpistemicStatement] = {}
        for statement in statements:
            self.add(statement)

    def add(self, statement: EpistemicStatement) -> None:
        if statement.statement_id in self._items:
            raise ProvenanceError(f"duplicate statement_id: {statement.statement_id}")
        missing = [sid for sid in statement.derived_from if sid not in self._items]
        if missing:
            raise ProvenanceError(f"unknown derived_from statements: {missing}")
        if statement.target_statement and statement.target_statement not in self._items:
            raise ProvenanceError(f"unknown target_statement: {statement.target_statement}")
        self._items[statement.statement_id] = statement

    def get(self, statement_id: str) -> EpistemicStatement:
        try:
            return self._items[statement_id]
        except KeyError as exc:
            raise ProvenanceError(f"unknown statement: {statement_id}") from exc

    def values(self) -> tuple[EpistemicStatement, ...]:
        return tuple(self._items.values())


class AttributionFirewall:
    """Never mutate an AI interpretation into stronger author/source attribution."""

    FORBIDDEN = {
        (StatementType.AI_SYNTHESIS, StatementType.AUTHOR_CLAIM),
        (StatementType.INTERPRETATION, StatementType.AUTHOR_CLAIM),
        (StatementType.CRITIQUE, StatementType.SOURCE_QUOTE),
    }
    STRONG = {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}

    @classmethod
    def retype(cls, statement: EpistemicStatement, new_type: StatementType) -> EpistemicStatement:
        pair = (statement.statement_type, new_type)
        if pair in cls.FORBIDDEN:
            raise ProvenanceError(
                f"attribution firewall forbids {pair[0].value} -> {pair[1].value}"
            )
        if new_type in cls.STRONG and new_type != statement.statement_type:
            raise ProvenanceError(
                "strong attribution must be created as a new source-grounded statement, not promoted"
            )
        return replace(statement, statement_type=new_type)


def validate_against_source(
    statement: EpistemicStatement, index: PaperEvidenceIndex
) -> None:
    if statement.statement_type not in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}:
        return
    if statement.paper_id != index.paper_id or statement.source_id != index.source_id:
        raise ProvenanceError("statement paper/source does not match evidence index")
    if statement.page is None or not index.contains(statement.page, statement.evidence_span or ""):
        raise ProvenanceError(
            f"evidence span not found on PDF page {statement.page}: {statement.statement_id}"
        )


def unsupported_author_claims(
    statements: Iterable[EpistemicStatement], index: PaperEvidenceIndex
) -> list[str]:
    unsupported: list[str] = []
    for statement in statements:
        if statement.statement_type != StatementType.AUTHOR_CLAIM:
            continue
        try:
            validate_against_source(statement, index)
        except ProvenanceError:
            unsupported.append(statement.statement_id)
    return unsupported
