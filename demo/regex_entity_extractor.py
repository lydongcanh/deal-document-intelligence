"""Baseline EntityExtractor (stage 6) — regex spotting of money, dates, orgs and
jurisdictions over the canonical text. Dependency-light stand-in for a real
multilingual NER model. Normalisation is deferred to stage 8 (the resolver), so
entities here carry raw text only. Satisfies the `EntityExtractor` interface.
"""

from __future__ import annotations

import re

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Entity,
    EntityType,
    EvidenceSpan,
)

_MODEL_VERSION = "regex-baseline-0.1"

_PATTERNS: list[tuple[EntityType, re.Pattern[str]]] = [
    (EntityType.MONEY, re.compile(r"(?:USD|US\$|\$)\s?[\d,]+(?:\.\d+)?")),
    (EntityType.DATE, re.compile(r"[A-Z][a-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}")),
    (EntityType.ORG, re.compile(
        r"(?:[A-Z][A-Za-z&.'\-]+ )+(?:Inc|LLC|L\.L\.C|Corp|Ltd)\.?")),
    (EntityType.JURISDICTION, re.compile(r"State of [A-Z][a-z]+(?: [A-Z][a-z]+)*")),
]


class RegexEntityExtractor:
    def extract(
        self, document: CanonicalDocument, clauses: list[ClauseUnit]
    ) -> list[Entity]:
        entities: list[Entity] = []
        counter = 0
        for etype, pattern in _PATTERNS:
            for match in pattern.finditer(document.text):
                start = match.start()
                text = match.group().strip()
                entities.append(
                    Entity(
                        id=f"e{counter}", type=etype, text=text,
                        evidence=[EvidenceSpan(
                            page=self._page_at(document, start),
                            char_start=start, char_end=start + len(text), text=text,
                        )],
                        confidence=0.5, model_version=_MODEL_VERSION,
                    )
                )
                counter += 1
        return entities

    @staticmethod
    def _page_at(document: CanonicalDocument, offset: int) -> int:
        for block in document.blocks:
            if block.char_start <= offset < block.char_end:
                return block.page
        return 1
