"""Baseline LanguageDetector (stage 3) — a dependency-light stand-in.

Assumes English unless the text is mostly non-ASCII, and guesses document type
by keyword. A real impl uses a language-ID model (fastText/lingua) and a trained
doc-type classifier. Satisfies the `LanguageDetector` interface.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import CanonicalDocument, DocumentType

_DOC_TYPE_KEYWORDS: list[tuple[str, DocumentType]] = [
    ("distributor", DocumentType.DISTRIBUTION),
    ("non-disclosure", DocumentType.NDA),
    ("confidential", DocumentType.NDA),
    ("employment", DocumentType.EMPLOYMENT),
    ("lease", DocumentType.LEASE),
    ("licen", DocumentType.LICENSE),
    ("share purchase", DocumentType.SHARE_PURCHASE),
]


class SimpleLanguageDetector:
    def detect(self, document: CanonicalDocument) -> CanonicalDocument:
        text = document.text
        non_ascii = sum(1 for ch in text if ord(ch) > 127)
        document.language = "unknown" if text and non_ascii / len(text) > 0.3 else "en"

        lowered = text.lower()
        document.document_type = DocumentType.UNKNOWN
        for keyword, dtype in _DOC_TYPE_KEYWORDS:
            if keyword in lowered:
                document.document_type = dtype
                break
        return document
