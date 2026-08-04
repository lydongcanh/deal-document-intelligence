"""The kind of deal document, plus its derived category and processing form.

`DocumentType` is the single label the detector predicts. `category` (the
due-diligence workstream) and `default_form` (which processing pipeline the
document enters) are DERIVED from the type by lookup, not predicted separately, so
they can never drift from the type. See docs/03-document-type.md for the full
taxonomy and why the axes are kept separate.
"""

from __future__ import annotations

from enum import StrEnum

from deal_document_intelligence.contracts.document_category import DocumentCategory
from deal_document_intelligence.contracts.document_form import DocumentForm


class DocumentType(StrEnum):
    """A whole-document deal type. The detector predicts exactly one of these."""

    # form: contract -- negotiated agreements, go through the clause pipeline
    ACQUISITION_AGREEMENT = "acquisition_agreement"
    SHAREHOLDERS_AGREEMENT = "shareholders_agreement"
    COMMERCIAL_AGREEMENT = "commercial_agreement"
    EMPLOYMENT_AGREEMENT = "employment_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    FINANCING_AGREEMENT = "financing_agreement"
    IP_AGREEMENT = "ip_agreement"
    NDA = "nda"
    INSURANCE_POLICY = "insurance_policy"
    DISCLOSURE_SCHEDULE = "disclosure_schedule"
    CONSTITUTIONAL = "constitutional"

    # form: statement -- tabular / figure-heavy
    FINANCIAL_STATEMENTS = "financial_statements"
    FINANCIAL_MODEL = "financial_model"
    TAX_DOCUMENT = "tax_document"
    CAP_TABLE = "cap_table"

    # form: record -- events or schema fields
    MINUTES = "minutes"
    CERTIFICATE = "certificate"
    REGULATORY = "regulatory"
    DILIGENCE_QA = "diligence_qa"

    # form: report -- narrative / slides
    INFORMATION_MEMORANDUM = "information_memorandum"
    REPORT = "report"
    LITIGATION = "litigation"

    # form: correspondence
    CORRESPONDENCE = "correspondence"

    # special labels -- no pipeline; keep the detector honest (see docs/03)
    OTHER = "other"
    UNKNOWN = "unknown"
    MIXED_BUNDLE = "mixed_bundle"

    @property
    def category(self) -> DocumentCategory | None:
        """The workstream this type rolls up to; None for the special labels."""
        return _CATEGORY.get(self)

    @property
    def default_form(self) -> DocumentForm | None:
        """The pipeline this type routes to; None for the special labels.

        "default" because a few form-heterogeneous types (e.g. LITIGATION: a
        pleading is a report, a settlement is a contract) refine this from the
        subtype. That refinement is applied by DetectedDocumentType once subtype
        values are enumerated; today every type uses its default.
        """
        return _FORM.get(self)


_CATEGORY: dict[DocumentType, DocumentCategory] = {
    DocumentType.ACQUISITION_AGREEMENT: DocumentCategory.TRANSACTION,
    DocumentType.SHAREHOLDERS_AGREEMENT: DocumentCategory.CORPORATE,
    DocumentType.COMMERCIAL_AGREEMENT: DocumentCategory.COMMERCIAL,
    DocumentType.EMPLOYMENT_AGREEMENT: DocumentCategory.EMPLOYMENT,
    DocumentType.LEASE_AGREEMENT: DocumentCategory.PROPERTY,
    DocumentType.FINANCING_AGREEMENT: DocumentCategory.FINANCIAL,
    DocumentType.IP_AGREEMENT: DocumentCategory.IP,
    DocumentType.NDA: DocumentCategory.TRANSACTION,
    DocumentType.INSURANCE_POLICY: DocumentCategory.INSURANCE,
    DocumentType.DISCLOSURE_SCHEDULE: DocumentCategory.TRANSACTION,
    DocumentType.CONSTITUTIONAL: DocumentCategory.CORPORATE,
    DocumentType.FINANCIAL_STATEMENTS: DocumentCategory.FINANCIAL,
    DocumentType.FINANCIAL_MODEL: DocumentCategory.FINANCIAL,
    DocumentType.TAX_DOCUMENT: DocumentCategory.FINANCIAL,
    DocumentType.CAP_TABLE: DocumentCategory.CORPORATE,
    DocumentType.MINUTES: DocumentCategory.CORPORATE,
    DocumentType.CERTIFICATE: DocumentCategory.CORPORATE,
    DocumentType.REGULATORY: DocumentCategory.LEGAL_REGULATORY,
    DocumentType.DILIGENCE_QA: DocumentCategory.DILIGENCE,
    DocumentType.INFORMATION_MEMORANDUM: DocumentCategory.DILIGENCE,
    DocumentType.REPORT: DocumentCategory.DILIGENCE,
    DocumentType.LITIGATION: DocumentCategory.LEGAL_REGULATORY,
    DocumentType.CORRESPONDENCE: DocumentCategory.CORRESPONDENCE,
}

_FORM: dict[DocumentType, DocumentForm] = {
    DocumentType.ACQUISITION_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.SHAREHOLDERS_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.COMMERCIAL_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.EMPLOYMENT_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.LEASE_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.FINANCING_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.IP_AGREEMENT: DocumentForm.CONTRACT,
    DocumentType.NDA: DocumentForm.CONTRACT,
    DocumentType.INSURANCE_POLICY: DocumentForm.CONTRACT,
    DocumentType.DISCLOSURE_SCHEDULE: DocumentForm.CONTRACT,
    DocumentType.CONSTITUTIONAL: DocumentForm.CONTRACT,
    DocumentType.FINANCIAL_STATEMENTS: DocumentForm.STATEMENT,
    DocumentType.FINANCIAL_MODEL: DocumentForm.STATEMENT,
    DocumentType.TAX_DOCUMENT: DocumentForm.STATEMENT,
    DocumentType.CAP_TABLE: DocumentForm.STATEMENT,
    DocumentType.MINUTES: DocumentForm.RECORD,
    DocumentType.CERTIFICATE: DocumentForm.RECORD,
    DocumentType.REGULATORY: DocumentForm.RECORD,
    DocumentType.DILIGENCE_QA: DocumentForm.RECORD,
    DocumentType.INFORMATION_MEMORANDUM: DocumentForm.REPORT,
    DocumentType.REPORT: DocumentForm.REPORT,
    DocumentType.LITIGATION: DocumentForm.REPORT,
    DocumentType.CORRESPONDENCE: DocumentForm.CORRESPONDENCE,
}
