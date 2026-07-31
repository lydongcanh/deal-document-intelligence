from __future__ import annotations

from deal_document_intelligence.contracts import ParsedDocument
from deal_document_intelligence.segmentation.clause_node import ClauseNode


def validate_tree(nodes: list[ClauseNode], document: ParsedDocument) -> list[str]:
    """Validate a materialised clause tree. Returns issue codes; empty means sound.

    The invariants from docs/04: every span is in bounds, offsets are monotonic,
    every child sits inside its parent, and top-level spans tile the body with no
    gap or overlap (text conservation).
    """

    issues: list[str] = []
    text_len = len(document.text)
    by_id = {node.id: node for node in nodes}

    last_offset = -1
    for node in nodes:
        if node.char_end is None or not (
            0 <= node.source_offset <= node.char_end <= text_len
        ):
            issues.append(f"span_out_of_bounds:{node.id}")

        if node.source_offset <= last_offset:
            issues.append(f"not_monotonic:{node.id}")

        last_offset = node.source_offset

        if node.parent_id is not None:
            parent = by_id.get(node.parent_id)
            if (
                parent is None
                or parent.char_end is None
                or not (
                    parent.source_offset <= node.source_offset
                    and (node.char_end or 0) <= parent.char_end
                )
            ):
                issues.append(f"child_outside_parent:{node.id}")

    # Top-level inclusive spans should be contiguous: each ends where the next begins.
    tops = [node for node in nodes if node.depth == 0]
    for a, b in zip(tops, tops[1:]):
        if a.char_end != b.source_offset:
            issues.append(f"top_gap_or_overlap:{a.id}->{b.id}")

    return issues
