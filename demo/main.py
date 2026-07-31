"""Demo entry point.

Usage:
    python demo/main.py [path-to-document]

With no argument it runs on a sample merger agreement in demo/documents/. It runs
the stages we have built so far (canonicalise, detect language, segment clauses)
and prints a summary plus the recovered clause tree. As we add stages, this is
where we wire them together.

These agreements are long (70+ pages), so the demo parses only the first pages
for speed. Pass a path to run on another document (still page-limited here).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Let this script import its sibling demo modules when run directly.
sys.path.insert(0, str(Path(__file__).parent))
from docling_parser import DoclingParser  # noqa: E402
from lingua_language_detector import LinguaLanguageDetector  # noqa: E402

from deal_document_intelligence.segmentation import ClauseSegmenter  # noqa: E402

DEFAULT_DOC = (Path(__file__).parent / "documents" / "merger_agreements"
               / "Moneygram International Inc. Merger Agreement.Pdf")
PAGES = (1, 20)  # demo only: parse the first pages of these long documents


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOC

    doc = DoclingParser(page_range=PAGES).parse(source)
    detected = LinguaLanguageDetector().detect(doc)
    clauses = ClauseSegmenter().segment(doc)

    conf = f"{detected.confidence:.2f}" if detected.confidence is not None else "n/a"
    print(f"doc_id     : {doc.doc_id}  (first {PAGES[1]} pages)")
    print(f"pages      : {doc.page_count}")
    print(f"blocks     : {len(doc.blocks)}")
    print(f"language   : {detected.language} (confidence {conf})")
    print(f"clauses    : {len(clauses)}")
    print()

    # The clause tree: indent by depth, show number and heading.
    print("clause tree (first 30):")
    for c in clauses[:30]:
        indent = "   " * c.meta.get("depth", 0)
        heading = f": {c.heading}" if c.heading else ""
        print(f"  {indent}{c.number}{heading}")


if __name__ == "__main__":
    main()
