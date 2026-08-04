"""DocumentTypeDetector interface -- the document-type stage (3b).

    Input : a ParsedDocument.
    Output: a DetectedDocumentType (predicted type + subtype; category and form are
            derived; a confidence and a review flag).

Signal it reads from the ParsedDocument (the contract is fixed; the exact feature
set is a modelling choice made when the detector is built):
  - `text`: primary. Title, first-page text, and heading lines carry most of the
    signal.
  - `blocks`: structure. Block-type mix (table-heavy -> statement; heading tree ->
    contract/report), heading levels, and bbox geometry (slide-like -> report).
  - `page_count` and `mime_type`: coarse length and modality hints.

In the intended deployment (a server, not a local CLI), a document's NAME and FOLDER
are user-editable data-room metadata (the user can rename or refile at any time), so
they are neither produced by parsing nor stable, and they do NOT live on
ParsedDocument. The service layer holds them and may use them AROUND this content
detector, never inside it:
  - the current document name: a weak, fusible PRIOR (content wins on conflict).
    Weak because it is user-editable and often generic or wrong, so a first version
    may ignore it and add it only if it earns its place on held-out data;
  - the folder / category: a CROSS-CHECK, comparing it against the content-predicted
    type flags misfiled documents rather than feeding the model.
Keeping the content model blind to both lets us evaluate content understanding
honestly and lets it catch mis-naming and misfiling. `quality_status` is read from
the parse output to gate, not recomputed here.

No implementation ships yet. The taxonomy is defined (see docs/03-document-type.md);
the detector is a later build. This interface fixes the seam so the future model
has a defined slot to plug into.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import DetectedDocumentType, ParsedDocument


@runtime_checkable
class DocumentTypeDetector(Protocol):
    def detect(self, document: ParsedDocument) -> DetectedDocumentType: ...
