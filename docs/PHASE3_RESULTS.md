# Phase 3 Results

## Current status

```
PAPER2AGENT_HUMANITIES_PHASE3_STATUS=BLOCKED_NO_LIVE_MODEL_RUNTIME
```

Phase-3 runtime architecture and safety gates are implemented, but no callable generative model endpoint is available to the repository process. Per the Phase-3 contract, no manually authored or deterministic substitute is reported as live scholarly generation.

## Baseline audit

- Phase-2 base HEAD: `e64f53b522d683c9a74c55cff07e9a927f7cd01e`
- Phase-2 base tree: `0b28716aa54ab700c43d242b6eb0e26976231a88`
- Phase-2 controlled `run_phase2_dialogue.py` contains prewritten D/E/F specifications and remains historical regression material.
- Existing source/edition/corpus/publication gates are preserved.

## Runtime availability

`evals/phase3/runtime-status.json` records `BLOCKED_NO_LIVE_MODEL_RUNTIME`. No credentials were discovered, scraped, generated, logged, or committed.

## DEV50 / FROZEN_REGRESSION50

The existing 50-query panel is treated as known development data. It is not a holdout.

The previously committed deterministic behavioral baseline remains:
- type accuracy 0.44
- voice accuracy 0.52
- page accuracy ~0.366
- span accuracy ~0.073
- unsupported-premise rejection ~0.333
- robustness 0.10

Phase-3 retrieval-only evaluation over the 41 grounded DEV50 rows currently reports page retrieval recall@6 = 0.3902439024. This is a retrieval metric, not generative accuracy.

## Live D/E/F

Not executed. A real ModelAdapter is required. There are no Phase-3 critique, response, synthesis, or multiturn artifacts, and no claim of Phase-3 hard-gate success for generated dialogue.

## What is implemented

- provider-neutral ModelAdapter
- explicit no-model blocker
- inspectable BM25-like/alias retrieval
- request classifier
- evidence-first generation packet
- publication verifier
- hardcoded Phase-2 text regression scan
- gold-inaccessibility tests for generation code
- unsupported/partial-support publication tests

The next step is to connect an already authorized callable model runtime without changing the evidence contracts.
