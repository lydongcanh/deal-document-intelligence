"""The bundle stage 7 (relations & obligations/events) produces.

Stage 6 produces entities; stage 7 consumes them and produces the higher-order
facts: obligations, events, and the relations linking everything together.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.event import Event
from deal_document_intelligence.contracts.obligation import Obligation
from deal_document_intelligence.contracts.relation import Relation


class RelationExtraction(BaseModel):
    obligations: list[Obligation] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
