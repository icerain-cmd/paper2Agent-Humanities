#!/usr/bin/env python3
"""Build reviewed Benjamin V2/V3 Paper Agent fixtures from approved Paper2Skill work dirs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper2humanities import (
    EpistemicStatement, EvidenceVoice, PaperAgent, PaperEvidenceIndex,
    ReviewStatus, SourceEdition, StatementType, validate_against_source,
)

def st(
    sid, kind, text, paper_id, source_id, edition_id, page, section,
    evidence_span, citation,
):
    return EpistemicStatement(
        statement_id=sid,
        statement_type=kind,
        text=text,
        paper_id=paper_id,
        source_id=source_id,
        author="Walter Benjamin",
        page=page,
        section=section,
        evidence_span=evidence_span,
        citation=citation,
        edition_id=edition_id,
        evidence_voice=EvidenceVoice.AUTHOR,
        review_status=ReviewStatus.REVIEWED,
    )

def build_v2(work: Path):
    paper_id=edition_id="benjamin-artwork-v2"
    source_id="s001-benjamin-kunstwerk-v2-gs350-384-verified"
    edition=SourceEdition(
        work_id="benjamin-artwork", edition_id=edition_id,
        version_label="Zweite Fassung (1936)", source_language="de",
        publication_year=1989,
        canonical_source="Walter Benjamin, Gesammelte Schriften VII.1, Suhrkamp 1989, pp.350-384",
    )
    idx=PaperEvidenceIndex.from_paper2skill_work(work,paper_id,source_id,edition=edition)
    statements=[
        st(
            "b-v2-c-technique-human-use", StatementType.AUTHOR_CLAIM,
            "Benjamin distinguishes first and second technology by the tendency of the first to deploy the human as much as possible and the second as little as possible.",
            paper_id,source_id,edition_id,10,"VI",
            "daß die erste Technik den Menschen so sehr, daß die zweite ihn so wenig wie möglich einsetzt.",
            "V2 PDF p.10; GS VII.1 p.359",
        ),
        st(
            "b-v2-c-once-experiment", StatementType.AUTHOR_CLAIM,
            "First technology is associated with the once-for-all, while second technology is associated with experiment and repeatable variation.",
            paper_id,source_id,edition_id,10,"VI",
            "Das Ein für allemal gilt für die erste Technik (da geht es um die nie wiedergutzumachende Verfehlung oder den ewig stellvertretenden Opfertod). Das Einmal ist keinmal gilt für die zweite (sie hat es mit dem Experiment und seiner unermüdlichen Variierung der Versuchsanordnung zu tun).",
            "V2 PDF p.10; GS VII.1 p.359",
        ),
        st(
            "b-v2-c-play-origin", StatementType.AUTHOR_CLAIM,
            "Benjamin locates the origin of second technology in the human taking distance from nature and, in other words, in play.",
            paper_id,source_id,edition_id,10,"VI",
            "Der Ursprung der zweiten Technik ist da zu suchen, wo der Mensch zum ersten Mal und mit unbewußter List daran ging, Abstand von der Natur zu nehmen. Er liegt mit anderen Worten im Spiel.",
            "V2 PDF p.10; GS VII.1 p.359",
        ),
        st(
            "b-v2-c-interplay", StatementType.AUTHOR_CLAIM,
            "Benjamin contrasts domination of nature with second technology's orientation toward an interplay between nature and humanity.",
            paper_id,source_id,edition_id,10,"VI",
            "Die erste hat es wirklich auf Beherrschung der Natur abgesehen; die zweite viel mehr auf ein Zusammenspiel zwischen der Natur und der Menschheit.",
            "V2 PDF p.10; GS VII.1 p.359",
        ),
        st(
            "b-v2-c-art-function", StatementType.AUTHOR_CLAIM,
            "The socially decisive function of contemporary art is described as practice in this interplay, especially in film.",
            paper_id,source_id,edition_id,10,"VI",
            "Funktion der heutigen Kunst ist Einübung in dieses Zusammenspiel. Insbesondere gilt das vom Film.",
            "V2 PDF p.10; GS VII.1 p.359",
        ),
        st(
            "b-v2-c-aura-decay", StatementType.AUTHOR_CLAIM,
            "Benjamin defines aura as a unique appearance of distance and connects its contemporary decay to mass reproduction and the desire to bring things nearer.",
            paper_id,source_id,edition_id,6,"IV",
            "Was ist eigentlich Aura? Ein sonderbares Gespinst aus Raum und Zeit: einmalige Erscheinung einer Ferne, so nah sie sein mag.",
            "V2 PDF p.6; GS VII.1 p.355",
        ),
    ]
    for x in statements: validate_against_source(x,idx)
    agent=PaperAgent(
        paper_id,"Das Kunstwerk im Zeitalter seiner technischen Reproduzierbarkeit (Zweite Fassung)",
        "Walter Benjamin",source_id,idx.source_sha256,
        ["Aura","erste Technik","zweite Technik","Spiel","Zusammenspiel","Film"],
        statements,edition_id=edition_id,
    )
    return agent,idx,edition

def build_v3(work: Path):
    paper_id=edition_id="benjamin-artwork-v3"
    source_id="s001-benjamin-kunstwerk-v3"
    edition=SourceEdition(
        work_id="benjamin-artwork", edition_id=edition_id,
        version_label="Dritte Fassung / autorisierte letzte Fassung (1939)",
        source_language="de", publication_year=1980,
        canonical_source="Walter Benjamin, Gesammelte Schriften I.2, Suhrkamp 1980, pp.471-508",
    )
    idx=PaperEvidenceIndex.from_paper2skill_work(work,paper_id,source_id,edition=edition)
    statements=[
        st(
            "b-v3-c-authenticity", StatementType.AUTHOR_CLAIM,
            "Benjamin grounds authenticity in the Here and Now of the original and states that the domain of authenticity eludes technical reproducibility.",
            paper_id,source_id,edition_id,6,"II",
            "_der Echtheit entzieht sich der technischen - und natürlich nicht nur der technischen_ - _Reproduzierbarkeit_",
            "V3 PDF p.6; GS I.2 p.476",
        ),
        st(
            "b-v3-c-aura-withers", StatementType.AUTHOR_CLAIM,
            "In the age of technical reproducibility, what withers is the artwork's aura.",
            paper_id,source_id,edition_id,7,"II",
            "was im Zeitalter der technischen Reproduzierbarkeit des Kunstwerks verkümmert, das ist seine Aura.",
            "V3 PDF p.7; GS I.2 p.477",
        ),
        st(
            "b-v3-c-aura-distance", StatementType.AUTHOR_CLAIM,
            "Benjamin defines natural aura as the unique appearance of a distance, however near it may be.",
            paper_id,source_id,edition_id,9,"III",
            "Diese letztere definieren wir als einmalige Erscheinung einer Ferne, so nah sie sein mag.",
            "V3 PDF p.9; GS I.2 p.479",
        ),
        st(
            "b-v3-c-cult-exhibition", StatementType.AUTHOR_CLAIM,
            "Benjamin identifies cult value and exhibition value as two polar accents in the reception of artworks.",
            paper_id,source_id,edition_id,12,"V",
            "Die Rezeption von Kunstwerken erfolgt mit verschiedenen Akzenten, unter denen sich zwei polare herausheben. Der eine dieser Akzente liegt auf dem Kultwert, der andere auf dem Ausstellungswert des Kunstwerkes",
            "V3 PDF p.12; GS I.2 p.482",
        ),
        st(
            "b-v3-c-distraction", StatementType.AUTHOR_CLAIM,
            "Benjamin contrasts concentration with distraction: the concentrated beholder enters the work, whereas the distracted mass absorbs the work into itself.",
            paper_id,source_id,edition_id,34,"XV",
            "Der vor dem Kunstwerk sich Sammelnde versenkt sich darein; er geht in dieses Werk ein, wie die Legende es von einem chinesischen Maler beim Anblick seines vollendeten Bildes erzählt. Dagegen versenkt die zerstreute Masse ihrerseits das Kunstwerk in sich.",
            "V3 PDF p.34; GS I.2 p.504",
        ),
        st(
            "b-v3-c-film-examiner", StatementType.AUTHOR_CLAIM,
            "Film trains a reception in distraction; the cinema public is an examiner, but a distracted one, whose evaluative attitude does not include attention.",
            paper_id,source_id,edition_id,35,"XV",
            "Der Film drängt den Kultwert nicht nur dadurch zurück, daß er das Publikum in eine begutachtende Haltung bringt, sondern auch dadurch, daß die begutachtende Haltung im Kino Aufmerksamkeit nicht einschließt. Das Publikum ist ein Examinator, doch ein zerstreuter.",
            "V3 PDF p.35; GS I.2 p.505",
        ),
        st(
            "b-v3-c-dada-demand", StatementType.AUTHOR_CLAIM,
            "Benjamin describes Dada's crude and extravagant forms as emerging from a rich historical force field and as anticipating effects later sought in film.",
            paper_id,source_id,edition_id,31,"XIV",
            "Die derart, zumal in den sogenannten Verfallszeiten, sich ergebenden Extravaganzen und Kruditäten der Kunst gehen in Wirklichkeit aus ihrem reichsten historischen Kräftezentrum hervor.",
            "V3 PDF p.31; GS I.2 p.501",
        ),
    ]
    for x in statements: validate_against_source(x,idx)
    agent=PaperAgent(
        paper_id,"Das Kunstwerk im Zeitalter seiner technischen Reproduzierbarkeit (Dritte Fassung)",
        "Walter Benjamin",source_id,idx.source_sha256,
        ["Aura","Echtheit","Kultwert","Ausstellungswert","Film","Zerstreuung","Rezeption"],
        statements,edition_id=edition_id,
        forbidden_terms=["erste Technik","zweite Technik","Ein für allemal","Einmal ist keinmal","Ursprung der zweiten Technik"],
    )
    return agent,idx,edition

def dump(agent,idx,edition,path:Path,verification_status:str):
    data={
      "schema_version":2,
      "paper_id":agent.paper_id,
      "title":agent.title,
      "author":agent.author,
      "source":{
        "source_id":agent.source_id,
        "sha256":agent.source_sha256,
        "edition_id":agent.edition_id,
        "edition":edition.to_dict(),
        "paper2skill_verification":verification_status,
        "user_approved":True,
      },
      "concepts":list(agent.concepts),
      "corpus_policy":{"forbidden_terms":list(agent.forbidden_terms)},
      "statements":[s.to_dict() for s in agent.store.values()],
    }
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--v2-work",required=True,type=Path)
    ap.add_argument("--v3-work",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    v2,idx2,ed2=build_v2(args.v2_work)
    v3,idx3,ed3=build_v3(args.v3_work)
    dump(v2,idx2,ed2,args.output_dir/"benjamin-artwork-v2-agent.json","reviewed_with_limitations")
    dump(v3,idx3,ed3,args.output_dir/"benjamin-artwork-v3-agent.json","reviewed_with_limitations")
    print(json.dumps({
      "BENJAMIN_V2_AGENT":"PASS","BENJAMIN_V2_STATEMENTS":len(v2.store.values()),
      "BENJAMIN_V3_AGENT":"PASS","BENJAMIN_V3_STATEMENTS":len(v3.store.values()),
      "V2_SHA256":idx2.source_sha256,"V3_SHA256":idx3.source_sha256,
    },ensure_ascii=False))

if __name__=="__main__":
    raise SystemExit(main())
