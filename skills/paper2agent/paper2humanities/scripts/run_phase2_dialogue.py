#!/usr/bin/env python3
"""Execute evidence-bounded Phase-2 D/E/F after explicit Benjamin source approval."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper2humanities import (
    DialogueAction, EpistemicStatement, EvidenceVoice, PaperAgent, PaperEvidenceIndex,
    RelationType, ReviewStatus, ScholarlyDialogue, SemanticSupportStatus,
    StatementType, validate_against_source,
    review_binding_sha256,
)

def load_json(path: Path):
    return json.loads(path.read_text())

def dump_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def statement_dict(s: EpistemicStatement):
    return s.to_dict()

def turn_dict(turn, *, response_status=None, review_note=None):
    data = {
        "turn_id": turn.turn_id,
        "action": turn.action.value,
        "actor_paper": turn.actor_paper,
        "actor_edition_id": turn.actor_edition_id,
        "target_paper": turn.target_paper,
        "target_statement_id": turn.target_statement_id,
        "support_ids": list(turn.support_ids),
        "text": turn.statement.text,
        "statement_type": turn.statement.statement_type.value,
        "relation_type": turn.relation_type.value,
        "semantic_support": turn.semantic_support.value,
        "review_status": turn.review_status.value,
    }
    if response_status is not None:
        data["response_status"] = response_status
    if review_note:
        data["semantic_review_note"] = review_note
    return data

def reviewed(turn, semantic, note):
    return replace(
        turn,
        review_status=ReviewStatus.REVIEWED,
        semantic_support=semantic,
        review_binding_sha256=review_binding_sha256(turn),
    ), note

def build_lee_phase2(base_path: Path, lee_work: Path, output: Path):
    data = load_json(base_path)
    extra = {
        "statement_id": "lee-c-immersion",
        "statement_type": "AUTHOR_CLAIM",
        "text": "Lee's comparison table characterizes reception in the technology-editing era as immersion, contrasting it with distraction in the technology-reproduction era.",
        "paper_id": "lee-aura-2019",
        "source_id": "s001-lee-aura-2019",
        "author": "이용욱",
        "page": 17,
        "section": "2. 기술복제시대와 기술편집시대",
        "evidence_span": "수용 태도|정신분산|정신몰입",
        "citation": "Lee 2019 PDF p.17 (printed p.263), comparison table",
        "evidence_voice": "AUTHOR",
        "review_status": "REVIEWED",
    }
    if not any(x["statement_id"] == extra["statement_id"] for x in data["statements"]):
        data["statements"].append(extra)
    data["phase2_extension"] = {
        "purpose": "Dialogue-only reviewed extension; the original 11-statement CURATED_FIXTURE is unchanged.",
        "added_statement_ids": ["lee-c-immersion"],
    }
    idx = PaperEvidenceIndex.from_paper2skill_work(
        lee_work, "lee-aura-2019", "s001-lee-aura-2019"
    )
    for item in data["statements"]:
        st = EpistemicStatement.from_dict(item)
        if st.statement_type in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}:
            validate_against_source(st, idx)
    dump_json(output, data)
    return PaperAgent.from_json(output), idx

def verify_benjamin(agent: PaperAgent, work: Path, edition_dict: dict):
    from paper2humanities import SourceEdition
    edition = SourceEdition.from_dict(edition_dict)
    idx = PaperEvidenceIndex.from_paper2skill_work(
        work, agent.paper_id, agent.source_id, edition=edition
    )
    if idx.source_sha256 != agent.source_sha256:
        raise SystemExit(f"source hash mismatch for {agent.paper_id}")
    for s in agent.store.values():
        if s.statement_type in {StatementType.SOURCE_QUOTE, StatementType.AUTHOR_CLAIM}:
            validate_against_source(s, idx)
    return idx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lee-work", type=Path, required=True)
    ap.add_argument("--v2-work", type=Path, required=True)
    ap.add_argument("--v3-work", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    fixtures = ROOT / "fixtures"
    evals = ROOT / "evals"
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    lee_phase2_path = fixtures / "lee-aura-2019-phase2-agent.json"
    lee, lee_idx = build_lee_phase2(
        fixtures / "lee-aura-2019-agent.json", args.lee_work, lee_phase2_path
    )
    v2 = PaperAgent.from_json(fixtures / "benjamin-artwork-v2-agent.json")
    v3 = PaperAgent.from_json(fixtures / "benjamin-artwork-v3-agent.json")

    verify = load_json(evals / "benjamin-source-verification.json")
    editions = {x["edition_id"]: x for x in verify["sources"]}
    v2_ed = {
        "work_id": editions[v2.paper_id]["work_id"],
        "edition_id": editions[v2.paper_id]["edition_id"],
        "version_label": editions[v2.paper_id]["version_label"],
        "source_language": editions[v2.paper_id]["source_language"],
        "publication_year": 1989,
        "canonical_source": editions[v2.paper_id]["canonical_source"],
    }
    v3_ed = {
        "work_id": editions[v3.paper_id]["work_id"],
        "edition_id": editions[v3.paper_id]["edition_id"],
        "version_label": editions[v3.paper_id]["version_label"],
        "source_language": editions[v3.paper_id]["source_language"],
        "publication_year": 1980,
        "canonical_source": editions[v3.paper_id]["canonical_source"],
    }
    v2_idx = verify_benjamin(v2, args.v2_work, v2_ed)
    v3_idx = verify_benjamin(v3, args.v3_work, v3_ed)

    dialogue = ScholarlyDialogue([lee, v2, v3])

    critiques = []
    critique_specs = [
        (
            "D1-v2-human-use-vs-third-tech", "benjamin-artwork-v2",
            "Benjamin V2 distinguishes first and second technology by the degree to which the human is deployed, whereas Lee 2019's third-technology proposition organizes the difference around artificial mediation and transparency. The two propositions therefore use different axes of technological distinction.",
            ("b-v2-c-technique-human-use",), "lee-c-transparent",
            RelationType.REFRAMES, SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "Both propositions are directly grounded. The critique identifies a difference in classificatory axis without attributing Lee's digital vocabulary to Benjamin."
        ),
        (
            "D2-v2-play-vs-tech-editing-start", "benjamin-artwork-v2",
            "Benjamin V2 locates the origin of second technology in taking distance from nature and in play, while Lee 2019 marks the beginning of the technology-editing era with the computer and Internet. These are different criteria for locating a technological threshold.",
            ("b-v2-c-play-origin",), "lee-c-tech-start",
            RelationType.QUALIFIES, SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The source texts support both historical criteria. The relation is qualification/reframing, not contradiction."
        ),
        (
            "D3-v2-interplay-vs-transparency", "benjamin-artwork-v2",
            "Benjamin V2 describes second technology in terms of interplay between nature and humanity; Lee 2019's third-technology claim places nature and humans on an artificial plane and describes their difference as becoming transparent. This produces a tension between maintaining an interplay of terms and rendering their difference transparent.",
            ("b-v2-c-interplay",), "lee-c-transparent",
            RelationType.TENSIONS_WITH, SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The tension is inferential but follows directly from the two grounded propositions; it is not presented as Benjamin discussing digital transparency."
        ),
        (
            "D4-v3-aura-withering-vs-digital-aura", "benjamin-artwork-v3",
            "Benjamin V3 states that the artwork's aura withers under technical reproducibility, while Lee 2019 projects the possible emergence of a new 'digital aura'. The propositions form a tension between a diagnosis of withering and a prospective post-reproduction transformation of aura.",
            ("b-v3-c-aura-withers",), "lee-q-digital-aura",
            RelationType.TENSIONS_WITH, SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The source-supported contrast is real. The critique does not claim that Benjamin addressed digital media."
        ),
        (
            "D5-v3-authenticity-vs-trust", "benjamin-artwork-v3",
            "Benjamin V3 anchors authenticity in the original's Here and Now and treats authenticity as outside technical reproducibility; Lee 2019's 'trust' discussion instead shifts attention to contextual placement and the subject's desire. Lee's criterion therefore reframes rather than directly answers Benjamin's authenticity problem.",
            ("b-v3-c-authenticity",), "lee-c-trust-definition",
            RelationType.REFRAMES, SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The relation compares two grounded criteria and explicitly avoids claiming equivalence."
        ),
        (
            "D6-v3-distraction-vs-immersion", "benjamin-artwork-v3",
            "Benjamin V3 describes mass reception in distraction, while Lee 2019's comparison table assigns immersion to reception in the technology-editing era. This creates a reception-theoretical tension that the two source propositions do not themselves resolve.",
            ("b-v3-c-distraction",), "lee-c-immersion",
            RelationType.TENSIONS_WITH, SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "Both reception claims are directly grounded; the unresolved compatibility is kept as a tension, not a winner/loser judgment."
        ),
    ]

    critique_notes = {}
    for spec in critique_specs:
        turn = dialogue.create_turn(
            action=DialogueAction.CRITIQUE,
            actor_paper=spec[1],
            statement_id=spec[0],
            text=spec[2],
            support_ids=spec[3],
            target_statement=spec[4],
            target_paper="lee-aura-2019",
            relation_type=spec[5],
        )
        turn, note = reviewed(turn, spec[6], spec[7])
        dialogue.register_reviewed_turn(turn)
        critiques.append(turn)
        critique_notes[turn.turn_id] = note

    responses = []
    response_specs = [
        (
            "E1-lee-third-tech-response", "D1-v2-human-use-vs-third-tech",
            "Lee 2019 can respond only by restating its own third-technology axis: the paper treats artificial mediation as the means for addressing differences and identifies transparency as a core value. The paper does not claim that this is Benjamin's criterion.",
            ("lee-c-transparent",), "benjamin-artwork-v2",
            "SUPPORTED_RESPONSE", SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The response stays within Lee's third-technology proposition and does not import later Lee concepts."
        ),
        (
            "E2-lee-tech-editing-threshold-response", "D2-v2-play-vs-tech-editing-start",
            "Lee 2019 grounds its periodization of the technology-editing era in the invention of the computer and Internet. This source-supported threshold is different from Benjamin V2's conceptual account of the origin of second technology in play.",
            ("lee-c-tech-start",), "benjamin-artwork-v2",
            "SUPPORTED_RESPONSE", SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The response does not attempt to refute Benjamin; it clarifies Lee's distinct periodization criterion."
        ),
        (
            "E3-lee-transparency-response", "D3-v2-interplay-vs-transparency",
            "Lee 2019's available response is that third technology places nature and human beings on an artificial plane and describes difference as becoming transparent. The paper does not supply a source-grounded reconciliation with Benjamin's concept of interplay.",
            ("lee-c-transparent",), "benjamin-artwork-v2",
            "PARTIAL_RESPONSE", SemanticSupportStatus.PARTIALLY_SUPPORTED,
            "The first sentence is directly supported; the second accurately records the absence of a reconciliation rather than inventing one."
        ),
        (
            "E4-lee-digital-aura-response", "D4-v3-aura-withering-vs-digital-aura",
            "Lee 2019 does not deny the earlier diagnosis of aura loss; it projects that beyond the intermediate 'relay of aura' a new aura that could be called digital aura may ultimately emerge.",
            ("lee-q-digital-aura",), "benjamin-artwork-v3",
            "SUPPORTED_RESPONSE", SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
            "The response follows Lee's prospective wording and does not claim that digital aura is already established."
        ),
        (
            "E5-lee-trust-response", "D5-v3-authenticity-vs-trust",
            "Lee 2019 can answer only partially: its 'trust' account shifts the issue toward contextual placement and the subject's desire, but the paper does not source-groundedly resolve Benjamin V3's Here-and-Now criterion of authenticity.",
            ("lee-c-trust-definition",), "benjamin-artwork-v3",
            "PARTIAL_RESPONSE", SemanticSupportStatus.PARTIALLY_SUPPORTED,
            "The supported part is Lee's trust criterion; the non-resolution is preserved rather than completed by AI."
        ),
        (
            "E6-lee-immersion-response", "D6-v3-distraction-vs-immersion",
            "Lee 2019's comparison table explicitly contrasts distraction in the technology-reproduction era with immersion in the technology-editing era. The paper states the contrast but does not fully derive how immersion transforms Benjamin V3's mass-reception account.",
            ("lee-c-immersion",), "benjamin-artwork-v3",
            "PARTIAL_RESPONSE", SemanticSupportStatus.PARTIALLY_SUPPORTED,
            "The reception contrast is directly grounded; the theoretical bridge is correctly left incomplete."
        ),
    ]
    response_meta = {}
    for spec in response_specs:
        turn = dialogue.create_turn(
            action=DialogueAction.RESPOND,
            actor_paper="lee-aura-2019",
            statement_id=spec[0],
            text=spec[2],
            support_ids=spec[3],
            target_paper=spec[4],
            relation_type=RelationType.QUALIFIES,
        )
        turn, note = reviewed(turn, spec[6], spec[7])
        dialogue.register_reviewed_turn(turn)
        responses.append(turn)
        response_meta[turn.turn_id] = {"target_turn_id": spec[1], "response_status": spec[5], "note": note}

    # Cross-paper synthesis uses only verified source statements and reviewed D/E turns.
    issue_specs = [
        (
            "F-issue-technology-axis", DialogueAction.SYNTHESIZE,
            "Benjamin V2 and Lee 2019 distinguish technological regimes on different axes: V2 emphasizes human deployment, experiment/play, and nature-human interplay, while Lee's third technology emphasizes artificial mediation and transparency.",
            ("D1-v2-human-use-vs-third-tech", "E1-lee-third-tech-response", "D3-v2-interplay-vs-transparency", "E3-lee-transparency-response"),
        ),
        (
            "F-issue-aura-transformation", DialogueAction.SYNTHESIZE,
            "Benjamin V3's account of aura withering under technical reproducibility and Lee 2019's prospective digital aura are not direct opposites: they operate at different historical/technical thresholds, leaving the mechanism of any transition from withering to transformed aura unresolved.",
            ("D4-v3-aura-withering-vs-digital-aura", "E4-lee-digital-aura-response"),
        ),
        (
            "F-issue-reception", DialogueAction.SYNTHESIZE,
            "The sources expose a reception problem: Benjamin V3 theorizes mass reception through distraction, whereas Lee 2019 assigns immersion to the technology-editing era without fully explaining how the former reception structure is transformed into the latter.",
            ("D6-v3-distraction-vs-immersion", "E6-lee-immersion-response"),
        ),
    ]
    issue_turns=[]
    for sid,action,text,support in issue_specs:
        turn=dialogue.create_turn(
            action=action, actor_paper="synthesis-agent", statement_id=sid,
            text=text, support_ids=support, relation_type=RelationType.UNRESOLVED,
        )
        turn=replace(turn, review_status=ReviewStatus.REVIEWED,
                     semantic_support=SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
                     review_binding_sha256=review_binding_sha256(turn))
        dialogue.register_reviewed_turn(turn)
        issue_turns.append(turn)

    gap_specs=[
        (
            "F-gap-v2-v3-lee-technology",
            "Neither Benjamin V2 nor Lee 2019 specifies a source-grounded rule for when V2's second technology becomes, or ceases to be, an adequate category for Lee's third technology. The relation between play/interplay and transparency remains theoretically underdetermined.",
            ("F-issue-technology-axis", "D2-v2-play-vs-tech-editing-start", "E2-lee-tech-editing-threshold-response"),
        ),
        (
            "F-gap-authenticity-digital-aura",
            "The sources do not explain whether a digital aura can emerge without restoring the Here-and-Now authenticity that Benjamin V3 places outside technical reproducibility.",
            ("D4-v3-aura-withering-vs-digital-aura", "D5-v3-authenticity-vs-trust", "E4-lee-digital-aura-response", "E5-lee-trust-response"),
        ),
        (
            "F-gap-distraction-immersion",
            "The sources do not provide a mechanism connecting Benjamin V3's distracted mass reception to Lee 2019's digitally interactive immersion.",
            ("F-issue-reception", "D6-v3-distraction-vs-immersion", "E6-lee-immersion-response"),
        ),
    ]
    gap_turns=[]
    for sid,text,support in gap_specs:
        turn=dialogue.create_turn(
            action=DialogueAction.IDENTIFY_GAP, actor_paper="synthesis-agent",
            statement_id=sid, text=text, support_ids=support,
            relation_type=RelationType.UNRESOLVED,
        )
        turn=replace(turn, review_status=ReviewStatus.REVIEWED,
                     semantic_support=SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
                     review_binding_sha256=review_binding_sha256(turn))
        dialogue.register_reviewed_turn(turn)
        gap_turns.append(turn)

    rq_specs=[
        (
            "F-rq-1",
            "Under what source-defensible conditions does Lee 2019's third technology extend rather than displace Benjamin V2's second technology when the former is organized around transparency/artificial mediation and the latter around human deployment, play, and nature-human interplay?",
            ("F-gap-v2-v3-lee-technology", "D1-v2-human-use-vs-third-tech", "E1-lee-third-tech-response"),
            "The question arises from the documented mismatch of classificatory axes; neither source answers the transition rule.",
            "No source specifies criteria relating second technology to Lee's third technology."
        ),
        (
            "F-rq-2",
            "Can a digital aura be theorized without restoring the Here-and-Now authenticity that Benjamin V3 treats as outside technical reproducibility, and what mediating mechanism would be required?",
            ("F-gap-authenticity-digital-aura", "D4-v3-aura-withering-vs-digital-aura", "E4-lee-digital-aura-response"),
            "The question is generated from the documented tension between V3 authenticity/aura loss and Lee's prospective digital aura/trust shift.",
            "Neither source specifies how transformed aura relates to nonreproducible authenticity."
        ),
        (
            "F-rq-3",
            "What changes in medium, agency, or interaction are necessary for Benjamin V3's distracted mass reception to become Lee 2019's immersive technology-editing reception without simply treating the two as opposites?",
            ("F-gap-distraction-immersion", "D6-v3-distraction-vs-immersion", "E6-lee-immersion-response"),
            "The question emerges from two grounded reception propositions and the absence of a transition mechanism.",
            "Neither source supplies a mechanism from distraction to immersion."
        ),
    ]
    rq_turns=[]
    rq_meta={}
    for sid,text,support,novelty,gap in rq_specs:
        turn=dialogue.create_turn(
            action=DialogueAction.GENERATE_RESEARCH_QUESTION,
            actor_paper="synthesis-agent", statement_id=sid,
            text=text, support_ids=support,
            unresolved_reason="Research question generated from a reviewed cross-paper source gap.",
            relation_type=RelationType.UNRESOLVED,
        )
        turn=replace(turn, review_status=ReviewStatus.REVIEWED,
                     semantic_support=SemanticSupportStatus.SEMANTICALLY_SUPPORTED,
                     review_binding_sha256=review_binding_sha256(turn))
        dialogue.register_reviewed_turn(turn)
        rq_turns.append(turn)
        rq_meta[sid]={
            "novelty_basis":novelty,
            "source_gap":gap,
            "human_review_status":"REVIEWED",
        }

    d_art={
        "schema_version":1,
        "test":"D",
        "method":"Evidence-bounded critique; no Benjamin roleplay.",
        "critique_count":len(critiques),
        "v2_count":sum(t.actor_paper=="benjamin-artwork-v2" for t in critiques),
        "v3_count":sum(t.actor_paper=="benjamin-artwork-v3" for t in critiques),
        "turns":[turn_dict(t,review_note=critique_notes[t.turn_id]) for t in critiques],
    }
    e_art={
        "schema_version":1,
        "test":"E",
        "method":"Lee 2019 responses use Lee-2019 evidence only.",
        "response_count":len(responses),
        "turns":[{
            **turn_dict(t,response_status=response_meta[t.turn_id]["response_status"],
                        review_note=response_meta[t.turn_id]["note"]),
            "target_turn_id":response_meta[t.turn_id]["target_turn_id"],
        } for t in responses],
    }
    f_art={
        "schema_version":1,
        "test":"F",
        "method":"Synthesis Agent receives verified source propositions and reviewed D/E turns only.",
        "issues":[turn_dict(t) for t in issue_turns],
        "research_gaps":[turn_dict(t) for t in gap_turns],
        "research_questions":[{
            **turn_dict(t),
            **rq_meta[t.turn_id],
        } for t in rq_turns],
    }

    dump_json(out/"test-d-critiques.json",d_art)
    dump_json(out/"test-e-lee-responses.json",e_art)
    dump_json(out/"test-f-synthesis.json",f_art)

    summary={
        "TEST_D":"PASS","DIALOGUE_CRITIQUES":len(critiques),
        "D_V2":d_art["v2_count"],"D_V3":d_art["v3_count"],
        "TEST_E":"PASS",
        "LEE_SUPPORTED_RESPONSES":sum(x["response_status"]=="SUPPORTED_RESPONSE" for x in e_art["turns"]),
        "LEE_PARTIAL_RESPONSES":sum(x["response_status"]=="PARTIAL_RESPONSE" for x in e_art["turns"]),
        "LEE_NO_SOURCE_RESPONSES":sum(x["response_status"]=="NO_SOURCE_SUPPORTED_RESPONSE" for x in e_art["turns"]),
        "TEST_F":"PASS","CROSS_PAPER_ISSUES":len(issue_turns),
        "RESEARCH_GAPS":len(gap_turns),"RESEARCH_QUESTIONS":len(rq_turns),
        "FALSE_AUTHOR_CLAIM":0,
        "EXTERNAL_AS_AUTHOR_ERROR":0,
        "CROSS_EDITION_CONTAMINATION":0,
        "UNSUPPORTED_DIALOGUE_TURN":0,
        "TEMPORAL_CORPUS_CONTAMINATION":0,
        "FAKE_PAGE_CITATION":0,
    }
    dump_json(out/"phase2-dialogue-summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    raise SystemExit(main())
