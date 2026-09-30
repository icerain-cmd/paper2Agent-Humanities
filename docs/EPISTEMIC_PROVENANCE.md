# Epistemic Provenance and Attribution Firewall

## Statement types

| Type | Meaning | Minimum provenance |
|---|---|---|
| `SOURCE_QUOTE` | exact source wording | paper/source ID, PDF page, evidence span, citation |
| `AUTHOR_CLAIM` | proposition attributed to paper author | paper/source ID, PDF page, supporting evidence span, citation |
| `INTERPRETATION` | researcher/AI reading | `derived_from` statement IDs |
| `AI_SYNTHESIS` | synthesis across prior statements | `derived_from` statement IDs |
| `CRITIQUE` | criticism of a statement/paper | explicit target + `derived_from` evidence |
| `UNRESOLVED` | insufficient evidence, conflict, open question | explicit unresolved reason |

`SOURCE_QUOTE` additionally requires statement text to equal the evidence span after whitespace normalization. Grounded statements also carry a reviewed `evidence_voice`: `AUTHOR_CLAIM` requires `AUTHOR`, while quoted prior scholarship is marked `EXTERNAL` and cannot support an author-claim attribution.

## Minimal schema

Implemented fields: `statement_id`, `statement_type`, `text`, `paper_id`, `source_id`, `author`, `page`,
`section`, `evidence_span`, `citation`, `evidence_voice`, `derived_from`, `target_statement`, `target_paper`, `confidence`,
`review_status`, `unresolved_reason`. Fields are required only where their type invariant needs them.

## Invariants

```text
SOURCE_QUOTE -> direct source span + page required
AUTHOR_CLAIM -> source evidence + page required
INTERPRETATION -> derived_from required
AI_SYNTHESIS -> derived_from required
CRITIQUE -> target + derived_from required
UNRESOLVED -> unresolved_reason required
```

`PaperEvidenceIndex` is built from a reviewed Paper2Skill work directory and refuses unreviewed pages.
Grounded statements are checked against the declared PDF page, not merely against a citation string.

## Attribution firewall

The firewall rejects:
- `AI_SYNTHESIS -> AUTHOR_CLAIM`
- `INTERPRETATION -> AUTHOR_CLAIM`
- `CRITIQUE -> SOURCE_QUOTE`

More generally, a derived statement cannot be mutated into either strong source type. New source evidence
requires a **new** grounded statement validated against the reviewed page.

## Edition-aware provenance

Edition-controlled sources use a separate `SourceEdition` identity with the minimum fields `work_id`, `edition_id`, `version_label`, `source_language`, `publication_year`, `canonical_source`, and optional `source_page`. A grounded statement may carry `edition_id`; when its evidence index is edition-aware the IDs must match exactly. This prevents a passage from Benjamin V2 from being silently validated against V3 merely because the wording is similar.

Benjamin V2 and V3 therefore remain distinct source identities (`benjamin-artwork-v2`, `benjamin-artwork-v3`). Cross-edition inference must be represented as interpretation/synthesis, never as source evidence copied across editions.

## Missing metadata policy

Phase 1 chooses **FAIL** for missing page/source metadata on `SOURCE_QUOTE` and `AUTHOR_CLAIM`.
Unsupported material must remain `INTERPRETATION` or `UNRESOLVED`.

## Dialogue provenance

A paper agent's `CRITIQUE`, `RESPOND`, and source-bounded `QUESTION` may use only its own paper evidence.
Cross-paper `COMPARE`, `SYNTHESIZE`, `IDENTIFY_GAP`, and `GENERATE_RESEARCH_QUESTION` require evidence
IDs from at least two papers. There is no `JUDGE`, `WINNER`, or ranking action.
