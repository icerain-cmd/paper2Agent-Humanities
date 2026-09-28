#!/usr/bin/env python3
"""Verify Benjamin V2/V3 source candidates without approving or ingesting them."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from pypdf import PdfReader, PdfWriter

V2_CONTAINER_SHA = "0f5f14abc67e1da4829b37830d2ac3f554468e7ff7470be3d6dd4db813d877c1"
V3_SHA = "bdb9107b41e05fd6919592d6ba786b501f160a1618b1d9e1f4d21108d0745568"
V2_TERMS = [
    "erste Technik", "zweiten Technik", "Ein für allemal",
    "Einmal ist keinmal", "Ursprung der zweiten Technik", "Spiel",
]
V3_POSITIVE = ["Aura", "Echtheit", "Kultwert", "Ausstellungswert", "Film", "Zerstreuung", "Rezeption"]
V3_FORBIDDEN_V2 = [
    "erste Technik", "zweiten Technik", "Ein für allemal",
    "Einmal ist keinmal", "Ursprung der zweiten Technik",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text(page) -> str:
    return " ".join((page.extract_text() or "").replace("\u00ad", "").split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-container", required=True)
    ap.add_argument("--v3", required=True)
    ap.add_argument("--v2-slice-out")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    v2_path, v3_path = Path(args.v2_container), Path(args.v3)
    v2, v3 = PdfReader(str(v2_path)), PdfReader(str(v3_path))
    v2_sha, v3_sha = sha256(v2_path), sha256(v3_path)
    if v2_sha != V2_CONTAINER_SHA:
        raise SystemExit(f"V2 container SHA mismatch: {v2_sha}")
    if v3_sha != V3_SHA:
        raise SystemExit(f"V3 SHA mismatch: {v3_sha}")
    if len(v2.pages) != 291 or len(v3.pages) != 38:
        raise SystemExit("unexpected source page count")

    v2_first, v2_key = text(v2.pages[195]), text(v2.pages[204])
    v2_following_editorial = text(v2.pages[230])
    if "Zweite Fassung" not in v2_first or "350-384" not in v2_following_editorial or "Zweite Fassung" not in v2_following_editorial:
        raise SystemExit("V2 boundary verification failed")
    missing_v2 = [term for term in V2_TERMS if term.lower() not in v2_key.lower()]
    if missing_v2:
        raise SystemExit(f"V2 key passage missing terms: {missing_v2}")

    v3_all = [text(page) for page in v3.pages]
    if "Dritte Fassung" not in v3_all[0] or "508" not in v3_all[-1]:
        raise SystemExit("V3 boundary verification failed")
    positive_pages = {
        term: [i for i, body in enumerate(v3_all, 1) if term.lower() in body.lower()]
        for term in V3_POSITIVE
    }
    if any(not pages for pages in positive_pages.values()):
        raise SystemExit(f"V3 expected vocabulary missing: {positive_pages}")
    forbidden_hits = {
        term: [i for i, body in enumerate(v3_all, 1) if term.lower() in body.lower()]
        for term in V3_FORBIDDEN_V2
    }
    if any(forbidden_hits.values()):
        raise SystemExit(f"V2-only passage contaminated V3: {forbidden_hits}")

    slice_sha = None
    if args.v2_slice_out:
        out = Path(args.v2_slice_out)
        writer = PdfWriter()
        for page_index in range(195, 230):
            writer.add_page(v2.pages[page_index])
        with out.open("wb") as f:
            writer.write(f)
        slice_sha = sha256(out)

    result = {
        "source_approval": "PENDING_SOURCE_APPROVAL",
        "v2": {
            "container_sha256": v2_sha,
            "container_pages": len(v2.pages),
            "container_pdf_page_range": [196, 230],
            "gs_page_range": [350, 384],
            "key_passage": {"container_pdf_page": 205, "gs_page": 359, "terms": V2_TERMS},
            "slice_sha256": slice_sha,
            "verified": True,
        },
        "v3": {
            "sha256": v3_sha,
            "pdf_pages": len(v3.pages),
            "pdf_page_range": [1, 38],
            "gs_page_range": [471, 508],
            "positive_term_pdf_pages": positive_pages,
            "v2_only_term_hits": forbidden_hits,
            "verified": True,
        },
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
