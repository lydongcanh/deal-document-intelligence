"""The frozen v1 label contract for the document-type model.

The published model's output labels are the 23 taxonomy leaves + `other` (24 in
total). `unknown` is a confidence threshold applied by the consumer, not a class;
`mixed_bundle` is out of scope for v1. The order of `MODEL_LABELS` is FROZEN: it
defines `id2label`, so reordering it would silently break every deployed consumer.

The assertions at the bottom are the mechanical taxonomy check (the one Codex runs):
if the package taxonomy ever drifts from this list, importing this module fails loudly
rather than shipping a wrong label set.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import DocumentType as T

# 8 classes we intend to pilot-validate with real dev+test (contract-form, text-heavy).
_PILOT: list[T] = [
    T.ACQUISITION_AGREEMENT,
    T.COMMERCIAL_AGREEMENT,
    T.IP_AGREEMENT,
    T.EMPLOYMENT_AGREEMENT,
    T.NDA,
    T.FINANCING_AGREEMENT,
    T.CONSTITUTIONAL,
    T.SHAREHOLDERS_AGREEMENT,
]

# 15 classes trained (synthetic) but shipped experimental until they earn a real eval.
_EXPERIMENTAL: list[T] = [
    T.FINANCIAL_STATEMENTS,
    T.FINANCIAL_MODEL,
    T.CAP_TABLE,
    T.TAX_DOCUMENT,
    T.MINUTES,
    T.CERTIFICATE,
    T.REGULATORY,
    T.LITIGATION,
    T.REPORT,
    T.INFORMATION_MEMORANDUM,
    T.DISCLOSURE_SCHEDULE,
    T.CORRESPONDENCE,
    T.INSURANCE_POLICY,
    T.LEASE_AGREEMENT,
    T.DILIGENCE_QA,
]

# Frozen output order: the 23 leaves (pilot then experimental) followed by `other`.
_LEAVES: list[T] = _PILOT + _EXPERIMENTAL
MODEL_LABELS: list[str] = [t.value for t in _LEAVES] + [T.OTHER.value]

PILOT_CLASSES: list[str] = [t.value for t in _PILOT]
EXPERIMENTAL_CLASSES: list[str] = [t.value for t in _EXPERIMENTAL]

ID2LABEL: dict[int, str] = dict(enumerate(MODEL_LABELS))
LABEL2ID: dict[str, int] = {label: i for i, label in enumerate(MODEL_LABELS)}

# `unknown` (abstention) and `mixed_bundle` (bundle detection) are deliberately NOT
# model classes in v1.
_NOT_MODEL_CLASSES = {T.OTHER, T.UNKNOWN, T.MIXED_BUNDLE}


def _self_check() -> None:
    leaves = set(_LEAVES)
    expected = set(T) - _NOT_MODEL_CLASSES
    assert leaves == expected, (
        f"taxonomy drift: leaves {sorted(t.value for t in leaves)} != "
        f"package {sorted(t.value for t in expected)}"
    )
    assert not (set(_PILOT) & set(_EXPERIMENTAL)), "pilot/experimental overlap"
    assert len(_PILOT) == 8, f"expected 8 pilot, got {len(_PILOT)}"
    assert len(_EXPERIMENTAL) == 15, f"expected 15 experimental, got {len(_EXPERIMENTAL)}"
    assert len(MODEL_LABELS) == 24 == len(set(MODEL_LABELS)), "labels not 24 unique"


_self_check()
