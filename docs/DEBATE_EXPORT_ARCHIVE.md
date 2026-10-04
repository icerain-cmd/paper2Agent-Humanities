# Debate Export / Archive V1

## Purpose

Debate sessions remain canonical in SQLite. Export files are derived research records that can be regenerated at any time.

## UI

Each Recent Session provides:

- MD
- PDF
- JSON

The current live session also exposes the same three formats after a session starts or resumes.

## Persistent archive

Generated files are stored outside the Git worktree:

`/home/leeyongwook/.local/share/paper2agent-humanities/exports/<session_id>/`

Each requested format is written to this folder before being returned to the browser.

## Markdown

Human-readable research note containing:

- topic / session / protocol / status
- participants
- complete turn transcript
- action / verification
- thesis
- target claim
- stance update
- open issue
- grounding statement IDs and PDF pages
- user interventions in chronological position
- source / provenance appendix

## JSON

Machine-readable canonical export containing:

- complete session payload
- participant metadata
- evidence index
- persisted event chronology
- protocol version
- interventions and turn-level provenance

Schema identifier:

`paper2agent-humanities-debate-export-v1`

## PDF

A4 research-reading copy generated through headless Chromium.

The PDF contains the same scholarly structure as the Markdown export, including Korean text, V2 argument metadata, interventions, grounding, and provenance appendix.

## API

```text
GET /api/debate/sessions/{session_id}/export/markdown
GET /api/debate/sessions/{session_id}/export/pdf
GET /api/debate/sessions/{session_id}/export/json
GET /api/debate/sessions/{session_id}/exports
```

## Validation

Verified against both:

- V1 stored sessions
- V2 stored sessions

Long-session PDF test:

- 10-turn V2 debate
- 13 PDF pages
- Korean rendering PASS
- first / middle / final page visually inspected
- Markdown / JSON / PDF browser downloads PASS
