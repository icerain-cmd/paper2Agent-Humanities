# Phase 3 Results

## Current status

`PHASE3_STATUS=COMPLETE`.

The authoritative Phase 3 state is recorded in:

- `skills/paper2agent/paper2humanities/evals/phase3/runtime-status.json`
- `skills/paper2agent/paper2humanities/evals/phase3/phase3-v4-final-report.json`
- `skills/paper2agent/paper2humanities/evals/phase3/holdout30-v4-score.json`

Final evaluated HEAD before this documentation-only sync: `f195280`.

## Final live scholarly dialogue result

The final live dialogue contains 32 runs:

- accepted: 26
- abstained: 6
- every abstention has insufficient evidence: **true**

Required dialogue gates are complete:

- Test D: **6 accepted**
  - Benjamin V2: **3**
  - Benjamin V3: **3**
- Test E: **6 accepted**
- Test F:
  - ISSUE: **3**
  - GAP: **3**
  - RESEARCH_QUESTION: **3**
- Multiturn sequence: **5 accepted**

The final live-dialogue status is **PASS**.

## Fresh HOLDOUT30 V4

The official fresh holdout is `phase3-holdout30-v4`.

Result:

- queries: **30**
- matches: **28/30**
- accuracy: **0.9333333333**
- accepted: **22**
- abstained: **8**
- rejected: **0**
- every abstention has insufficient evidence: **true**
- status: **PASS**

The V4 chronology is preserved as:

1. implementation freeze: `e9051f58f1de6d8d0fbce6587b2ba10e5b589ccd`
2. panel freeze commit: `032796a1017da43bf935309a0cf7a7bb9b1651f8`
3. response freeze commit: `420db56a42f8f82d8771a18f7a53cd537eee4734`
4. gold creation commit: `5b99d686b3fbc8f2edc39b3faa7fb5c10ab5b03d`

Integrity records:

- panel SHA-256: `06a051c03653cd04ac06b5e609ecfe7f8a432d683b3f2926a91a51d08e282a9d`
- response SHA-256: `a36711d2807d5f98c00290873b91c6aed9d5443d40c8dce4c199c284cff5f2c8`
- gold SHA-256: `a0de2efb4f83fcade3b3136595a7868145c7dacabe72c2ac3fd83c6d74369ed8`
- gold available during generation: **false**
- gold created after response freeze: **true**
- exact overlap with prior development/live prompts: **0**
- gold leakage: **0**

## HOLDOUT30 V4 mismatches

There are exactly two non-hard-gate mismatches.

### H30V4-001

- frozen gold type: `AUTHOR_CLAIM`
- actual type: `SOURCE_QUOTE`
- actual page: **22**
- cause: the runtime classified an exact author quotation as `SOURCE_QUOTE`, while the frozen gold expected `AUTHOR_CLAIM`.
- page and support are correct.

### H30V4-009

- frozen gold type: `AUTHOR_CLAIM`
- actual type: `SOURCE_QUOTE`
- actual page: **12**
- cause: the runtime classified an exact author quotation as `SOURCE_QUOTE`, while the frozen gold expected `AUTHOR_CLAIM`.
- page and support are correct.

These are type-label differences only. They do not trigger a Phase 3 hard gate, and the frozen gold was not changed after scoring.

## Final hard gates

All required hard gates are zero:

| Hard gate | Count |
|---|---:|
| `FALSE_AUTHOR_CLAIM` | 0 |
| `EXTERNAL_AS_AUTHOR_ERROR` | 0 |
| `CROSS_EDITION_CONTAMINATION` | 0 |
| `UNSUPPORTED_DIALOGUE_TURN` | 0 |
| `TEMPORAL_CORPUS_CONTAMINATION` | 0 |
| `FAKE_PAGE_CITATION` | 0 |
| `HARDCODED_DIALOGUE_TEXT` | 0 |
| `GOLD_LEAKAGE` | 0 |

`FINAL_HARD_GATES_PASS=true`.

## Verification

Final recorded test results:

- Humanities / Phase 3 pytest: **79 passed, 0 failed**
- Paper2Skill upstream unittest: **27 passed, 0 failed**
- total: **106 passed**

No tests are rerun as part of this documentation-only synchronization.

## Historical development record

The following results are retained as history and must not be read as the current Phase 3 state.

### V2 repair stage

The V2 evaluation exposed four `UNSUPPORTED_DIALOGUE_TURN` failures. The implementation was repaired so that evidence sufficiency and qualification were represented consistently across generation, schema validation, and publication gating. Once implementation changed, that V2 panel ceased to be valid unseen holdout evidence and was retained only as development compatibility data.

### V3 development stage

The former `HOLDOUT30_V3` was inspected during mismatch diagnosis and therefore was reclassified as `DEV30_COMPAT_V3`. It is not official holdout evidence.

The V3 repair work addressed multilingual retrieval tie truncation, named cross-paper evidence supply, claim-level typing, comparison/interpretation classification, and score-time allowed-corpus validation. The repaired ten-row development composite reached accuracy 1.0 with all hard gates zero, but remains development-only evidence.

### Final V4 stage

Only the post-freeze `HOLDOUT30_V4` is the official fresh Phase 3 holdout. Its result is **28/30, accuracy 0.9333333333, PASS**, with all eight hard gates equal to zero.

## Final determination

`PAPER2AGENT_HUMANITIES_PHASE3_STATUS=COMPLETE`.

PR #3 remains a Draft review PR and is not merged by this Phase 3 work order.
