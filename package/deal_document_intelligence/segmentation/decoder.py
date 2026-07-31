"""Deterministic decoder: candidates -> clause tree (structure only).

Walks the block-start candidates from the body start, keeping a stack of open
clauses, and uses the numbering grammar to decide each marker's place:

- sibling of an open level -> close deeper levels, continue that level
- first child of the top   -> open a deeper level
- fresh sub-list under top -> open a deeper level (cross-family, e.g. 2.1 -> (a))
- a new article            -> reset to top level
- none of the above        -> skip as noise (a stray or cross-reference)

The stack is what lets "return to ancestor" work: after 2.1's (a), (b), the
marker 2.2 is recognised as a sibling of 2.1, not of (b).

Spans (where each clause ends) are added in the next step; here we produce the
ordered clause nodes with depth and parent.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import ParsedDocument
from deal_document_intelligence.segmentation.candidate import Candidate
from deal_document_intelligence.segmentation.candidate_anchors import (
    generate_candidates,
)
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.numbering import (
    is_child_start,
    is_sibling_successor,
    parse_marker,
    starts_sequence,
)
from deal_document_intelligence.segmentation.parsed_marker import ParsedMarker


def body_start_index(
    candidates: list[Candidate], block_chars: dict[str, int], min_body_chars: int = 100
) -> int:
    """Index of the first body clause among block-start candidates.

    v2, family-agnostic: the body begins at the first block-start marker whose
    block carries real clause content (not a short table-of-contents title). If
    that first section is introduced by an article header immediately before it,
    we back up one step to include the article. This works for "1.1.", "Section
    1.1", "Clause 5", or article-only numbering without naming any style. It keys
    on content and structure, not on specific tokens, so it generalises past our
    sample. Robust multi-signal TOC detection (dot leaders, trailing page numbers,
    titles repeated later) remains a tracked follow-up in docs/04.
    """
    first = None
    for j, c in enumerate(candidates):
        if block_chars.get(c.block_id, 0) >= min_body_chars:
            first = j
            break

    if first is None:
        return 0

    # If the first content-bearing marker is a section introduced by an article
    # header right before it, include that article. Back up only one step, so a
    # table-of-contents article two steps back cannot sneak in.
    if (candidates[first].marker_family != "article"
            and first > 0 and candidates[first - 1].marker_family == "article"):
        return first - 1
    return first


def _kind(family: str) -> str:
    """Numbering kind for sibling comparison. Articles, decimal sections, and
    each parenthesised style are distinct kinds, so "(i)" is never a sibling of
    "ARTICLE VIII" just because alpha i = 9 = 8 + 1."""
    if family == "article":
        return "article"
    if family in ("section", "hier-decimal", "decimal"):
        return "decimal"
    return family  # paren-lower / paren-upper / paren-num


def _place(
    stack: list[tuple[ClauseNode, ParsedMarker]],
    marker: ParsedMarker,
    candidate: Candidate,
) -> tuple[int | None, str | None]:
    """Decide (depth, parent_id) for a marker, or (None, None) to skip it."""

    # Sibling of an open level (deepest first): closes everything below it.
    # Siblings must be the same numbering kind, not merely consecutive numbers.
    for level in range(len(stack) - 1, -1, -1):
        same_kind = _kind(stack[level][1].family) == _kind(candidate.marker_family)
        if same_kind and is_sibling_successor(stack[level][1], marker):
            parent_id = stack[level - 1][0].id if level > 0 else None
            return level, parent_id

    # An article is always top level: it can never be nested under another clause,
    # so a stray leading (table-of-contents) article cannot swallow the body.
    if candidate.marker_family == "article":
        return 0, None

    # Child of the current top, or a fresh sub-list opening under it.
    if stack and (is_child_start(stack[-1][1], marker) or starts_sequence(marker)):
        return len(stack), stack[-1][0].id

    # With no open clause: a decimal/section can legitimately open the document,
    # but a parenthesized sub-part ((a), (i), (A)) cannot, it is subordinate by
    # definition. An orphan sub-part (its section was lost from the stack) is
    # skipped rather than promoted to a top-level clause. Recovering such
    # orphans by keeping their section on the stack is a tracked robustness
    # follow-up.
    if not stack:
        if candidate.marker_family.startswith("paren"):
            return None, None
        return 0, None

    return None, None


def decode(document: ParsedDocument) -> list[ClauseNode]:
    block_chars = {b.id: len(b.text) for b in document.blocks}
    candidates = [c for c in generate_candidates(document) if c.at_block_start]
    candidates = candidates[body_start_index(candidates, block_chars) :]

    stack: list[tuple[ClauseNode, ParsedMarker]] = []
    nodes: list[ClauseNode] = []

    for candidate in candidates:
        marker = parse_marker(candidate.marker_family, candidate.marker_text)
        if not marker.path:
            continue

        depth, parent_id = _place(stack, marker, candidate)
        if depth is None:
            continue

        del stack[depth:]  # close any levels at or below the new node's depth
        node = ClauseNode(
            id=f"cl-{len(nodes)}",
            marker_text=candidate.marker_text,
            path=marker.path,
            depth=depth,
            parent_id=parent_id,
            source_offset=candidate.source_offset,
        )
        stack.append((node, marker))
        nodes.append(node)

    return nodes
