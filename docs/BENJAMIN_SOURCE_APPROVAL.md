# Benjamin Source Approval Gate

Status: **PENDING_SOURCE_APPROVAL**.

Phase 2 source verification has been completed, but neither Benjamin source is marked approved and no Benjamin Paper Agent is created until the user explicitly approves the source pair.

## V2 — Zweite Fassung

Candidate identity:

- `work_id=benjamin-artwork`
- `edition_id=benjamin-artwork-v2`
- version: Zweite Fassung, 1936
- canonical critical-edition source: *Gesammelte Schriften* VII.1, Suhrkamp 1989, pp. 350–384
- access facsimile container: Wikimedia Commons `Benjamin_Kunstwerk.pdf`
- container SHA-256: `0f5f14abc67e1da4829b37830d2ac3f554468e7ff7470be3d6dd4db813d877c1`
- container size: 291 PDF pages
- verified V2 range inside container: PDF 196–230
- mapping: PDF 196 = GS 350; PDF 230 = GS 384
- prepared 35-page V2-only working slice: `Benjamin_Kunstwerk_V2_GS350-384.pdf`
- V2-only slice SHA-256: `d5c9f013689f2662a64e8235a4599ade25036fb40dcd18a388b93d683bcca0ec`

Visual and text verification confirms that container PDF page 196 is headed **Zweite Fassung** and page 230 ends on printed page 384.

The passage required by Lee 2019 is present at container PDF page 205 / V2-only PDF page 10 / GS p.359. Verified wording includes `erste Technik`, the inflected forms `die zweite` / `der zweiten Technik`, `Ein für allemal`, `Einmal ist keinmal`, `Der Ursprung der zweiten Technik`, and `Spiel`. The exact nominative string `Zweite Technik` is not asserted where the source uses an inflected form. The German source says that first technology deploys the human as much as possible and second technology as little as possible; it contrasts `Ein für allemal` with `Einmal ist keinmal`, locates the origin of second technology in taking distance from nature, and says that origin is in play.

This corresponds strongly to Lee 2019 PDF p.18 / printed p.264 and Lee's citation to the Korean Benjamin edition pp.56–57.

## V3 — Dritte Fassung

Candidate identity:

- `work_id=benjamin-artwork`
- `edition_id=benjamin-artwork-v3`
- version: Dritte Fassung / autorisierte letzte Fassung, 1939
- canonical critical-edition source: *Gesammelte Schriften* I.2, Suhrkamp 1980, pp.471–508
- access: German Wikisource plus linked Commons facsimile
- facsimile SHA-256: `bdb9107b41e05fd6919592d6ba786b501f160a1618b1d9e1f4d21108d0745568`
- facsimile size: 38 PDF pages
- mapping: PDF p.1 = GS p.471; PDF p.38 = GS p.508

Positive verification found the expected final-version vocabulary and arguments, including `Aura`, `Echtheit`, `Kultwert`, `Ausstellungswert`, film, `Zerstreuung`, and `Rezeption`. German Wikisource describes the transcription as complete and twice proofread against the source.

Negative verification across all 38 V3 pages found **zero** occurrences of the V2-specific strings `erste Technik`, `zweite Technik`, `Ein für allemal`, `Einmal ist keinmal`, and `Ursprung der zweiten Technik`. V2 first/second-technology evidence therefore cannot be attributed to V3.

## Approval decision

The source pair is technically suitable for edition-separated Paper2Skill ingestion:

```
BENJAMIN_V2_SOURCE_VERIFIED=TRUE
BENJAMIN_V3_SOURCE_VERIFIED=TRUE
BENJAMIN_V2_SOURCE_APPROVED=FALSE
BENJAMIN_V3_SOURCE_APPROVED=FALSE
BENJAMIN_AGENT=PENDING_SOURCE_APPROVAL
```

User approval should explicitly approve V2 and V3 as separate sources. Approval does not merge editions; it merely permits ingestion of each source under its own `paper_id/source_id/edition_id`.
