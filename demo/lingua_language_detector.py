"""A lingua-based LanguageDetector, for the demo.

A CONSUMER implementation of the package's `LanguageDetector` interface
(package/deal_document_intelligence/interfaces/language_detector.py). The package
ships no detector; language ID is a commodity, so here we wrap lingua. Swapping
to fastText later would just mean another class with the same `detect` method.

lingua bundles its models (nothing downloads) and returns a real confidence,
which maps straight onto our `DetectedLanguage`.
"""

from __future__ import annotations

from lingua import LanguageDetectorBuilder

from deal_document_intelligence.contracts import DetectedLanguage, ParsedDocument


class LinguaLanguageDetector:
    """Detects the document language with lingua."""

    def __init__(self) -> None:
        # Consider all languages lingua knows. We could narrow this to the
        # languages we expect in deal rooms to cut memory; kept broad for now.
        self._detector = LanguageDetectorBuilder.from_all_languages().build()

    def detect(self, document: ParsedDocument) -> DetectedLanguage:
        text = document.text
        language = self._detector.detect_language_of(text)
        if language is None:
            # lingua could not decide (e.g. empty or too-short text).
            return DetectedLanguage(language=None, confidence=None)

        # lingua's enum exposes the ISO 639-1 code; normalise to lowercase 'en'.
        iso_code = language.iso_code_639_1.name.lower()
        confidence = self._detector.compute_language_confidence(text, language)
        return DetectedLanguage(language=iso_code, confidence=confidence)
