"""A typed integrity issue found by `EvidenceBackedResult.validate_integrity()`.

Typed (code + message + optional ref) rather than a bare string, so callers can
branch on `code` and issues serialise cleanly into results/telemetry.
"""

from __future__ import annotations

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    code: str  # e.g. "missing_evidence", "dangling_ref", "span_mismatch"
    message: str
    ref: str | None = None  # the offending item id, when applicable
