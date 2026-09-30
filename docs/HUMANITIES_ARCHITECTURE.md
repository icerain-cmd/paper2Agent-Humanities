# Paper2Agent-Humanities Architecture

## Decision

Paper2Agent-Humanities is a **sidecar extension**, not a rewrite of Paper2Skill or Paper2MCP.
The reviewed Paper2Skill work directory remains the source-verification boundary.
`paper2humanities` starts after that boundary and adds typed propositions, attribution validation,
evidence-bounded paper identity, scholarly dialogue, and evaluation.

This minimizes upstream drift: `paper2skill/` and `paper2mcp/` remain intact and future upstream merges
do not need to reconcile a modified extraction/runtime core.

## Upstream audit baseline

Audited upstream: `jmiao24/Paper2Agent` at `8c2d059165ef8cdcb70dbea76655b9c2b55b38e6`.

### Paper2Skill

The supported interface is `paper2skill/scripts/paper_bundle.py`. `prepare` snapshots inputs and records
SHA-256 identity; `extract` creates per-page state; `review-aid` creates contact sheets and a review queue;
`build` creates the paper skill; `verify --strict` enforces review and artifact integrity.

PDF and supplement pages retain page identity. Figures/tables retain page/bounding-box provenance.
Spreadsheet export preserves coordinates and relevant workbook metadata and is rechecked against the snapshot.
Review reuse is permitted only when the source SHA-256 matches. Exact diagnostic adjudications are
fingerprinted, so changed diagnostics invalidate old adjudications.

Generated skills contain compact paper/supplement Markdown and extracted assets. Review evidence remains
outside the delivery. Paper2Humanities therefore does **not** build a second PDF parser.

### Paper2MCP

Paper2MCP maps real research repositories to tested MCP tools. Exposed tools must bind to actual repository
functions found through tutorials, README/API/examples/tests; invented scientific algorithms are prohibited.
Routing supports Python, R, and CLI repositories. Workflow state, fresh-process runtime calls, schemas, and
acceptance cases are explicitly verified.

### Existing routing

- paper files -> Paper2Skill
- research code -> Paper2MCP
- both -> both, in separate work directories, then combined delivery

Paper2Humanities is orthogonal: it consumes a **reviewed Paper2Skill evidence boundary** and does not alter
paper-only/code-only/combined routing.

### Tests and installation

The audited upstream Paper2Skill regression suite has 27 tests; Phase 1 ran all 27 successfully.
Paper2MCP uses workflow/runtime verification scripts plus generated acceptance tests.

The entire `skills/paper2agent/` tree is installed. Current documented locations:
- Claude Code: `~/.claude/skills/paper2agent/`
- Codex: `~/.agents/skills/paper2agent/`

## Humanities extension

```text
Paper / Supplement -> Paper2Skill -> reviewed page evidence + SHA-256
                                      |
                                      v
                               paper2humanities
                        schema / provenance / PaperAgent
                        dialogue / validation / evaluation
                                      |
                                      v
                               Researcher review
```

Implementation: `skills/paper2agent/paper2humanities/`.

## Boundaries

1. Paper2Skill owns ingestion, extraction, page review, hashes and artifact checks.
2. Paper2Humanities owns epistemic statement types and attribution rules.
3. A PaperAgent retrieves only propositions registered to its paper.
4. `CRITIQUE`, `RESPOND`, and source-bounded `QUESTION` use only the actor paper's evidence.
5. Cross-paper compare/synthesis/gap/question requires provenance from at least two papers.
6. There is no winner/loser or judge action.
7. Interpretations, syntheses, critiques and generated questions are never silently promoted to author claims.

## Trade-off

Phase 1 uses a small deterministic proposition registry instead of automatic large-scale claim extraction.
This deliberately optimizes for attribution precision. A future one-way adapter may export reviewed statements
to Research-to-Skill without coupling either core project.
