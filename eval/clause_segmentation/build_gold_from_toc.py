"""Build a segmentation gold file from a document's own table of contents.

The TOC is the drafter's authoritative list of articles and sections. It is
independent of our segmenter (which parses the body and skips the TOC), so it is
a legitimate, non-circular source of ground truth at the section level.

Handles the two common styles seen so far:
    "1.1. Title ..... A-3"          (bare decimal)
    "Section 1.1 Title ..... A-1"   (word-Section)
and article lines "ARTICLE I ... A-1" or "ARTICLE I" (title on its own line).

Usage:
    python eval/clause_segmentation/build_gold_from_toc.py <source-under-demo-docs> [out.json]

Verify the result against the PDF; TOC parsing is best-effort.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "demo" / "documents"
GOLD = Path(__file__).parent / "gold"

ART = re.compile(r"^ARTICLE\s+([IVXLC]+)\b\.?\s*(.*)$")
SEC = re.compile(r"^(?:Section\s+)?(\d+\.\d+)\.?\s+(.+?)\s+A-\w+\s*$")  # TOC line w/ page ref
BODY_SEC = re.compile(r"^(?:Section\s+)?\d+\.\d+\.?\s+\S")  # section-like, prose (body)
PAGE_REF = re.compile(r"\s+A-\w+\s*$")


def build(source_rel: str) -> dict:
    pdf = pdfium.PdfDocument(str(DOCS / source_rel))
    clauses: list[dict] = []
    seen: set = set()
    in_toc = False
    for i in range(len(pdf)):
        for line in pdf[i].get_textpage().get_text_range().splitlines():
            s = line.strip()
            m_sec = SEC.match(s)
            m_art = ART.match(s)
            if m_sec:
                in_toc = True
                num = m_sec.group(1)
                if ("s", num) not in seen:
                    seen.add(("s", num))
                    clauses.append({"number": num, "depth": 1, "heading": m_sec.group(2).strip()})
            elif m_art:
                num = f"ARTICLE {m_art.group(1)}"
                if ("a", num) not in seen:
                    seen.add(("a", num))
                    title = PAGE_REF.sub("", m_art.group(2)).strip()
                    clauses.append({"number": num, "depth": 0, "heading": title})
            elif in_toc and BODY_SEC.match(s):
                pdf.close()
                return _wrap(source_rel, clauses)
    pdf.close()
    return _wrap(source_rel, clauses)


def _wrap(source_rel: str, clauses: list[dict]) -> dict:
    return {
        "source": source_rel,
        "page_range": None,
        "note": "Derived from the document's own table of contents (independent of the "
                "segmenter, which parses the body). Section level (Article + N.M). "
                "Verify against the PDF.",
        "clauses": clauses,
    }


def main() -> None:
    source_rel = sys.argv[1]
    if len(sys.argv) > 2:
        out = Path(sys.argv[2])
    else:
        # Mirror the source's subfolder, e.g. merger_agreements/moneygram.json
        stem = Path(source_rel).name.rsplit(".", 1)[0].lower().replace(" ", "_")
        out = GOLD / Path(source_rel).parent / (stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build(source_rel)
    out.write_text(json.dumps(data, indent=2))
    arts = [c["number"] for c in data["clauses"] if c["depth"] == 0]
    print(f"{out.name}: {len(data['clauses'])} clauses ({len(arts)} articles) -> {arts}")


if __name__ == "__main__":
    main()
