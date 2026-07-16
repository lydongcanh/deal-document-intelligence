"""How two extracted items relate."""

from __future__ import annotations

from enum import StrEnum


class RelationType(StrEnum):
    PARTY_HAS_OBLIGATION = "party_has_obligation"
    OBLIGATION_UNDER_CLAUSE = "obligation_under_clause"
    ENTITY_IN_CLAUSE = "entity_in_clause"
    EVENT_UNDER_CLAUSE = "event_under_clause"
    OTHER = "other"
