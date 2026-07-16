"""Baseline Linker (stage 7) — attaches each entity to the clause that contains
it (by character offset) and emits an ENTITY_IN_CLAUSE relation. A minimal
stand-in for real relation linking (party↔obligation↔clause). Satisfies the
`Linker` interface.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Extractions,
    Relation,
    RelationType,
)


class OffsetLinker:
    def link(
        self,
        document: CanonicalDocument,
        clauses: list[ClauseUnit],
        extractions: Extractions,
    ) -> list[Relation]:
        relations: list[Relation] = []
        counter = 0
        for entity in extractions.entities:
            if not entity.evidence:
                continue
            offset = entity.evidence[0].char_start
            clause = self._clause_at(clauses, offset)
            if clause is None:
                continue
            entity.clause_id = clause.id  # mutates the shared entity object
            relations.append(
                Relation(
                    id=f"r{counter}", type=RelationType.ENTITY_IN_CLAUSE,
                    source_id=entity.id, target_id=clause.id,
                )
            )
            counter += 1
        return relations

    @staticmethod
    def _clause_at(clauses: list[ClauseUnit], offset: int) -> ClauseUnit | None:
        for clause in clauses:
            if clause.char_start <= offset < clause.char_end:
                return clause
        return None
