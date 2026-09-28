---
name: paper2humanities
description: Add attribution-aware humanities propositions and evidence-bounded scholarly dialogue on top of a reviewed Paper2Skill bundle.
---

# Paper2Humanities

Use this layer only after Paper2Skill has produced a reviewed source bundle. Do not
re-ingest the paper here and do not bypass Paper2Skill page review or source hashes.

## Contract

1. Build or reuse the Paper2Skill review work directory.
2. Create a `PaperEvidenceIndex` from reviewed page JSON.
3. Encode propositions as one of:
   `SOURCE_QUOTE`, `AUTHOR_CLAIM`, `INTERPRETATION`, `AI_SYNTHESIS`,
   `CRITIQUE`, `UNRESOLVED`.
4. Run source validation. `Unsupported AUTHOR_CLAIM` must be zero.
5. For multi-paper work, keep one `PaperAgent` per paper and use
   `ScholarlyDialogue`. A paper agent may answer/criticize only from its own paper
   evidence. Cross-paper synthesis must retain statement IDs from at least two papers.
6. Human review remains required for interpretation, synthesis, critique and research questions.

## Non-negotiable boundaries

- Never convert an interpretation or AI synthesis into `AUTHOR_CLAIM`.
- Never convert a critique into `SOURCE_QUOTE`.
- Never invent page citations.
- Never use a synthesis agent as a winner/loser judge.
- A source quote or author claim without page evidence is invalid.
- If evidence is insufficient or conflicting, preserve `UNRESOLVED`.

## Code

The implementation is in `src/paper2humanities/`. Tests are in `tests/`.
The Lee Yongwook Phase-1 fixture is under `fixtures/`; the original PDF is not
committed. Its source SHA-256 and Google Drive identity are recorded instead.
