# Phase 2 Results

## Status

```
PHASE2_STATUS=COMPLETE
BENJAMIN_V2_SOURCE=APPROVED_AND_VERIFIED
BENJAMIN_V3_SOURCE=APPROVED_AND_VERIFIED
BENJAMIN_V2_AGENT=PASS
BENJAMIN_V3_AGENT=PASS
TEST_D=PASS
TEST_E=PASS
TEST_F=PASS
```

V2 and V3 were explicitly approved by the user as **separate** Paper Agent sources. They were independently processed through Paper2Skill, visually reviewed page-by-page, adjudicated where parser-number diagnostics remained, and strict verification passed as `reviewed_with_limitations` with `mechanical_ok=true`.

## Live behavioral boundary

The prior committed 50-response 1.0 result remains classified as `COMMITTED_BLIND_RESPONSE_SET`, not a live inference result.

The official gold-isolated run `lee-aura-live-20260928T041757Z` used `DETERMINISTIC_BEHAVIORAL_EVAL` because no external model runtime was available to the repository process. Gold was unavailable during response generation and `EXTERNAL_BLIND=false`.

- type accuracy: 0.44
- evidence voice accuracy: 0.52
- page accuracy: 0.3658536585
- evidence span accuracy: 0.0731707317
- unsupported-claim rejection: 0.3333333333
- false author claims: 5
- external-as-author errors: 4
- adversarial robustness: 0.10

These failures remain committed and are not mixed with the Phase-2 source-bounded dialogue gates.

## Benjamin V2

- paper/edition ID: `benjamin-artwork-v2`
- source: Zweite Fassung, GS VII.1 pp.350–384
- reviewed working PDF: 35 pages
- SHA-256: `d5c9f013689f2662a64e8235a4599ade25036fb40dcd18a388b93d683bcca0ec`
- Paper2Skill status: `reviewed_with_limitations`
- mechanical verification: PASS
- reviewed pages: 35/35
- applied adjudications: 3
- Paper Agent propositions: 6

The first/second-technology passage is at V2 working PDF p.10 / GS p.359.

## Benjamin V3

- paper/edition ID: `benjamin-artwork-v3`
- source: Dritte Fassung, GS I.2 pp.471–508
- reviewed PDF: 38 pages
- SHA-256: `bdb9107b41e05fd6919592d6ba786b501f160a1618b1d9e1f4d21108d0745568`
- Paper2Skill status: `reviewed_with_limitations`
- mechanical verification: PASS
- reviewed pages: 38/38
- applied adjudications: 10
- Paper Agent propositions: 7

V2-specific first/second-technology strings remain absent from the verified V3 facsimile.

## Lee–Benjamin mapping

Five source mappings remain conservatively classified as `STRONG_MATCH`; none is promoted to `EXACT` because the Korean translation was not independently aligned word-for-word against the German critical-edition text.

```
MAPPING_EXACT=0
MAPPING_STRONG_MATCH=5
MAPPING_PARTIAL=0
MAPPING_UNRESOLVED=0
```

## Test D — Benjamin-source critique

Six reviewed evidence-bounded critique turns were generated:

- V2-based: 3
- V3-based: 3

No turn is phrased as "what Benjamin would say." Each turn names a Benjamin source proposition, a Lee target proposition, a relation type, edition identity, and semantic-review status.

Topics:

1. V2 human-deployment criterion vs Lee third-technology transparency
2. V2 play/origin of second technology vs Lee computer/Internet periodization
3. V2 nature-human interplay vs Lee artificial/transparency framing
4. V3 aura withering vs Lee prospective digital aura
5. V3 authenticity/Here-and-Now vs Lee trust/context criterion
6. V3 distraction vs Lee technology-editing immersion

## Test E — Lee 2019 response

All six responses are bounded to the 2019 paper.

```
SUPPORTED_RESPONSE=3
PARTIAL_RESPONSE=3
NO_SOURCE_SUPPORTED_RESPONSE=0
```

The partial responses explicitly preserve missing bridges rather than completing Lee's theory with later concepts.

A temporal/corpus firewall blocks later Lee vocabulary such as `아투라`, `기계세/Mechanocene`, `기술생성시대`, `공진주체 WE`, `마찰의 투명성`, and `생성 아우라` from being emitted as Lee-2019 responses.

## Test F — synthesis

The synthesis actor is explicitly `synthesis-agent`, not a paper author.

```
CROSS_PAPER_ISSUES=3
RESEARCH_GAPS=3
RESEARCH_QUESTIONS=3
```

All issue/gap outputs are `AI_SYNTHESIS`; research questions remain `UNRESOLVED`. Each research question records `novelty_basis`, `derived_from`, `source_gap`, and human-review status.

The three research-question directions are:

1. criteria for relating Benjamin V2 second technology to Lee's third technology without collapsing their different axes;
2. whether digital aura can be theorized without silently restoring V3 authenticity/Here-and-Now;
3. what mechanism could connect V3 distracted mass reception to Lee's digitally interactive immersion.

## Semantic-support review

A separate post-generation source-verifier pass reviewed 21 D/E/F turns. It is explicitly **not** claimed as an independent external human review.

- D critiques: 6 reviewed
- E responses: 6 reviewed
- F issues/gaps/questions: 9 reviewed
- unsupported/overstated publishable turns: 0

Provenance validity alone was not treated as semantic support.

## Hard gates

Final verifier result:

```
FALSE_AUTHOR_CLAIM=0
EXTERNAL_AS_AUTHOR_ERROR=0
CROSS_EDITION_CONTAMINATION=0
UNSUPPORTED_DIALOGUE_TURN=0
TEMPORAL_CORPUS_CONTAMINATION=0
FAKE_PAGE_CITATION=0
```

## Limitations

1. The live blind behavioral run remains weak; Phase-2 dialogue success does not erase those failures.
2. The semantic verifier is a separate source-review pass in the same ChatGPT work session, not an external human replication.
3. Korean/German source mappings are `STRONG_MATCH`, not exact translation alignments.
4. The dialogue artifacts are a small evidence-controlled PoC, not a general benchmark of open-ended humanities reasoning.
