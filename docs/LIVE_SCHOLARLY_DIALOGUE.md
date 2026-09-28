# Live Scholarly Dialogue Runtime

Phase 3 introduces a production path under `paper2humanities/runtime/` that is separate from historical Phase-2 controlled fixtures.

Pipeline:

```
question -> query classification -> inspectable retrieval -> bounded evidence packet
         -> ModelAdapter -> typed turn -> provenance/publication checks -> semantic review
```

The runtime code contains no Phase-2 critique/response/synthesis wording. Historical controlled fixtures remain regression artifacts only.

## Model boundary

Generative execution requires a concrete `ModelAdapter`. The current implementation includes an OpenAI-compatible adapter that uses only an explicitly configured endpoint/model and optional pre-existing API-key environment variable. It never searches credentials, browser state, cookies, PATs, or hidden account data.

No callable generation endpoint/model credential is available in the current execution environment. Therefore the runtime reports `BLOCKED_NO_LIVE_MODEL_RUNTIME`. Deterministic text or manually authored answers are not substituted.

## Evidence packet

The generator receives only the research question, action, actor identity/edition, target, selected proposition IDs/evidence, dialogue history, and output contract. Gold answers and Phase-2 expected wording are not inputs.

## Retrieval

Phase 3 replaces plain token overlap with a small BM25-like inverse-document-frequency score plus concept aliases and grounded-statement preference. Each turn can save candidate IDs/scores, selected statements/evidence, and rejected candidates.

The known DEV50 is a development/regression set, not unseen generalization. Current page retrieval recall@6 over its 41 grounded queries is recorded in `evals/phase3/dev50-retrieval.json`.

## Abstention

The generation contract explicitly permits `INSUFFICIENT_EVIDENCE`, `SOURCE_CONFLICT`, `EDITION_CONFLICT`, `ATTRIBUTION_UNCLEAR`, and `NO_SOURCE_SUPPORTED_RESPONSE`. Unsupported content must not be optimized into a rebuttal.
