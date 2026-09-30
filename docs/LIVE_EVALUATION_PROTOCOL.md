# Live Evaluation Protocol

## Scope

Phase 2 separates three evaluation scopes:

1. `CURATED_FIXTURE`: deterministic validation of the 11 committed Lee statements.
2. `COMMITTED_BLIND_RESPONSE_SET`: scoring a previously frozen response artifact against the reviewed 50-query gold panel.
3. `LIVE_BLIND_RUN`: response generation happens after receiving only the query-only panel, reviewed Paper2Skill evidence, and the frozen Paper Agent artifact. The response artifact is hashed and frozen before gold is opened.

Only the third scope measures a fresh behavioral run.

## Runtime boundary

The live runner creates a temporary workspace containing only:

```
query-panel.json
source/reviewed-source.json
agent/paper-agent.json
output/
```

The response generator CLI accepts only `--queries`, `--source`, `--agent`, and `--output`. It has no gold argument. The parent runner opens the gold panel only after the response file has been copied to the persistent run directory and SHA-256 has been recorded.

This is an execution-boundary safeguard, not an OS-level chroot. The run manifest therefore records:

```
gold_available_during_response_generation=false
external_blind=false
```

## Inference mode

No external model/API runtime was available to the repository process during this Phase-2 pass. Therefore the implementation is explicitly:

```
LIVE_EVAL_MODE=DETERMINISTIC_BEHAVIORAL_EVAL
```

It is not called `LIVE_AGENT_EVAL`. The generator performs lexical evidence retrieval over reviewed Paper2Skill page items and conservative attribution classification. It does not copy the committed response artifact.

## Run provenance

Each run records:

- run_id and UTC timestamp
- git commit
- query panel SHA-256
- source PDF SHA-256
- Paper Agent artifact SHA-256
- frozen response artifact SHA-256
- Python runtime
- model/host-agent identity
- gold exposure flag
- external-blind flag
- generation method

## Live-run reporting

Each official run is committed under `skills/paper2agent/paper2humanities/evals/live_runs/<run_id>/` with `manifest.json`, frozen `responses.json`, and `score.json`. Failed cases are retained. A run is only treated as official when the runner/generator code is already committed and the run manifest identifies that commit.

## Negative controls

Mutation tests deliberately alter correct answers:

- AUTHOR voice -> EXTERNAL
- EXTERNAL voice -> AUTHOR
- correct page -> wrong page
- correct span -> wrong span
- UNRESOLVED -> AUTHOR_CLAIM
- INTERPRETATION -> AUTHOR_CLAIM
- V2 edition -> V3 edition

Every mutation must reduce the relevant metric and/or trip a hard gate.

## Interpretation

The live result must not be averaged together with the committed-response 1.0 result. They measure different boundaries. Future model-backed evaluation may add `LIVE_AGENT_EVAL`, but only if a real inference runtime is invoked with the same gold-isolation contract.

## Official Phase-2 boundary run

Committed run: `lee-aura-live-20260928T041757Z` at generator code commit `2194ab86eaf9f39e7b589ec783ab84371e940a7c`.

- mode: `DETERMINISTIC_BEHAVIORAL_EVAL`
- external blind: `false`
- gold available during response generation: `false`
- query panel SHA-256: `c411bac58b82e8bfd5e1ca6b94dce37b2f7586c87249209063f237c150ba42b9`
- response artifact SHA-256: `356762e7015941e5e31e266b9410f4fcd7b6fd249191fc6550e00aeea8d9df18`
- Attribution Type Accuracy: 0.44
- Evidence Voice Accuracy: 0.52
- Page Accuracy: 0.3658536585
- Evidence Span Accuracy: 0.0731707317
- Unsupported Claim Rejection Rate: 0.3333333333
- False AUTHOR_CLAIM: 5
- External-as-Author Error: 4
- Interpretation Promotion Error: 0
- Cross-edition contamination: 0
- Adversarial Robustness Rate: 0.10

The 45 failed rows remain in the committed score artifact. This result supersedes any interpretation of the committed 1.0 response-set score as live behavioral performance.
