"""Split the clause taxonomy into DOCUMENT METADATA vs PROVISIONS.

Not every CUAD "clause type" is a provision a lawyer reviews. Some are really
*document attributes* — the title, the parties, key dates — better thought of as
extracted entities/metadata than as "clauses". Folding them into a "does this
document contain clause X?" signal pollutes it: a title or a date is present in
almost every contract, so those types over-fire and drag precision (exactly what
the gold eval showed).

So we categorise the taxonomy. Product features that ask "which *provisions* does
this deal contain?" score over `PROVISION_TYPES`; the `METADATA_TYPES` route to
attribute/entity extraction instead.

This is a categorisation *layer* over `ClauseType`, independent of the model's
output space (the current schema, `cuad41-derived-other-v1`, has 41 deal outputs
and derives OTHER). We just interpret/score predicted types by category.
"""

from __future__ import annotations

from enum import StrEnum

from deal_document_intelligence.contracts.clause_type import ClauseType


class ClauseCategory(StrEnum):
    METADATA = "metadata"    # document attributes: title, parties, key dates
    PROVISION = "provision"  # substantive clauses a reviewer cares about


# Document-attribute types — not "provisions" for presence/review purposes.
METADATA_TYPES: frozenset[ClauseType] = frozenset({
    ClauseType.DOCUMENT_NAME,
    ClauseType.PARTIES,
    ClauseType.AGREEMENT_DATE,
    ClauseType.EFFECTIVE_DATE,
    ClauseType.EXPIRATION_DATE,
})

# Everything else in the 41 is a provision. (UNKNOWN/OTHER is neither.)
PROVISION_TYPES: frozenset[ClauseType] = frozenset(
    c for c in ClauseType if c != ClauseType.UNKNOWN and c not in METADATA_TYPES
)


def category_of(clause_type: ClauseType) -> ClauseCategory | None:
    """METADATA / PROVISION — or None for UNKNOWN (the negative class)."""
    if clause_type in METADATA_TYPES:
        return ClauseCategory.METADATA
    if clause_type in PROVISION_TYPES:
        return ClauseCategory.PROVISION
    return None
