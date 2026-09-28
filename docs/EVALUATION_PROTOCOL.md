# Evaluation Protocol

## Two evaluation scopes

Paper2Agent-Humanities reports two deliberately separate scopes.

### CURATED_FIXTURE

The Phase-1 Lee PoC contains 11 selected statements: 6 `AUTHOR_CLAIM`, 4 `SOURCE_QUOTE`, and 1 `INTERPRETATION`. Its deterministic checks measure whether those registered statements preserve source/page provenance and epistemic typing. They are `FIXTURE_VALIDATION`, not full-paper behavioral accuracy.

### BLIND_ADVERSARIAL_PANEL

Phase 1.5 uses a separate query panel that does not reuse the 11 fixture statements as answer keys. Queries probe new attribution decisions, misleading premises, embedded quotations, interpretation promotion, neighboring concepts, wrong pages, and mixed voices.

## Panel construction provenance

Independent agent spawning was unavailable in this execution environment, so roles are temporally separated and recorded:

1. **Evaluator A / query author** writes the query-only blind panel without gold labels.
2. **Evaluator B / source reviewer** returns to the reviewed 31-page Paper2Skill source and assigns gold labels and evidence.
3. **Evaluator C / adjudicator** checks label/source/page consistency and resolves disputed items before the panel is marked reviewed.
4. A behavior-response pass is kept separate from gold scoring. The repository records this limitation; the procedure is not claimed to be a truly independent human-blind study.

The committed 11-statement fixture is not used as the gold source for the panel. Gold evidence is checked against the reviewed PDF/page extraction.

## Required gold fields

Each gold record contains:

- `query_id`
- `query`
- `expected_type`
- `expected_voice`
- `expected_source`
- `expected_page`
- `allowed_answer_types`
- `forbidden_answer_types`
- `gold_evidence_span`
- `adversarial_category`
- `review_status`

An unsupported or absent premise may legitimately have no page/span; its gold record must explain that the full reviewed paper was checked and the safe type is `UNRESOLVED`.

## Metrics

Behavioral evaluation reports the metrics separately rather than collapsing them into one score:

- Attribution Type Accuracy
- Evidence Voice Accuracy
- Page Accuracy
- Evidence Span Accuracy
- Unsupported Claim Rejection Rate
- False AUTHOR_CLAIM Rate
- External-as-Author Error Rate
- Interpretation Promotion Error Rate
- Adversarial Robustness Rate

Hard gates:

```
FALSE_AUTHOR_CLAIM = 0
EXTERNAL_AS_AUTHOR_ERROR = 0
```

A high score is not interpreted as general paper-level accuracy. The panel is finite, reviewed, and reproducible; failures remain in the report.

## Phase boundary

Phase 1.5 does not execute Lee ↔ Benjamin critique, Lee response, or cross-paper gap generation. Those are Phase 2 tasks after separate Benjamin V2/V3 source approval.
