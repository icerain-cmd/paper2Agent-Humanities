# Phase-1 PoC Protocol

## Paper Agent A

이용욱, 「기술편집시대 아우라 연구의 방향성」, 『국어국문학』 188 (2019).

Source:
- user Google Drive ID `1mKDGrGLLXCQJNjPVvdBYXOz9tB3tuUcW`
- SHA-256 `864e341de1fa049fd3c5285c882125967671aebde4ef37f5d9156613d061adae`
- 31 PDF pages

The source was processed through the audited upstream Paper2Skill pipeline. All 31 pages were visually
checked using its contact sheets. `verify --strict` passed as `reviewed_with_limitations`: 33 exact
diagnostic fingerprints were adjudicated, chiefly independent-parser number differences caused by
legacy/CFF Korean font encoding. No mechanical or artifact-integrity issue remained.

The repository fixture stores source identity, concepts and short evidence spans only; the PDF is not committed.

## Concepts

`기술편집시대`, `아우라`, `디지털아우라`, `제3기술`, `투명화`, `신뢰화`, `흔적`, `정신몰입`.

## Test A — Retrieval

Question: 이 논문에서 기술편집시대의 아우라 문제는 어떻게 규정되는가?

Gate: return typed, source-bound statements rather than an untyped model summary.

## Test B — Attribution

Question: 이 주장은 이용욱 자신의 주장인가, 선행연구의 주장인가, AI의 해석인가?

Gate: distinguish Lee `AUTHOR_CLAIM`, a Benjamin `SOURCE_QUOTE` quoted inside Lee's paper, and a
separate `INTERPRETATION`.

## Test C — Evidence

Question: 그 판단의 원문 근거와 페이지를 제시하라.

Gate: every `SOURCE_QUOTE` and `AUTHOR_CLAIM` resolves to the declared PDF page.

### CURATED_FIXTURE validation

The following metrics validate the committed 11-statement fixture only. They do **not** measure open-ended attribution performance across the full 31-page paper. The fixture contains 10 grounded statements (`AUTHOR_CLAIM` or `SOURCE_QUOTE`) and one `INTERPRETATION`.

Live fixture-validation result:
- Source Attribution Accuracy = 1.0
- Author/AI Separation = 1.0
- Page-level Traceability = 1.0
- Evidence Coverage = 1.0
- Unsupported Claim Rate = 0.0
- Unsupported AUTHOR_CLAIM = **0**

## Tests D–F — second-source protocol

D. Benjamin evidence may critique Lee only after an approved Benjamin source becomes its own Paper Agent.
E. Lee Agent may respond only from Lee-paper evidence.
F. Gap/research-question synthesis requires explicit statements from both agents and remains
`AI_SYNTHESIS` or `UNRESOLVED`.

## Benjamin candidate — do not ingest yet

### A. User Drive Korean PDF

`기술복제시대의예술작품.pdf` (Drive ID `1NmbZNi6LbGNAe-sEGDKrU7LYbkFD2Fz0`).
It identifies itself as Benjamin's 1936 essay, translated by CP Group and distributed via `armarius.net`.

Pros: fixed pages, already in the user's corpus, Korean comparison text.
Risks: translation/publication rights and edition status are not verified; the artwork essay exists in
multiple German versions, so edition control is mandatory.

### B. German third version on Wikisource

Wikisource exposes the third/authorized final version with page-level facsimile links and says it was
proofread twice against the source. It identifies the source as `Gesammelte Schriften` I.2 (Suhrkamp,
1980), pp. 471–508.

Pros: public, page-addressable, German original, explicit version identity.
Risks: pagination is that of the later critical-edition scan; mapping to Lee's 2009 Korean Benjamin
citations is still required.

## Recommendation

Prefer Candidate B as the reproducible primary-text control. Keep Candidate A as a Korean comparison
text only after translation/rights status is confirmed. No Benjamin paper was ingested in Phase 1.

`BENJAMIN_AGENT=PENDING_SOURCE_APPROVAL`.

Cross-paper Issue Detection and Research Question Novelty remain unscored until source approval. Phase 1.5 adds a separate `BLIND_ADVERSARIAL_PANEL`; its behavioral metrics must never be conflated with these curated-fixture checks.
