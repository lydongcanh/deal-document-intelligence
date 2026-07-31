"""Span materialisation: give each clause node its extent in the source.

The inclusive span is [source_offset, char_end): the clause plus all its
descendants, ending where the next non-descendant begins (a sibling, or an
ancestor's sibling), or at the document end. The direct spans are the inclusive
span with the children's inclusive spans removed, so they are the clause's OWN
text. It is a list because a parent's sentence can resume after a sub-list.

No text is generated or rewritten; we only compute offsets into the source.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import ParsedDocument
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.decoder import decode


def _subtract(start: int, end: int, holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """[start, end) with the (sorted) holes removed, dropping empty pieces."""
    spans: list[tuple[int, int]] = []
    cursor = start
    for hole_start, hole_end in sorted(holes):
        if hole_start > cursor:
            spans.append((cursor, hole_start))
        cursor = max(cursor, hole_end)
    if cursor < end:
        spans.append((cursor, end))
    return spans


def materialize_spans(nodes: list[ClauseNode], document: ParsedDocument) -> list[ClauseNode]:
    text_len = len(document.text)

    # Inclusive end: the start of the next node at the same or a shallower depth.
    for i, node in enumerate(nodes):
        end = text_len
        for other in nodes[i + 1:]:
            if other.depth <= node.depth:
                end = other.source_offset
                break
        node.char_end = end

    # Direct spans: inclusive span minus the children's inclusive spans.
    children: dict[str | None, list[ClauseNode]] = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node)
    for node in nodes:
        kids = children.get(node.id, [])
        node.direct_spans = _subtract(
            node.source_offset,
            node.char_end or node.source_offset,
            [(k.source_offset, k.char_end or k.source_offset) for k in kids],
        )
    return nodes


def clause_tree(document: ParsedDocument) -> list[ClauseNode]:
    """Decode then materialise: the full deterministic segmentation."""
    return materialize_spans(decode(document), document)
