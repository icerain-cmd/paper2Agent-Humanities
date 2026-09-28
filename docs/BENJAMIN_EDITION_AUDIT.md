# Benjamin Edition Audit — Phase 1.5

Status: source acquisition / edition audit only. **No Benjamin Paper Agent is created in Phase 1.5.**

## Why edition identity is mandatory

Lee Yong-wook's 2019 paper explicitly works across Benjamin versions. In its section "3. 아우라와 제3기술", Lee states that the discussion of first and second technology was present in the second version and deleted from the third, then cites the Korean Benjamin edition for that passage. V2 and V3 therefore cannot be collapsed into one undifferentiated "Benjamin source".

Paper2Agent-Humanities models them as separate edition IDs:

```
work_id = benjamin-artwork
edition_id = benjamin-artwork-v2 | benjamin-artwork-v3
```

A source-grounded statement from one edition cannot validate against the other edition even if a phrase happens to overlap.

## V2 — Zweite, erweiterte deutsche Fassung

**Edition identity**

- work: Walter Benjamin, *Das Kunstwerk im Zeitalter seiner technischen Reproduzierbarkeit*
- version: Zweite, erweiterte deutsche Fassung
- version date: 1936 (composed between late 1935 and early February 1936)
- canonical bibliographic source: *Gesammelte Schriften*, Band VII, Teil 1, ed. Rolf Tiedemann and Hermann Schweppenhäuser, Suhrkamp, 1989, pp. 350–384
- proposed edition_id: `benjamin-artwork-v2`
- source language: German

**Access candidate**

Wikimedia Commons file `Benjamin Kunstwerk.pdf`:
https://commons.wikimedia.org/wiki/File:Benjamin_Kunstwerk.pdf

The Commons description identifies the file as an own scan containing the four versions from 1935–1939, 291 PDF pages, and marks the work public domain. This is useful as an openly accessible facsimile container, but Phase 1.5 does not yet treat an OCR/transcription from it as canonical text.

**Page stability**

The canonical scholarly pagination is GS VII.1, pp. 350–384. The Commons container has stable PDF pages, but its internal page-to-GS mapping must be recorded during ingestion rather than guessed.

**Transcription status**

No dedicated twice-proofread V2 Wikisource transcription was identified in this audit. Therefore V2 should enter Paper2Skill from a verified facsimile/source scan and undergo the normal page review.

**Copyright/access**

Walter Benjamin died in 1940; Wikimedia Commons marks the scan as public domain/free of known restrictions in the jurisdictions described on its file page. The critical-edition typesetting/editorial apparatus may have separate rights; Paper2Agent-Humanities should ingest only what is legally available to the researcher and should retain source metadata.

**Mapping to Lee 2019**

Lee PDF p.18 (printed p.264) quotes the first/second-technology passage and cites Benjamin/Choi Seong-man translation, pp. 56–57. The V2 source is therefore required for claims involving `Erste und zweite Technik`, `Ein für allemal`, `Einmal ist keinmal`, and the origin of second technology in play.

**Recommendation**

`BENJAMIN_V2_SOURCE=Wikimedia Commons Benjamin_Kunstwerk.pdf as public facsimile candidate, edition identity cross-checked to GS VII.1 (1989), pp.350–384; ingest only after page-range verification.`

## V3 — Dritte, autorisierte letzte Fassung

**Edition identity**

- work: Walter Benjamin, *Das Kunstwerk im Zeitalter seiner technischen Reproduzierbarkeit*
- version: Dritte, autorisierte letzte Fassung
- version date: 1939
- canonical bibliographic source: *Gesammelte Schriften*, Band I, Teil 2, ed. Rolf Tiedemann and Hermann Schweppenhäuser, Suhrkamp, 1980, pp. 471–508
- proposed edition_id: `benjamin-artwork-v3`
- source language: German

**Access candidate**

German Wikisource:
https://de.wikisource.org/wiki/Das_Kunstwerk_im_Zeitalter_seiner_technischen_Reproduzierbarkeit_(Dritte_Fassung)

Facsimile file:
https://commons.wikimedia.org/wiki/File:Das_Kunstwerk_im_Zeitalter_seiner_technischen_Reproduzierbarkeit_(Dritte_Fassung).pdf

Wikisource identifies the text as the posthumously printed authorized final version, sourced from GS I.2 pp.471–508. The transcription is marked complete and twice proofread against the source, and individual transcription pages link to the scan.

**Page stability**

Excellent for the PoC: 38-page facsimile, stable GS printed pagination 471–508, and page-addressable Wikisource transcription.

**Transcription status**

Wikisource marks the transcription `fertig` and twice proofread against the source. The source spelling is retained.

**Copyright/access**

The Commons file page marks the work public domain under its stated life-plus-70 analysis. As with V2, retain the exact access/source record and do not infer rights for unrelated translations.

**Mapping to Lee 2019**

V3 is suitable for aura, authenticity, ritual/exhibition value, film, distraction and related final-version claims. It must **not** be used to fabricate evidence for the first/second-technology passage that Lee explicitly notes was deleted from V3.

**Recommendation**

`BENJAMIN_V3_SOURCE=German Wikisource Dritte Fassung + linked Commons facsimile, GS I.2 (1980), pp.471–508.`

## Cross-edition policy

1. Never merge V2 and V3 into one source_id or edition_id.
2. Never repair a missing V3 passage with V2 text while citing V3.
3. Every Benjamin grounded statement must carry the edition identity of the evidence source.
4. Cross-edition comparison is `INTERPRETATION` or `AI_SYNTHESIS` with both source identities.
5. Lee's Korean translation citation is a mapping aid, not permission to substitute translation pagination for German-source pagination.
6. Source approval is required before either candidate becomes Agent B.

## Phase boundary

```
BENJAMIN_AGENT=PENDING_SOURCE_APPROVAL
```

No Lee ↔ Benjamin critique, response, or research-gap generation is executed in Phase 1.5.

## Phase-2 facsimile verification update

Actual source files were downloaded and checked. The Commons four-version container is 291 PDF pages with SHA-256 `0f5f14abc67e1da4829b37830d2ac3f554468e7ff7470be3d6dd4db813d877c1`. V2 occupies container PDF pp.196–230 = GS VII.1 pp.350–384. The reviewed working slice is 35 pages with SHA-256 `d5c9f013689f2662a64e8235a4599ade25036fb40dcd18a388b93d683bcca0ec`. Its first/second-technology passage occurs at container p.205 / slice p.10 / GS p.359. The source uses grammatical forms including `erste Technik`, `die zweite`, and `der zweiten Technik`, together with `Ein für allemal`, `Einmal ist keinmal`, and the origin of second technology in `Spiel`.

The separate V3 facsimile is 38 pages, SHA-256 `bdb9107b41e05fd6919592d6ba786b501f160a1618b1d9e1f4d21108d0745568`, mapping PDF pp.1–38 to GS I.2 pp.471–508. Aura/Echtheit/Kultwert/Ausstellungswert/Film/Zerstreuung/Rezeption were positively located. A full-page scan found no V2-specific first/second-technology passage strings.

Both candidates were later explicitly approved by the user on 2026-09-28. Verification and approval remain separate events; V2 and V3 were subsequently ingested as distinct Paper Agents.
