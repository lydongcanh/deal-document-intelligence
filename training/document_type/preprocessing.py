"""Frozen input preprocessing, shared by every model so train == inference.

The interface freezes the model's view to the document's OPENING (the type is
usually clear from the first page). We approximate "first N tokens" with the first N
whitespace tokens at the data level; the transformer then additionally caps at its own
512 subword tokens on this same opening. Both models therefore look only at the start,
and the baseline and the transformer see a comparable window.

Keeping this in one place means a change here changes training and serving together,
so they cannot silently diverge.
"""

from __future__ import annotations

import hashlib

MAX_TOKENS = 512


def document_opening(text: str, max_tokens: int = MAX_TOKENS) -> str:
    """Return the first `max_tokens` whitespace tokens of `text`."""
    return " ".join(text.split()[:max_tokens])


def sha256(text: str) -> str:
    """Stable content hash, used for dedup and provenance."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
