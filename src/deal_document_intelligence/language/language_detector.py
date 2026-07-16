"""LanguageDetector interface — stage 3.

    Input : a CanonicalDocument (freshly parsed).
    Output: the same document enriched with `language` (ISO 639-1) and
            `document_type`.

Commodity: language ID is a solved problem (fastText/lingua); consumers may
supply their own. Document-type detection may be a light classifier we own.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import CanonicalDocument


@runtime_checkable
class LanguageDetector(Protocol):
    def detect(self, document: CanonicalDocument) -> CanonicalDocument: ...
