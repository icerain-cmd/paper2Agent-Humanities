# Phase 3 hard-gate repair v3

## Scope
- Branch: `feat/phase3-live-scholarly-dialogue`
- Runtime: PC2 `DESKTOP-GA4FNS2`, Codex exec
- Generator: `gpt-6-sol`
- Verifier: `gpt-5.6-sol`, fresh ephemeral context, independent model
- Prior hard gate source: `holdout30-v2-final-score.json`
- Prior value: `UNSUPPORTED_DIALOGUE_TURN=4`
- Exact rows: `H30V2F-005`, `006`, `012`, `013`

## Diagnosis
All four rows had the required primary evidence in retrieval top-k. None is a retrieval miss.
The generator correctly returned a bounded partial answer: it supported the clause available in evidence and explicitly refused the unsupported clause.
However, `publication_gate()` required a non-empty `qualification` for `PARTIALLY_SUPPORTED`, while `typed_turn.schema.json` used `additionalProperties:false` and did not permit a `qualification` field.
Therefore a model could not produce a structurally valid qualified partial turn that also satisfied the publication gate.

Failure classification:
- H30V2F-005: EVIDENCE_TOO_WEAK + OTHER(PUBLICATION_GATE_SCHEMA_CONTRACT_MISMATCH)
- H30V2F-006: EVIDENCE_TOO_WEAK + OTHER(PUBLICATION_GATE_SCHEMA_CONTRACT_MISMATCH)
- H30V2F-012: EVIDENCE_TOO_WEAK + OTHER(PUBLICATION_GATE_SCHEMA_CONTRACT_MISMATCH)
- H30V2F-013: EVIDENCE_TOO_WEAK + OTHER(PUBLICATION_GATE_SCHEMA_CONTRACT_MISMATCH)

Failure-stage summary:
- RETRIEVAL_MISS=0
- WRONG_EVIDENCE_SELECTED=0
- OVERGENERALIZATION=0
- UNSUPPORTED_BRIDGE=0
- OTHER=4
## Minimal repair
1. Added typed fields `evidence_sufficiency` and `qualification` to the live output schema.
2. Live schema now requires both fields.
3. `PARTIALLY_SUPPORTED` live output requires a non-empty explicit qualification.
4. `UNRESOLVED` requires `INSUFFICIENT` or `CONFLICTING` sufficiency and null qualification.
5. Generator contract now instructs the model to emit `SUFFICIENT/PARTIAL/INSUFFICIENT/CONFLICTING` and a bounded qualification.
6. Python validator remains backward-compatible with legacy manually-constructed test turns; the live schema still enforces the new fields.

## Verification
- Full unit/regression suite: `72 passed`.
- Fresh dev reproduction panel: `dev4-hardgate-repro-v3.json`.
- Actual live model calls: generator=4, verifier=4.
- Generator subprocess attempts: 4 total (1 per row).
- Verifier subprocess attempts: 4 total (1 per row).
- Outcomes after repair:
  - H30V2F-005: ACCEPTED, gate_errors=[]
  - H30V2F-006: ACCEPTED, gate_errors=[]
  - H30V2F-012: ACCEPTED, gate_errors=[]
  - H30V2F-013: ACCEPTED, gate_errors=[]
- Fresh-context verifier=true; independent-model verifier=true.

## Remaining boundary
This repair proves the exact four prior hard-gate cases no longer fail the publication gate.
It does **not** by itself declare Phase 3 COMPLETE.
The old HOLDOUT30_V2 is development/compatibility evidence after this code change.
A new post-freeze HOLDOUT30_V3 plus full D/E/F and five-stage multiturn run is still required before COMPLETE can be declared.
