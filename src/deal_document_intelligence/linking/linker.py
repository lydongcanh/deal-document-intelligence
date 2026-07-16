"""Linker interface — stage 7 (relation linking + value normalisation).

    Input : a CanonicalDocument, its clauses, and the Extractions.
    Output: a list of Relation linking the items together.

HYBRID: value normalisation (dates→ISO, money→amount+currency, durations) uses
libraries; linking party↔obligation↔clause is deal-specific logic implemented
here.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Extractions,
    Relation,
)


@runtime_checkable
class Linker(Protocol):
    def link(
        self,
        document: CanonicalDocument,
        clauses: list[ClauseUnit],
        extractions: Extractions,
    ) -> list[Relation]: ...
