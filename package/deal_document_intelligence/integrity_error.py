"""Raised by `Pipeline(validation="strict")` when a result fails integrity."""

from __future__ import annotations

from deal_document_intelligence.contracts import ValidationIssue


class IntegrityError(Exception):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        preview = "; ".join(i.message for i in issues[:5])
        super().__init__(f"{len(issues)} integrity issue(s): {preview}")
