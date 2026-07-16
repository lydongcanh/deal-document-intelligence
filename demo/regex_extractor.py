"""Baseline Extractor (stage 6) — regex spotting of money, dates, orgs and
jurisdictions over the canonical text. A dependency-light stand-in for a real
NER model (GLiNER/spaCy) or custom deal extractor; it's the baseline to beat.
Satisfies the `Extractor` interface.

Because matches are found in `document.text`, every entity's EvidenceSpan is
guaranteed to verify against the source.
"""

from __future__ import annotations

import re

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Entity,
    EntityType,
    EvidenceSpan,
    Extractions,
)

_PATTERNS: list[tuple[EntityType, re.Pattern[str]]] = [
    (EntityType.MONEY, re.compile(r"(?:USD|US\$|\$)\s?[\d,]+(?:\.\d+)?")),
    (EntityType.DATE, re.compile(r"[A-Z][a-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}")),
    (EntityType.ORG, re.compile(
        r"(?:[A-Z][A-Za-z&.'\-]+ )+(?:Inc|LLC|L\.L\.C|Corp|Ltd)\.?")),
    (EntityType.JURISDICTION, re.compile(r"State of [A-Z][a-z]+")),
]


class RegexExtractor:
    def extract(
        self, document: CanonicalDocument, clauses: list[ClauseUnit]
    ) -> Extractions:
        entities: list[Entity] = []
        counter = 0
        for etype, pattern in _PATTERNS:
            for match in pattern.finditer(document.text):
                start, end = match.start(), match.end()
                text = match.group().strip()
                span = EvidenceSpan(
                    page=self._page_at(document, start),
                    char_start=start, char_end=start + len(text), text=text,
                )
                entities.append(
                    Entity(
                        id=f"e{counter}", type=etype, text=text,
                        normalized_value=self._normalize(etype, text),
                        evidence=[span], confidence=0.5,
                    )
                )
                counter += 1
        return Extractions(entities=entities)

    @staticmethod
    def _page_at(document: CanonicalDocument, offset: int) -> int:
        for block in document.blocks:
            if block.char_start <= offset < block.char_end:
                return block.page
        return 1

    @staticmethod
    def _normalize(etype: EntityType, text: str) -> str | None:
        if etype == EntityType.MONEY:
            digits = re.sub(r"[^\d.]", "", text)
            return f"USD {digits}" if digits else None
        return None
