"""One clause-classification training example (multi-label).

`labels == [ClauseType.UNKNOWN]` denotes an OTHER/negative example (a clause
that is none of the deal-critical types).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts import ClauseType


class ClauseExample(BaseModel):
    text: str
    labels: list[ClauseType] = Field(default_factory=list)
    source: str  # "cuad" | "ledgar"
    doc_id: str  # source contract (CUAD) / synthetic id (LEDGAR) — used for leakage-free splits
    split: str = ""  # "train" | "val" | "test"
