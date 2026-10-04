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


## 7. Hands-on: run a real Live Debate

The general Live Debate runtime currently lives on **`feat/live-agent-debate`**, not stable `main`. The commands below reflect files and options verified in the repository.

### 7.1 Prepare the experimental branch

```bash
git clone https://github.com/icerain-cmd/paper2Agent-Humanities.git
cd paper2Agent-Humanities
git switch feat/live-agent-debate
```

A working Codex installation and model access are required. The runner looks for `codex` on PATH and then `~/.local/bin/codex`.

### 7.2 Included sample agents

The current fixtures include Benjamin V2, Benjamin V3, and Lee Aura 2019 agents under:

```text
skills/paper2agent/paper2humanities/fixtures/
```

Benjamin V2 and V3 remain separate sources because edition identity is part of the evidence boundary.

### 7.3 Run a Benjamin–Lee debate

From the repository root:

```bash
python skills/paper2agent/paper2humanities/scripts/run_live_debate.py \
  --agents benjamin-artwork-v2 lee-aura-2019 \
  --topic "How should technological reproduction and the transformation of aura be understood?" \
  --turns 8 \
  --json-out debate-result.json
```

The current runner defaults to `gpt-6-sol` and **8 total turns**. Eight turns means eight turns across the session, not eight turns per agent.

To select another available model:

```bash
python skills/paper2agent/paper2humanities/scripts/run_live_debate.py \
  --agents benjamin-artwork-v3 lee-aura-2019 \
  --topic "How are concentration, distraction, and technological media related?" \
  --turns 10 \
  --model <AVAILABLE_MODEL_ID> \
  --json-out debate-result.json
```

Each turn prints the agent, action, text, and evidence IDs/pages. `ABSTAIN` can be a correct outcome when evidence is insufficient.

### 7.4 Save a research memo

Preserve the JSON session and create a separate research memo containing:

```text
Research question:
Agents / editions:
Debate session file:
Core conflict:
Strongest critique:
Possible revision to my argument:
Atura candidate:
Primary-source checks:
Additional literature:
Final researcher judgment:
```

Keep **Atura candidates** separate from conclusions. A momentary insight is the beginning of a hypothesis, not validated knowledge.

### 7.5 Local API and web assets

The experimental branch includes a local API runner:

```bash
python skills/paper2agent/paper2humanities/scripts/serve_debate_api.py \
  --host 127.0.0.1 \
  --port 8765
```

The default port is `8765`. Web assets live under:

```text
skills/paper2agent/paper2humanities/web/
```

Treat this as experimental branch functionality, not a production-stable public service.

## 8. Adding your own paper

It is important to distinguish what is automated from what still requires scholarly preparation.

The repository has a general runtime for debating registered fixture agents. It does **not** yet expose a stable one-command workflow on `main` that turns any humanities PDF into a fully registered debate agent.

### 8.1 Verify the source first

Do not turn a raw PDF directly into role-play. Use Paper2Skill first to preserve page review and source identity.

A useful coding-agent instruction is:

```text
Process this paper with Paper2Skill.
Preserve page review and source hashes, and prepare a reviewed source bundle
for a humanities Paper Agent. Separate author claims from interpretation.
Do not invent claims or page references that cannot be verified.

Paper: <PDF_OR_ACCESSIBLE_SOURCE>
Workspace: <PROJECT_DIR>
```

### 8.2 Minimum requirements for a new Paper Agent

Before debate, require:

- unique `paper_id / agent_id`,
- accurate author, paper, and edition identity,
- reviewed evidence index,
- evidence statement IDs,
- real page references,
- separation of `AUTHOR_CLAIM` and `INTERPRETATION`,
- an explicit allowed-corpus boundary.

Apply the same standard even when the paper is your own.

### 8.3 Validate alone before debate

Ask the new agent to:

1. state three central claims with pages,
2. identify three things the paper does not explicitly claim,
3. distinguish interpretive passages from direct author claims,
4. abstain or mark `UNRESOLVED` when evidence is absent.

Do not promote an agent to multi-agent debate if it produces false attribution or fake pages.

### 8.4 Start with two agents

Begin with **two agents and one precise issue**, then add a third paper after the debate is stable.

Good topics ask where concepts diverge, what one theory explains that another cannot, or which proposition would need revision after a source-grounded critique.

Avoid “Who is greater?”, “What would these authors think about AI today?”, or “Debate freely.” Such prompts invite role-play and general model knowledge beyond the source corpus.

## 9. Turning debate into scholarship

Live Debate is not itself a research result. Use three stages:

**Discovery → Verification → Researcher judgment**

### Discovery
Find unexpected connections, objections, and Atura candidates in the friction between agents.

### Verification
Return to the evidence IDs and primary-source pages. Add relevant secondary literature when needed.

### Researcher judgment
Decide whether the connection is merely verbal similarity or a defensible conceptual relation. In publication, do not cite AI debate as scholarly authority; rebuild the argument from primary sources, prior scholarship, and your own reasoning.

Used this way, Paper2Agent-Humanities is not an “AI that writes the paper for you.” It is **a research environment in which scholars design friction between texts and discover new questions**.

## 10. Implementation status and citation

Paper2Humanities is being developed as a sidecar extension rather than a rewrite of the upstream core. The public `main` remains close to upstream Paper2Agent, while Humanities functionality is layered through Draft PRs. This guide documents the project's research philosophy and validated workflow; it does **not** imply that every experimental feature is available from `main` as a single command.

When using the project in research, cite the original Paper2Agent/Nature work as appropriate. When reporting use of this Humanities fork, record the commit/branch, source editions, models, prompts/protocol, and human-review procedure.

**AI-generated dialogue does not replace the source. The primary text remains the final evidentiary authority.**
