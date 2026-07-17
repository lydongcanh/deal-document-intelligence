"""A real-world entity resolved ACROSS all documents in a deal (stage 9b).

This is the deal-level counterpart of `Entity`: one canonical record with all
the surface aliases it appears under and every document mention, so a party like
"Acme Holdings Inc." / "Acme" / "the Company" is a single node across the room.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.entity_mention import EntityMention
from deal_document_intelligence.contracts.entity_type import EntityType


class CanonicalEntity(BaseModel):
    id: str
    type: EntityType
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    mentions: list[EntityMention] = Field(default_factory=list)
    normalized_value: str | None = None
    meta: dict = Field(default_factory=dict)
