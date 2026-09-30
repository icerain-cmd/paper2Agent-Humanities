import pytest

from paper2humanities import (
    AttributionFirewall,
    EpistemicStatement,
    EvidenceVoice,
    PaperEvidenceIndex,
    ProvenanceError,
    ReviewStatus,
    SourceEdition,
    StatementStore,
    StatementType,
    validate_against_source,
)


def source_index():
    return PaperEvidenceIndex(
        "p1", "s1", "a" * 64, {1: "Visible source statement with evidence."}
    )


def grounded_claim(**overrides):
    data = dict(
        statement_id="c1",
        statement_type=StatementType.AUTHOR_CLAIM,
        text="The author makes a claim.",
        paper_id="p1",
        source_id="s1",
        author="Author",
        page=1,
        section="Introduction",
        evidence_span="Visible source statement with evidence.",
        citation="PDF p.1",
        evidence_voice=EvidenceVoice.AUTHOR,
        review_status=ReviewStatus.REVIEWED,
    )
    data.update(overrides)
    return EpistemicStatement(**data)


def test_direct_quote_without_source_fails():
    with pytest.raises(ProvenanceError):
        EpistemicStatement(
            statement_id="q1",
            statement_type=StatementType.SOURCE_QUOTE,
            text="quote",
            evidence_span="quote",
        )


def test_author_claim_without_evidence_fails():
    with pytest.raises(ProvenanceError):
        EpistemicStatement(
            statement_id="c1",
            statement_type=StatementType.AUTHOR_CLAIM,
            text="claim",
            paper_id="p1",
            source_id="s1",
            page=1,
            citation="PDF p.1",
        )


def test_valid_author_claim_with_evidence_passes():
    claim = grounded_claim()
    validate_against_source(claim, source_index())


def test_external_voice_cannot_support_author_claim():
    with pytest.raises(ProvenanceError):
        grounded_claim(evidence_voice=EvidenceVoice.EXTERNAL)


def test_missing_page_metadata_fails():
    with pytest.raises(ProvenanceError):
        grounded_claim(page=None)


def test_ai_synthesis_cannot_be_promoted_to_author_claim():
    claim = grounded_claim()
    synthesis = EpistemicStatement(
        statement_id="s1",
        statement_type=StatementType.AI_SYNTHESIS,
        text="AI synthesis",
        derived_from=(claim.statement_id,),
    )
    with pytest.raises(ProvenanceError):
        AttributionFirewall.retype(synthesis, StatementType.AUTHOR_CLAIM)


def test_interpretation_cannot_be_promoted_without_new_source_statement():
    claim = grounded_claim()
    interpretation = EpistemicStatement(
        statement_id="i1",
        statement_type=StatementType.INTERPRETATION,
        text="Interpretation",
        derived_from=(claim.statement_id,),
    )
    with pytest.raises(ProvenanceError):
        AttributionFirewall.retype(interpretation, StatementType.AUTHOR_CLAIM)


def test_critique_without_target_fails():
    with pytest.raises(ProvenanceError):
        EpistemicStatement(
            statement_id="k1",
            statement_type=StatementType.CRITIQUE,
            text="Critique",
            derived_from=("c1",),
        )


def test_store_rejects_unknown_derivation():
    store = StatementStore()
    with pytest.raises(ProvenanceError):
        store.add(
            EpistemicStatement(
                statement_id="i1",
                statement_type=StatementType.INTERPRETATION,
                text="Interpretation",
                derived_from=("missing",),
            )
        )


def test_edition_separation_requires_exact_edition_id():
    edition_v2 = SourceEdition(
        work_id="benjamin-artwork", edition_id="benjamin-artwork-v2",
        version_label="Zweite Fassung", source_language="de", publication_year=1936,
        canonical_source="Gesammelte Schriften VII.1, 350-384",
    )
    index_v2 = PaperEvidenceIndex("b", "s-v2", "b" * 64, {1: "same phrase"}, edition=edition_v2)
    statement = EpistemicStatement(
        statement_id="b-v2-q", statement_type=StatementType.SOURCE_QUOTE, text="same phrase",
        paper_id="b", source_id="s-v2", author="Walter Benjamin", page=1,
        evidence_span="same phrase", citation="V2 p.1", edition_id="benjamin-artwork-v2",
        evidence_voice=EvidenceVoice.AUTHOR, review_status=ReviewStatus.REVIEWED,
    )
    validate_against_source(statement, index_v2)


def test_cross_edition_contamination_rejected_even_when_text_matches():
    edition_v3 = SourceEdition(
        work_id="benjamin-artwork", edition_id="benjamin-artwork-v3",
        version_label="Dritte Fassung", source_language="de", publication_year=1939,
        canonical_source="Gesammelte Schriften I.2, 471-508",
    )
    index_v3 = PaperEvidenceIndex("b", "s-v3", "c" * 64, {1: "same phrase"}, edition=edition_v3)
    statement = EpistemicStatement(
        statement_id="b-v2-q", statement_type=StatementType.SOURCE_QUOTE, text="same phrase",
        paper_id="b", source_id="s-v3", author="Walter Benjamin", page=1,
        evidence_span="same phrase", citation="V2 p.1", edition_id="benjamin-artwork-v2",
        evidence_voice=EvidenceVoice.AUTHOR, review_status=ReviewStatus.REVIEWED,
    )
    with pytest.raises(ProvenanceError, match="edition"):
        validate_against_source(statement, index_v3)
