# Phase 2 Dialogue Protocol

## Scope

Phase 2 dialogue is evidence-bounded scholarly comparison, not author role-play. A Paper Agent may speak only from reviewed propositions belonging to its own paper/source/edition boundary.

Benjamin source approval is a hard prerequisite for creating either Benjamin Paper Agent or executing Tests D/E/F.

## Agent identities

Planned post-approval agents remain separate:

```
lee-aura-2019
benjamin-artwork-v2
benjamin-artwork-v3
```

V2 and V3 use distinct `paper_id`, `source_id`, and `edition_id`. Similar wording never permits cross-edition evidence substitution.

## Dialogue turns

Phase-2 turns preserve:

- turn_id
- action
- actor_paper
- actor_edition_id
- target_paper
- target_statement_id
- support_ids
- relation_type
- statement text
- semantic support status
- review status

Critique relation types are:

`CONTRADICTS`, `TENSIONS_WITH`, `QUALIFIES`, `EXTENDS`, `REFRAMES`, `NOT_ADDRESSED`, `UNRESOLVED`.

There is no judge/winner operation.

## Edition firewall

For paper-owned QUESTION / CRITIQUE / RESPOND turns:

1. every paper-owned support statement must match the actor's `paper_id`, `source_id`, and `edition_id`, and its grounded source statement must match the corresponding evidence index;
2. wording checks, including German inflections of first/second `Technik`, provide an additional warning layer;
3. a V2 statement cannot be emitted with a V3 citation;
4. a V3 agent cannot answer a V2-only passage;
5. cross-edition synthesis must cite statements from both separate source agents and remains `AI_SYNTHESIS` or `UNRESOLVED`.

## Temporal/corpus firewall

The Lee Paper Agent is bounded to 「기술편집시대 아우라 연구의 방향성」 (2019). Its committed corpus policy blocks later Lee vocabulary when used as a Lee-2019 response, including:

`아투라`, `기계세`, `Mechanocene`, `기술생성시대`, `공진주체 WE`, `마찰의 투명성`, `생성 아우라`.

This is a negative-control list, not a claim that these terms exhaust all later concepts. A later concept may appear only in an explicitly external synthesis layer, never as Lee-2019 evidence.

## Semantic support review

Provenance validity and semantic support are separate.

A turn begins at `PROVENANCE_VALID`; this means its support IDs exist and obey paper/edition boundaries. It is not yet publishable.

Approval is bound to SHA256 of canonical UTF-8 JSON containing `turn_id`, `text`, `statement_type`, `support_ids`, `relation_type`, `actor_paper`, `actor_edition_id`, `target_paper`, and `target_statement_id` (sorted keys, compact separators, original support order). The semantic review artifact stores `review_binding_sha256`; publication and verification block changed or unbound turns with `SEMANTIC_REVIEW_STALE`.

Reviewer statuses:

- `SEMANTICALLY_SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `OVERSTATED`
- `UNSUPPORTED`

Publication requires `review_status=REVIEWED` and semantic support of either `SEMANTICALLY_SUPPORTED` or `PARTIALLY_SUPPORTED`. `OVERSTATED` and `UNSUPPORTED` fail publication.

## Test D — source-bounded critique

After source approval, create at least six reviewed cases: at least three V2-based and three V3-based. A critique references the actor's verified Benjamin proposition and a specific Lee proposition. Digital concepts not addressed by Benjamin are labelled `NOT_ADDRESSED` or `UNRESOLVED`; they are not invented as Benjamin speech.

## Test E — Lee response

Each Test-D turn is passed to the Lee-2019 agent. Lee may answer only with Lee-2019 propositions. Valid outcomes are `SUPPORTED_RESPONSE`, `PARTIAL_RESPONSE`, `NO_SOURCE_SUPPORTED_RESPONSE`, or `UNRESOLVED`. There is no requirement to fabricate a rebuttal.

## Test F — synthesis

The synthesis layer receives only verified Lee statements, verified V2/V3 statements, reviewed D turns, and reviewed E turns. New connections are `AI_SYNTHESIS` or `UNRESOLVED`, never `AUTHOR_CLAIM`.

Research questions record `novelty_basis`, `derived_from`, `source_gap`, and `human_review_status`.

## Hard gates

Post-approval dialogue publication requires:

```
FALSE_AUTHOR_CLAIM=0
EXTERNAL_AS_AUTHOR_ERROR=0
CROSS_EDITION_CONTAMINATION=0
UNSUPPORTED_DIALOGUE_TURN=0
TEMPORAL_CORPUS_CONTAMINATION=0
FAKE_PAGE_CITATION=0
```

Before source approval these dialogue-run gates are `NOT_EVALUATED`, not assumed to be zero.
