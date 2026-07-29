"""LanguageDetector interface — stage 3.

    Input : a CanonicalDocument (freshly parsed).
    Output: a DocumentClassification (language + document_type), a separate
            object rather than a mutated document, so the return type only ever
            carries fields this stage actually produced.

Commodity: language ID is a solved problem (fastText/lingua); consumers may
supply their own. Document-type detection may be a light classifier we own.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import CanonicalDocument, DocumentClassification


@runtime_checkable
class LanguageDetector(Protocol):
    def detect(self, document: CanonicalDocument) -> DocumentClassification: ...
