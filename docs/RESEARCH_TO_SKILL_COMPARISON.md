# Paper2Agent vs Research-to-Skill

Audited Research-to-Skill: `icerain-cmd/book-to-skill` at
`9355188b292ede45262d2871049385d310d6b106`. No file in that repository was modified.

| Capability | Research-to-Skill | Paper2Agent | Decision |
|---|---|---|---|
| source ingestion | deterministic extract; stable IDs; hash/dedup | Paper2Skill snapshots PDFs/attachments | DO_NOT_DUPLICATE |
| claim extraction | claim schema + host-agent compile plan | source-centric paper skill | EXTEND in sidecar |
| concept extraction | versioned concepts | searchable paper skill | REUSE conceptually |
| provenance | source IDs, SHA-256, claim source IDs | snapshot hash + page review + artifact verification | REUSE both |
| citation | evidence locators, quote/summary, source IDs | section/figure/table/PDF-page guidance | EXTEND with statement/page binding |
| validation | schema/locator/source membership | strict page/source/artifact verification | DO_NOT_DUPLICATE; compose |
| semantic artifacts | research.json, concepts, claims, graph | paper Markdown/assets | KEEP SEPARATE |
| multi-source | workspace and graph | main/supplement/attachments | REUSE identity; dialogue is new |
| handoff | explicit artifacts | delivery contracts | DO_NOT_DUPLICATE |
| export | skill/json/markdown | skill/MCP delivery | DO_NOT_DUPLICATE |
| agent identity | workspace, not one evidence-bounded paper voice | paper skill without typed speech boundary | EXTEND with PaperAgent |
| persistent graph | yes | none equivalent in Paper2Skill | REUSE LATER through adapter |

## REUSE

- source identity and SHA-256 discipline
- explicit claim/evidence relationships
- direct vs inferred/supporting evidence distinction
- graph relations such as `supports`, `contradicts`, `derived_from`
- explicit handoff rather than hidden model memory

## EXTEND

- six epistemic statement types
- code-level attribution firewall
- exact page-bound evidence for `SOURCE_QUOTE` and `AUTHOR_CLAIM`
- one-paper evidence boundary for critique/response
- cross-paper synthesis retaining statement IDs from both sources
- explicit `UNRESOLVED` preservation
- unsupported-author-claim metric

## DO_NOT_DUPLICATE

Paper2Humanities does not reimplement PDF extraction, source hashing/dedup, page rendering/review,
figure/table extraction, persistent research graphs, generic handoff/export, or code-to-MCP conversion.

## Architecture decision

**Do not merge the projects in Phase 1.**

Paper2Skill verifies a paper; Paper2Humanities creates a small typed statement boundary; a future
one-way adapter may export reviewed statements to Research-to-Skill's existing claim/evidence/graph model.
Neither core project should depend on the other.
