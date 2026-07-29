"""LanguageDetector interface — the language stage.

    Input : a ParsedDocument (freshly parsed).
    Output: a DetectedLanguage (language + confidence), a separate object rather
            than a mutated document, so the return type only ever carries fields
            this stage actually produced.

Commodity: language ID is a solved problem (fastText/lingua), so consumers may
supply their own. Document-type detection is a separate stage.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import DetectedLanguage, ParsedDocument


@runtime_checkable
class LanguageDetector(Protocol):
    def detect(self, document: ParsedDocument) -> DetectedLanguage: ...
