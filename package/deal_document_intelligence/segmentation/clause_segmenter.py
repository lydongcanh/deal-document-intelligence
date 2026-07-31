from __future__ import annotations

from deal_document_intelligence.contracts import (
    Block,
    ClauseUnit,
    EvidenceSpan,
    ParsedDocument,
)
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.spans import clause_tree


def _block_at(document: ParsedDocument, offset: int) -> Block | None:
    for block in document.blocks:
        if block.char_start <= offset < block.char_end:
            return block

    return None


def _heading(text: str, node: ClauseNode) -> str | None:
    """Best-effort clause title: the marker's own line up to the first sentence."""
    if not node.direct_spans:
        return None

    start, end = node.direct_spans[0]
    lead = text[start:end]

    if lead.startswith(node.marker_text):
        lead = lead[len(node.marker_text) :]

    # collapse newlines/spaces (number and title are separate blocks)
    lead = " ".join(lead.split())
    lead = lead.lstrip(". ") # drop any leftover marker punctuation
    head = lead.split(". ")[0].strip().rstrip(".")

    return head if head and len(head) <= 100 else None


class ClauseSegmenter:
    """ClauseSegmenter: the Segmenter interface implementation (stage 4).

    Runs the deterministic core (candidates -> grammar -> decoder -> spans) and
    converts the clause tree into the package's `ClauseUnit` contract. Each unit
    carries its inclusive text (the clause plus its sub-parts, so it is meaningful on
    its own) with an exact evidence span. Hierarchy that `ClauseUnit` has no field
    for (depth, parent) is kept in `meta`, so consumers can pick a granularity (for
    example only depth-1 sections) without losing the tree.
    """

    def segment(self, document: ParsedDocument) -> list[ClauseUnit]:
        units: list[ClauseUnit] = []
        for node in clause_tree(document):
            start, end = node.source_offset, node.char_end or node.source_offset
            text = document.text[start:end]
            block = _block_at(document, start)
            units.append(
                ClauseUnit(
                    id=node.id,
                    text=text,
                    char_start=start,
                    char_end=end,
                    number=node.marker_text.strip().rstrip("."),
                    heading=_heading(document.text, node),
                    evidence=[
                        EvidenceSpan(
                            page=block.page if block else 1,
                            char_start=start,
                            char_end=end,
                            text=text,
                            block_id=block.id if block else None,
                        )
                    ],
                    meta={
                        "depth": node.depth,
                        "parent_id": node.parent_id,
                        "path": list(node.path),
                    },
                )
            )
        return units
