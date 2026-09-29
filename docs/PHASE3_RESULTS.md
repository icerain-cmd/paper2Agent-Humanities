# Phase 3 Results

## Current status

`PHASE3_STATUS=REPAIR_VALIDATED_AWAITING_V3_FREEZE`. Phase 3 is not complete.

PC2 runtime is live and verified on `DESKTOP-GA4FNS2` with Codex `0.155.1`. Generator `gpt-6-sol` and verifier `gpt-5.6-sol` both completed real schema-constrained ephemeral calls. The verifier runs with fresh context and is independent from the generator model.

The V2 evaluation exposed `UNSUPPORTED_DIALOGUE_TURN=4` in rows H30V2F-005/006/012/013. All four had the needed primary evidence in retrieval top-k. The direct failure was a schema/publication-gate contract mismatch: `publication_gate()` required a `qualification` for `PARTIALLY_SUPPORTED`, while the live typed-turn schema prohibited that field. Repair commit `226a5bd` added explicit `evidence_sufficiency` and `qualification` fields and tightened the generator contract. A fresh four-query live reproduction then returned four `ACCEPTED` turns with `gate_errors=[]`; generator and verifier each completed four calls in one attempt per row.

Because implementation changed after the V2 holdout, that 30-query set is now `DEV30_COMPAT_V2`, not official unseen holdout evidence. A new post-freeze `HOLDOUT30_V3` must be created and evaluated before Phase 3 can be declared complete. Full D/E/F, five-stage multiturn, DEV50_V3, and fresh HOLDOUT30_V3 evaluation are still pending.

## Baseline and development evidence

- Phase-2 base HEAD: `e64f53b522d683c9a74c55cff07e9a927f7cd01e`
- Phase-2 base tree: `0b28716aa54ab700c43d242b6eb0e26976231a88`
- The controlled Phase-2 dialogue script contains prewritten D/E/F specifications and remains historical regression material. The Phase-3 prompts and runtime contain no Phase-2 prewritten answer strings.
- DEV50 / FROZEN_REGRESSION50 is known development data. Its committed deterministic baseline has type accuracy 0.44, voice accuracy 0.52, page accuracy about 0.366, span accuracy about 0.073, unsupported-premise rejection about 0.333, and robustness 0.10.
- Phase-3 retrieval-only recall@6 on 41 grounded DEV50 rows is 0.3902439024. This is a retrieval metric, not generative accuracy.
- The old HOLDOUT30 is `DEV30_COMPAT`. Its freeze SHA, `2f10c6ebe8a821c7e6635128b99acc84c7941c08`, predates the Codex Exec implementation. Its query and gold contents are unchanged and must not be reported as fresh holdout evidence.

## Live evaluation contract

The runner requires at least three accepted Test D critiques from each Benjamin edition, one accepted Test E Lee response per accepted D, three accepted Test F artifacts of each subtype (ISSUE, GAP, RESEARCH_QUESTION), and the accepted multiturn sequence Benjamin → Lee → Benjamin → Lee → synthesis. Rejected attempts are retained in the artifact. Bounded retries use alternative evidence-bounded queries. The artifact records generator and verifier subprocess-attempt totals for later `REAL_MODEL_CALLS` computation.

Panel generation accepts a query-only file. It freezes the response SHA and records `gold_available_during_generation=false` in the manifest. The separate scoring commands check the frozen SHA before opening gold. The new HOLDOUT30_V2 query-only panel is ready; no new gold or response has been created.
