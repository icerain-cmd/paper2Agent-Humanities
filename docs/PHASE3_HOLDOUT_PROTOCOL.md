# Phase 3 Holdout Protocol

The existing 50-query panel is `DEV50 / FROZEN_REGRESSION50`; it is known development data and is never called a holdout.

A valid HOLDOUT30 may only be created after the Phase-3 implementation is frozen in Git. Its manifest must record `IMPLEMENTATION_FREEZE_SHA` and prove creation chronology. Query-only and gold artifacts remain separate.

During live generation the runtime receives only the query-only HOLDOUT30 plus source agents/evidence. Gold is not provided to the generator path. If no live model runtime is available, HOLDOUT30 may be constructed but cannot produce a holdout model result; that absence must be reported rather than filled with deterministic/manual answers.

Suggested categories: author/external attribution, unsupported premise, page trap, paraphrase retrieval, concept neighbor, mixed voice, cross-paper retrieval, and edition trap.

## Current HOLDOUT30

`evals/phase3/holdout30-query-panel.json` and `holdout30-gold.json` were created only after implementation freeze commit `2f10c6ebe8a821c7e6635128b99acc84c7941c08`. They contain 30 unique queries with zero exact query-string overlap with DEV50. Because the generative runtime is unavailable, no holdout response generation has occurred; `HOLDOUT_GOLD_HIDDEN_DURING_GENERATION` is recorded as `NOT_RUN_NO_LIVE_MODEL_RUNTIME` rather than incorrectly asserted TRUE.
