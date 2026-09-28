# Phase 3 Results

## Current status

`PHASE3_STATUS=IMPLEMENTED_AWAITING_FREEZE_AND_LIVE_EVALUATION`. Phase 3 is not complete.

The host independently verified `PC2_RUNTIME=PASS`, `REAL_MODEL_SMOKE=PASS`, and `ISOLATED_RUNTIME_SMOKE=PASS` with Codex `0.155.1`. Schema-constrained ephemeral read-only calls passed for generator `gpt-6-sol` and verifier `gpt-5.6-sol`. The verifier is an independent model invocation with fresh context containing the candidate turn and supplied evidence only. These are host runtime facts; this workspace did not run `codex exec`.

`IMPLEMENTATION_FREEZE_SHA_V2=PENDING` until the host creates a commit. `HOLDOUT30_V2=NOT_CREATED_PRE_FREEZE`. Live D/E/F, multiturn, DEV50 generation and HOLDOUT30_V2 scoring remain `NOT_RUN`. No Phase-3 hard-gate success is claimed.

## Baseline and development evidence

- Phase-2 base HEAD: `e64f53b522d683c9a74c55cff07e9a927f7cd01e`
- Phase-2 base tree: `0b28716aa54ab700c43d242b6eb0e26976231a88`
- The controlled Phase-2 dialogue script contains prewritten D/E/F specifications and remains historical regression material. The Phase-3 prompts and runtime contain no Phase-2 prewritten answer strings.
- DEV50 / FROZEN_REGRESSION50 is known development data. Its committed deterministic baseline has type accuracy 0.44, voice accuracy 0.52, page accuracy about 0.366, span accuracy about 0.073, unsupported-premise rejection about 0.333, and robustness 0.10.
- Phase-3 retrieval-only recall@6 on 41 grounded DEV50 rows is 0.3902439024. This is a retrieval metric, not generative accuracy.
- The old HOLDOUT30 is `DEV30_COMPAT`. Its freeze SHA, `2f10c6ebe8a821c7e6635128b99acc84c7941c08`, predates the Codex Exec implementation. Its query and gold contents are unchanged and must not be reported as fresh holdout evidence.

## Live evaluation contract

The runner requires at least three accepted Test D critiques from each Benjamin edition, one accepted Test E Lee response per accepted D, three accepted Test F artifacts of each subtype (ISSUE, GAP, RESEARCH_QUESTION), and the accepted multiturn sequence Benjamin → Lee → Benjamin → Lee → synthesis. Rejected attempts are retained in the artifact. Bounded retries use alternative evidence-bounded queries. The artifact records generator and verifier subprocess-attempt totals for later `REAL_MODEL_CALLS` computation.

Panel generation accepts a query-only file. It freezes the response SHA and records `gold_available_during_generation=false` in the manifest. The separate scoring commands check the frozen SHA before opening gold. No `HOLDOUT30_V2` panel or gold has been created.
