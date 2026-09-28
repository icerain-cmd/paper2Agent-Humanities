# Phase 2 Results — Pre-Approval Checkpoint

## Status

```
PHASE2_STATUS=BLOCKED_SOURCE_APPROVAL
BENJAMIN_AGENT=PENDING_SOURCE_APPROVAL
TEST_D=NOT_RUN_PENDING_SOURCE_APPROVAL
TEST_E=NOT_RUN_PENDING_SOURCE_APPROVAL
TEST_F=NOT_RUN_PENDING_SOURCE_APPROVAL
```

The approval block is intentional. Source verification is complete enough to present a source choice, but user approval has not been inferred from the task instruction.

## Phase 1.5 live-evaluation correction

The previous 50-response 1.0 result is now labelled `COMMITTED_BLIND_RESPONSE_SET`: it scores a frozen, pre-existing response artifact. It is not evidence that an agent freshly answered 50 blind queries.

A separate gold-isolated `LIVE_BLIND_RUN` was implemented. No external model runtime was available to the repository process, so the run is explicitly `DETERMINISTIC_BEHAVIORAL_EVAL`, not `LIVE_AGENT_EVAL`.

Official run: `lee-aura-live-20260928T041757Z`.

- gold available during response generation: false
- external blind: false
- type accuracy: 0.44
- evidence voice accuracy: 0.52
- page accuracy: 0.3658536585
- evidence span accuracy: 0.0731707317
- unsupported-claim rejection: 0.3333333333
- false author claims: 5
- external-as-author errors: 4
- interpretation promotions: 0
- adversarial robustness: 0.10

All 45 failed rows remain in the run artifact.

## Benjamin V2 verification

The Commons four-version container is 291 pages, SHA-256 `0f5f14abc67e1da4829b37830d2ac3f554468e7ff7470be3d6dd4db813d877c1`.

Verified V2 boundary:

- container PDF 196–230
- GS VII.1 pp.350–384
- prepared V2-only working slice: 35 pages
- current slice SHA-256 `d5c9f013689f2662a64e8235a4599ade25036fb40dcd18a388b93d683bcca0ec`
- first/second technology passage: container PDF 205 / slice PDF 10 / GS 359

The German passage contains the relevant inflected wording for first/second technology, `Ein für allemal`, `Einmal ist keinmal`, the origin of second technology, and `Spiel`.

## Benjamin V3 verification

The separate V3 facsimile is 38 pages, SHA-256 `bdb9107b41e05fd6919592d6ba786b501f160a1618b1d9e1f4d21108d0745568`, mapping PDF 1–38 to GS I.2 pp.471–508.

Aura, Echtheit, Kultwert, Ausstellungswert, film, Zerstreuung, and Rezeption were positively located. The V2-specific first/second-technology strings were absent across all 38 pages.

## Lee–Benjamin pre-approval mapping

Five reviewed source mappings are committed:

- V2 first/second technology → Lee PDF 18 / printed 264
- V3 aura destruction → Lee PDF 7 / printed 253
- V3 concentration/distraction → Lee PDF 8 / printed 254
- V3 distracted examiner/film → Lee PDF 10 / printed 256
- V3 crisis/new demand/Dada → Lee PDF 14 / printed 260

All are `STRONG_MATCH`, not `EXACT`, because the Korean translation was not independently aligned word-for-word against the German edition.

## Implemented pre-approval hardening

- PaperAgent edition identity
- dialogue actor edition identity
- actor-owned/edition-owned response support
- cross-edition synthesis provenance
- Lee-2019 temporal/corpus deny-list for later concepts
- semantic-support review states
- publishability gate separate from provenance validation
- source-map artifact and source-verification artifact

## Not performed

No Benjamin Paper Agent is created. No source is marked user-approved. No Test-D critique, Test-E Lee response, or Test-F cross-paper research-gap synthesis is executed.

The next operation requires explicit user approval of **both separately identified V2 and V3 source candidates**.
