"""Demo entry point.

Usage:
    python demo/main.py [path-to-document]

With no argument it parses the sample lease in demo/documents/. It runs the
stages we have built so far (canonicalise, then detect language) and prints the
result. As we add pipeline stages, this is where we wire them together.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Let this script import its sibling demo modules when run directly.
sys.path.insert(0, str(Path(__file__).parent))
from docling_parser import DoclingParser  # noqa: E402
from lingua_language_detector import LinguaLanguageDetector  # noqa: E402

DEFAULT_DOC = Path(__file__).parent / "documents" / "Commercial_Lease_Agreement.pdf"


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOC
    doc = DoclingParser().parse(source)

    print(f"doc_id     : {doc.doc_id}")
    print(f"pages      : {doc.page_count}")
    print(f"blocks     : {len(doc.blocks)}")
    print(f"text length: {len(doc.text)}")

    # Language stage: detect the document language from the canonical text.
    detected = LinguaLanguageDetector().detect(doc)
    confidence = f"{detected.confidence:.2f}" if detected.confidence is not None else "n/a"
    print(f"language   : {detected.language} (confidence {confidence})")
    print()

    # Print every block, full text, in document order. Because offsets are
    # exact, this reconstructs the whole canonical document.
    for b in doc.blocks:
        print(f"[{b.type:<10}] p{b.page} {b.char_start:>5}:{b.char_end:<5}")
        print(f"    {b.text}")
        print()


if __name__ == "__main__":
    main()
