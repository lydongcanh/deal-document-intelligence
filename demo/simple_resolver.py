"""Baseline Resolver (stage 8) — normalises money values and tags within-document
alias groups by a normalised key. Dependency-light stand-in for locale-aware
normalisation (dateparser/price-parser/pint) + real coreference. Satisfies the
`Resolver` interface.
"""

from __future__ import annotations

import re

from deal_document_intelligence.contracts import CanonicalDocument, Entity, EntityType

_MODEL_VERSION = "rules-baseline-0.1"
_ORG_SUFFIX = re.compile(r"\b(inc|llc|l\.l\.c|corp|ltd|limited)\.?\b", re.IGNORECASE)


class SimpleResolver:
    def resolve(
        self, document: CanonicalDocument, entities: list[Entity]
    ) -> list[Entity]:
        for entity in entities:
            entity.model_version = _MODEL_VERSION
            if entity.type == EntityType.MONEY:
                digits = re.sub(r"[^\d.]", "", entity.text)
                entity.normalized_value = f"USD {digits}" if digits else None
            # within-document alias key: lets later stages group co-referent mentions
            entity.meta["alias_key"] = self._alias_key(entity)
        return entities

    @staticmethod
    def _alias_key(entity: Entity) -> str:
        text = entity.text.lower()
        if entity.type == EntityType.ORG:
            text = _ORG_SUFFIX.sub("", text)
        return f"{entity.type.value}:{re.sub(r'[^a-z0-9]+', ' ', text).strip()}"
