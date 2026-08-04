from __future__ import annotations

from enum import StrEnum


class DocumentForm(StrEnum):
    """How a document is built, which selects its processing pipeline family.

    This is the routing field: `form` decides which stage-4+ pipeline a document
    enters. Only `contract` goes through clause segmentation + classification; the
    others get their own structural segmentation and extraction. Derived from
    DocumentType by lookup. See docs/03-document-type.md.
    """

    CONTRACT = "contract"
    STATEMENT = "statement"
    RECORD = "record"
    REPORT = "report"
    CORRESPONDENCE = "correspondence"
