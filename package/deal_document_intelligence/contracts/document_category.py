from __future__ import annotations

from enum import StrEnum


class DocumentCategory(StrEnum):
    """Due-diligence workstream a document type rolls up to.

    Coarse grouping used at the deal level (room index, completeness checklists)
    and as the graceful fallback label when the exact type is uncertain. Derived
    from DocumentType by lookup, never predicted on its own. See
    docs/03-document-type.md.
    """

    TRANSACTION = "transaction"
    CORPORATE = "corporate"
    COMMERCIAL = "commercial"
    EMPLOYMENT = "employment"
    PROPERTY = "property"
    FINANCIAL = "financial"
    IP = "ip"
    INSURANCE = "insurance"
    LEGAL_REGULATORY = "legal_regulatory"
    DILIGENCE = "diligence"
    CORRESPONDENCE = "correspondence"
