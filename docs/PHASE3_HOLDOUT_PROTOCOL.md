# Phase 3 Holdout Protocol

DEV50 / FROZEN_REGRESSION50 is known development data. The original HOLDOUT30 is `DEV30_COMPAT`: its freeze SHA (`2f10c6ebe8a821c7e6635128b99acc84c7941c08`) predates the Codex Exec implementation. Its existing query and gold contents remain unchanged and are not a fresh Phase-3 holdout.

`IMPLEMENTATION_FREEZE_SHA_V2=PENDING`. `HOLDOUT30_V2=NOT_CREATED_PRE_FREEZE`. The host must first commit the Phase-3 implementation and record its SHA. Only then may it create the new query-only panel and separate gold artifact, recording creation chronology and the implementation freeze SHA.

Generation reads only a query-only panel and source agents. It does not open gold. After generation, the response manifest records the query SHA, response SHA, generator and verifier models, subprocess-attempt counts, `response_frozen=true`, and `gold_available_during_generation=false`. Scoring is a separate command; it verifies the frozen response hash before opening gold. A failed runtime leaves the holdout unscored.

Suggested categories are author/external attribution, unsupported premise, page trap, paraphrase retrieval, concept neighbor, mixed voice, cross-paper retrieval, and edition trap. Do not use `DEV30_COMPAT` results as `HOLDOUT30_V2` results.
