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

`SOURCE_QUOTE` additionally requires statement text to equal the evidence span after whitespace normalization.

## Minimal schema

Implemented fields: `statement_id`, `statement_type`, `text`, `paper_id`, `source_id`, `author`, `page`,
`section`, `evidence_span`, `citation`, `derived_from`, `target_statement`, `target_paper`, `confidence`,
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

## Missing metadata policy

Phase 1 chooses **FAIL** for missing page/source metadata on `SOURCE_QUOTE` and `AUTHOR_CLAIM`.
Unsupported material must remain `INTERPRETATION` or `UNRESOLVED`.

## Dialogue provenance

A paper agent's `CRITIQUE`, `RESPOND`, and source-bounded `QUESTION` may use only its own paper evidence.
Cross-paper `COMPARE`, `SYNTHESIZE`, `IDENTIFY_GAP`, and `GENERATE_RESEARCH_QUESTION` require evidence
IDs from at least two papers. There is no `JUDGE`, `WINNER`, or ranking action.
