# Paper2Agent-Humanities User Manual

> **Status:** Experimental humanities extension. The Paper2Agent base is on `main`; evidence-bounded Paper2Humanities dialogue features are under development and review in Draft PRs. Always verify primary sources before citation or publication.

## 1. Purpose

Paper2Agent-Humanities is a research environment for turning papers into **source-bounded Paper Agents** and placing claims, concepts, and interpretations from different papers into structured scholarly dialogue.

The humanities layer distinguishes:

- `SOURCE_QUOTE`: direct source text
- `AUTHOR_CLAIM`: a claim demonstrably attributable to the author
- `INTERPRETATION`: scholarly interpretation
- `AI_SYNTHESIS`: AI-generated synthesis across evidence
- `CRITIQUE`: criticism
- `UNRESOLVED`: insufficient, conflicting, or open evidence

The governing principle: **preserve who actually said what, in which source, before optimizing for fluent AI output.**

## 2. Getting started

### Requirements
Git, Python, a skill/shell-capable coding agent such as Claude Code or Codex, and the paper PDF or authoritative source.

```bash
git clone https://github.com/icerain-cmd/paper2Agent-Humanities.git
cd paper2Agent-Humanities
```

For stable upstream functionality, follow the root `README.md` and `skills/paper2agent/SKILL.md`. Inspect the relevant Draft PRs for experimental Paper2Humanities features.

### Recommended sequence

1. Acquire the authoritative source.
2. Use **Paper2Skill first** for ingestion, page review, and source-hash verification.
3. Build a Paper Agent from the reviewed source bundle.
4. Type propositions with the six categories above.
5. Validate page evidence for every `SOURCE_QUOTE` and `AUTHOR_CLAIM`.
6. Keep **one Paper Agent per paper/source** in multi-paper research.
7. Run critique and response, then re-check primary evidence.
8. Treat synthesis and research questions as AI outputs requiring human judgment.

## 3. Non-negotiable boundaries

### One agent, one bounded corpus
A Paper Agent should represent an author only through evidence in its assigned paper. Do not silently inject other papers, later writings, web knowledge, or general model knowledge.

### Keep editions separate
Different editions should remain separate sources when differences matter. The Benjamin experiments in this project keep V2 and V3 as independent Paper Agent sources.

### Separate author claims from interpretation
- “The author argues X.” → `AUTHOR_CLAIM`; source evidence required.
- “This passage can be interpreted as X.” → `INTERPRETATION`.
- “Reading A and B together suggests C.” → `AI_SYNTHESIS`.

A compelling AI interpretation does not become an author claim.

### Allow the system to stop
When evidence is insufficient or conflicting, preserve `UNRESOLVED`. Filling gaps with plausible prose is not scholarship.

## 4. Core research workflows

### A. Deep-read one paper
Ask for central propositions with pages, direct evidence, concepts in context, premises and conclusions, what the paper does **not** explicitly claim, and passages requiring interpretation. The goal is an **argument map**, not merely a summary.

### B. Compare two papers
Start with one shared research question. Require each agent to answer from its own source. Preserve provenance when identifying similarities, differences, and conceptual asymmetries.

### C. Scholarly debate
Recommended sequence:

1. **POSITION** — source-grounded position
2. **CRITIQUE** — assumptions, gaps, or tensions
3. **REBUTTAL** — response within the agent's own evidence
4. **REVISION** — what can change and what remains
5. **CLOSING** — agreements, disagreements, new research questions

For research, prefer “According to evidence in this edition...” over unconstrained role-play such as “Benjamin would say...”.

### D. Debate with 2–3 papers
Keep discussion issue-centered and preserve source identity for each substantive turn. The synthesis agent is **not a judge**. Ask it for shared problems, unresolved differences, gaps between literatures, claims needing verification, and follow-up research questions.

## 5. A practical guide for humanities scholars

### 1) Let another theory attack your own paper
Turn your paper into an agent and expose it to critique from a classical or competing theoretical paper. This can reveal assumptions and conceptual leaps hidden by familiarity.

### 2) Ask “Where do they diverge?” before “Who is right?”
The precise point at which concepts diverge may be more valuable than an artificial winner.

### 3) Capture moments of Atura
When an unexpected connection or momentary insight emerges, do not immediately promote it to a conclusion. Save it as a research memo.

Record:
- which statements or concepts triggered it,
- which sources were involved,
- whether AI proposed the connection or the researcher recognized it,
- whether primary-source evidence can support it,
- what additional literature is needed.

**The generation of insight and the validation of insight are different stages.**

### 4) Preserve disagreement deliberately
Do not force incompatible theories into consensus. An `UNRESOLVED` disagreement can be more productive than synthetic harmony.

### 5) Use the system to generate questions
Ask: What remains unanswered by both texts? Which concept is shared but differently defined? Does one theory expose a blind spot in the other? Do edition or historical changes alter the argument?

### 6) Treat AI as a research environment, not an author simulator
A Paper Agent does not reproduce an author's consciousness or intention. It is a **research interface that generates bounded utterances from reviewed textual evidence**.

## 6. Pre-research checklist

- [ ] Do quotations and page numbers match the primary source?
- [ ] Has an interpretation been mislabeled as `AUTHOR_CLAIM`?
- [ ] Have different editions been mixed?
- [ ] Has another paper's claim been attributed to the wrong author?
- [ ] Is AI synthesis being mistaken for scholarly consensus?
- [ ] Is each rebuttal supported by the responding paper?
- [ ] Is insufficient evidence preserved as `UNRESOLVED`?
- [ ] Have novelty and prior literature for new questions been checked separately?
- [ ] Has the researcher reviewed the final interpretation and judgment?

## 7. Implementation status and citation

Paper2Humanities is being developed as a sidecar extension rather than a rewrite of the upstream core. The public `main` remains close to upstream Paper2Agent, while Humanities functionality is layered through Draft PRs. This guide documents the project's research philosophy and validated workflow; it does **not** imply that every experimental feature is available from `main` as a single command.

When using the project in research, cite the original Paper2Agent/Nature work as appropriate. When reporting use of this Humanities fork, record the commit/branch, source editions, models, prompts/protocol, and human-review procedure.

**AI-generated dialogue does not replace the source. The primary text remains the final evidentiary authority.**
