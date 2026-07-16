"""Baseline RelationExtractor (stage 7) — attaches entities to their clause
(ENTITY_IN_CLAUSE), and spots obligations ("shall") and events (termination /
renewal) by keyword. A minimal stand-in for real relation/obligation modelling.
Satisfies the `RelationExtractor` interface.
"""

from __future__ import annotations

import re

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Entity,
    Event,
    Obligation,
    Relation,
    RelationExtraction,
    RelationType,
)

_MODEL_VERSION = "rules-baseline-0.1"
_EVENT_KEYWORDS = {"terminat": "termination", "renew": "renewal"}


class BaselineRelationExtractor:
    def extract(
        self,
        document: CanonicalDocument,
        clauses: list[ClauseUnit],
        entities: list[Entity],
    ) -> RelationExtraction:
        relations: list[Relation] = []
        obligations: list[Obligation] = []
        events: list[Event] = []

        for i, entity in enumerate(entities):
            if not entity.evidence:
                continue
            clause = self._clause_at(clauses, entity.evidence[0].char_start)
            if clause is None:
                continue
            entity.clause_id = clause.id  # mutates the shared entity object
            relations.append(Relation(
                id=f"r{i}", type=RelationType.ENTITY_IN_CLAUSE,
                source_id=entity.id, target_id=clause.id, model_version=_MODEL_VERSION,
            ))

        for i, clause in enumerate(clauses):
            lowered = clause.text.lower()
            if "shall" in lowered:
                obligations.append(Obligation(
                    id=f"o{i}", text=self._sentence_with(clause.text, "shall"),
                    evidence=clause.evidence, clause_id=clause.id,
                    confidence=0.4, model_version=_MODEL_VERSION,
                ))
            for keyword, event_type in _EVENT_KEYWORDS.items():
                if keyword in lowered:
                    events.append(Event(
                        id=f"ev{i}-{event_type}", type=event_type,
                        text=clause.heading or clause.text[:60],
                        evidence=clause.evidence, clause_id=clause.id,
                        confidence=0.4, model_version=_MODEL_VERSION,
                    ))
        return RelationExtraction(
            obligations=obligations, events=events, relations=relations
        )

    @staticmethod
    def _clause_at(clauses: list[ClauseUnit], offset: int) -> ClauseUnit | None:
        for clause in clauses:
            if clause.char_start <= offset < clause.char_end:
                return clause
        return None

    @staticmethod
    def _sentence_with(text: str, keyword: str) -> str:
        for sentence in re.split(r"(?<=[.;])\s+", text):
            if keyword in sentence.lower():
                return " ".join(sentence.split())[:200]
        return " ".join(text.split())[:200]
