"""Map LEDGAR's 100 provision labels onto our canonical CUAD-41 taxonomy.

Finding (from inspecting LEDGAR): its taxonomy is mostly generic/administrative
provisions; only a handful overlap CUAD's deal-critical types with confidence.
So LEDGAR's role is (a) reinforce those few overlapping types and (b) supply a
large, varied pool of realistic NEGATIVES (everything else → UNKNOWN/OTHER),
which sharpens precision on the deal types Ansarada actually reviews. CUAD stays
the primary source of deal-critical positives.

Only high-confidence 1:1 semantic matches are mapped, to avoid label noise
(e.g. LEDGAR "Assignments"/"Terminations"/"Warranties" are broader than CUAD's
"Anti-Assignment"/"Termination For Convenience"/"Warranty Duration", so they are
intentionally left as OTHER).
"""

from __future__ import annotations

from deal_document_intelligence.contracts import ClauseType

LEDGAR_TO_CUAD: dict[str, ClauseType] = {
    "Change In Control": ClauseType.CHANGE_OF_CONTROL,
    "Governing Laws": ClauseType.GOVERNING_LAW,
    "Effective Dates": ClauseType.EFFECTIVE_DATE,
    "Non-Disparagement": ClauseType.NON_DISPARAGEMENT,
    "Insurances": ClauseType.INSURANCE,
}


def map_ledgar_label(label: str) -> ClauseType:
    """LEDGAR label → canonical clause type (UNKNOWN denotes OTHER/negative)."""
    return LEDGAR_TO_CUAD.get(label, ClauseType.UNKNOWN)
