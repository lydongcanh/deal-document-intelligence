"""Baseline Classifier (stage 5) — keyword matching against the clause heading
and text. Deliberately weak (fixed confidence 0.5); it's the baseline the
CUAD-fine-tuned classifier must beat. Satisfies the `Classifier` interface.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseType,
    ClauseUnit,
)

# Ordered (substring, type): first match wins.
_KEYWORDS: list[tuple[str, ClauseType]] = [
    ("governing law", ClauseType.GOVERNING_LAW),
    ("termination for convenience", ClauseType.TERMINATION_FOR_CONVENIENCE),
    ("minimum commitment", ClauseType.MINIMUM_COMMITMENT),
    ("renewal", ClauseType.RENEWAL_TERM),
    ("exclusiv", ClauseType.EXCLUSIVITY),
    ("effective date", ClauseType.EFFECTIVE_DATE),
    ("by and between", ClauseType.PARTIES),
    ("insurance", ClauseType.INSURANCE),
    ("audit", ClauseType.AUDIT_RIGHTS),
]


class KeywordClassifier:
    def classify(
        self, clauses: list[ClauseUnit], document: CanonicalDocument
    ) -> list[ClauseUnit]:
        for clause in clauses:
            haystack = f"{clause.heading or ''}\n{clause.text}".lower()
            clause.clause_type = ClauseType.UNKNOWN
            clause.classification_confidence = None
            for keyword, ctype in _KEYWORDS:
                if keyword in haystack:
                    clause.clause_type = ctype
                    clause.classification_confidence = 0.5
                    break
        return clauses
