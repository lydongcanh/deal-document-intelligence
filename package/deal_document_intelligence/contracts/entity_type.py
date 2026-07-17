"""Kinds of entities.

Generic types come from off-the-shelf NER baselines; deal-specific ones
(PARTY-as-role, GOVERNING_LAW, …) are custom.
"""

from __future__ import annotations

from enum import StrEnum


class EntityType(StrEnum):
    PARTY = "party"
    PERSON = "person"
    ORG = "org"
    DATE = "date"
    MONEY = "money"
    PERCENT = "percent"
    DURATION = "duration"
    JURISDICTION = "jurisdiction"
    GOVERNING_LAW = "governing_law"
    LOCATION = "location"
    OTHER = "other"
