from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from deal_document_intelligence.contracts.document_category import DocumentCategory
from deal_document_intelligence.contracts.document_form import DocumentForm
from deal_document_intelligence.contracts.document_type import DocumentType


class DetectedDocumentType(BaseModel):
    """Output of the document-type stage (3b).

    The detector predicts `document_type` (and `subtype` when the text makes it
    clear). `category` and `form` are DERIVED from the type and exposed as computed
    fields, so they cannot drift and are never set by the caller. `quality_status`
    and `language` are deliberately NOT here: they are document-level attributes
    produced upstream (parse and stage 3a) and travel with the document. See
    docs/03-document-type.md.

    No detector ships yet; this fixes the contract shape the future model fills.
    Kept separate from ParsedDocument so the parser's return type never carries a
    field it did not produce.
    """

    document_type: DocumentType | None = None
    subtype: str | None = Field(
        default=None,
        description="finer label under a broad type (e.g. certificate/report kind); free text until enumerated",
    )
    confidence: float | None = Field(default=None, ge=0, le=1)
    needs_review: bool = Field(
        default=False,
        description="escalate to human review (UNKNOWN, MIXED_BUNDLE, or low confidence)",
    )

    @computed_field
    @property
    def category(self) -> DocumentCategory | None:
        """Workstream, derived from document_type (None for specials or unset)."""
        return self.document_type.category if self.document_type is not None else None

    @computed_field
    @property
    def form(self) -> DocumentForm | None:
        """Processing form, derived from document_type (None for specials or unset).

        Form-heterogeneous types (e.g. LITIGATION) will refine this from `subtype`
        once subtype values are enumerated; today it is the type's default_form.
        """
        return (
            self.document_type.default_form if self.document_type is not None else None
        )
