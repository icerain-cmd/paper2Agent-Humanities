# Phase 3 Holdout Protocol

## HOLDOUT30 V5 preregistration

Before any V5 generation, `skills/paper2agent/paper2humanities/evals/phase3/holdout30-v5-pass-contract.json` fixes the pass criteria: every hard-gate count must be zero (including `WRONG_SOURCE_ID` and `STALE_SEMANTIC_REVIEW`), exact-match accuracy at least 0.90, source-id accuracy at least 0.95, unsupported-premise rejection at least 0.90, false-author-claim count zero, and fake-page-citation count zero. The reusable evaluator is `paper2humanities.runtime.pass_contract.evaluate_pass_contract`. V5 gold records must contain the expected `source_id`; generated response rows record the selected Paper Agent's `source_id`. A V5 score also requires a separate `responses.semantic-review.json` sidecar with the frozen response SHA and `reviewed_query_ids` covering every query. No HOLDOUT30 V5 panel, responses, gold, or score has been created.

## HISTORICAL PHASE STATE

DEV50 / FROZEN_REGRESSION50 is known development data. The original HOLDOUT30 is `DEV30_COMPAT`: its freeze SHA (`2f10c6ebe8a821c7e6635128b99acc84c7941c08`) predates the Codex Exec implementation. Its existing query and gold contents remain unchanged and are not a fresh Phase-3 holdout.

`IMPLEMENTATION_FREEZE_SHA_V2=006845917201f701e5d0c5f00dff56a2d2b8a2e7`. The evaluated V2 30-query set is now reclassified as `DEV30_COMPAT_V2` because implementation changed after it was scored. Its original internal panel IDs and file contents are preserved for auditability; only the repository file names and a reclassification manifest identify its current development-only role. It must never be reported as unseen holdout evidence after repair commit `226a5bd`.

For V3, freeze the implementation first and record `IMPLEMENTATION_FREEZE_SHA_V3`. Only after that commit may `HOLDOUT30_V3` be created. Required chronology is: freeze query panel → record query SHA → live generation with no gold access → freeze responses → record response SHA → only then create/reveal gold → score. The generation process must not open any gold path and the response manifest must record `gold_available_during_generation=false`.

`HOLDOUT30_V3` must contain 30 queries with zero exact overlap against DEV50, DEV30_COMPAT_V2, and prior live D/E prompts. Categories should cover author/external attribution, unsupported premise, page retrieval, paraphrase, mixed voice, edition trap, cross-paper comparison, abstention, critique, and response. Meaning-level overlap should also be reviewed manually where practical.

Generation reads only the query-only panel and source agents. Scoring is a separate command and must verify the frozen response hash before reading gold. A failed runtime leaves the holdout unscored.
