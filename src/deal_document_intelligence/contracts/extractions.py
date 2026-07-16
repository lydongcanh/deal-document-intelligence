"""The bundle stage 6 (extraction) produces, so the interface returns one value."""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.entity import Entity
from deal_document_intelligence.contracts.event import Event
from deal_document_intelligence.contracts.obligation import Obligation


class Extractions(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
