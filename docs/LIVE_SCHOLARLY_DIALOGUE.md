# Live Scholarly Dialogue Runtime

Phase 3 has an experimental live path under `paper2humanities/runtime/`, separate from historical Phase-2 controlled fixtures.

Pipeline:

```
question -> query classification -> inspectable retrieval -> bounded evidence packet
         -> ModelAdapter -> typed turn -> provenance/publication checks -> semantic review
```

The runtime code contains no Phase-2 critique/response/synthesis wording. Historical controlled fixtures remain regression artifacts only.

## Model boundary

Generative execution uses a concrete Codex Exec adapter and a separate verifier model. The completed live Phase 3 dialogue and historical valid HOLDOUT30 V4 result are documented in `PHASE3_RESULTS.md`. A missing model runtime still produces an explicit `BLOCKED_NO_LIVE_MODEL_RUNTIME` outcome.

## Evidence packet

The generator receives only the research question, action, actor identity/edition, target, selected proposition IDs/evidence, dialogue history, and output contract. Gold answers and Phase-2 expected wording are not inputs.

## Retrieval

Phase 3 uses inverse-document-frequency scoring plus concept aliases and grounded-statement preference. The live panel classifies each raw query before retrieval. Retrieval respects action and edition, and returns an empty packet when no lexical or conceptual term overlaps; insufficient evidence requires abstention. Each turn saves candidate IDs/scores, selected evidence, and rejected candidates.

The known DEV50 is a development/regression set, not unseen generalization. Current page retrieval recall@6 over its 41 grounded queries is recorded in `evals/phase3/dev50-retrieval.json`.

## Abstention

The generation contract requires `UNRESOLVED` on insufficient evidence. Unsupported content must not be optimized into a rebuttal.
