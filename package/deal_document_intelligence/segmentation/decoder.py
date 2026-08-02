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

Known limitation: when the parser merges an article header with its first section
into one block, that first section arrives inline and is not seen here, so it can
be missed. Recovering inline sections without disturbing the rest is a tracked
follow-up (see docs/04); an earlier attempt regressed the well-structured
documents and was reverted.

Spans (where each clause ends) are added in the next step; here we produce the
ordered clause nodes with depth and parent.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import ParsedDocument
from deal_document_intelligence.segmentation.candidate import Candidate
from deal_document_intelligence.segmentation.candidate_anchors import generate_candidates
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.numbering import (
    is_child_start,
    is_sibling_successor,
    parse_marker,
    starts_sequence,
)
from deal_document_intelligence.segmentation.parsed_marker import ParsedMarker


def _lead_in_start(candidates: list[Candidate], first: int) -> int:
    """Back up from `first` to the start of its opening numbering run.

    The opening sections and the article that parents them are often short heading
    blocks (title split from the body prose) whose own content run is short, so the
    first marker body-start keeps is 1.02, not ARTICLE I / 1.01. Walk backwards chaining
    section to section: an earlier sibling opener (1.01 before 1.02) or the article
    that introduces the run (ARTICLE I -> 1.01), skipping the parenthesised
    sub-parts between sections. Each step must match the run head by numbering, so
    a table-of-contents tail (11.02, ARTICLE XI) that does not chain into this run
    is never swept in.
    """
    head = parse_marker(candidates[first].marker_family, candidates[first].marker_text)
    start = first
    k = first - 1
    while k >= 0:
        if candidates[k].marker_family.startswith("paren"):
            k -= 1  # a descendant sub-part of an earlier section in the run
            continue
        prev = parse_marker(candidates[k].marker_family, candidates[k].marker_text)
        if is_child_start(prev, head):  # the article/section that opens the run
            return k
        if not is_sibling_successor(prev, head):  # not an earlier sibling opener
            return start
        start, head, k = k, prev, k - 1
    return start


def body_start_index(
    candidates: list[Candidate], text_len: int, min_content_chars: int = 100
) -> int:
    """Index of the first body clause among block-start candidates.

    The body begins at the first section-level marker (never a parenthesised
    sub-part) whose content run is substantial, then backs up over its opening
    lead-in (see `_lead_in_start`). The content run is the text from a marker to
    the next section-level marker, that is the marker's own clause and its
    sub-parts. This is the structural signal that separates a table-of-contents
    entry from a real clause: a TOC line has almost no text before the next entry,
    while a real clause runs for paragraphs even when its title was split into a
    short heading block (so "1.1 Purchase and Sale." with the body in the next
    block still qualifies, which a block-length test missed).

    `min_content_chars` is the one hand-tuned value here: ~100 chars is about a
    line, enough to separate a TOC entry (a title plus a page number, well under a
    line) from a real clause (at least a sentence). It is deliberately generous so
    the run only needs to clear "more than a title". Making this fully relative
    (comparing to the document's own TOC-vs-body run distribution) is the tracked
    robust multi-signal TOC detection follow-up in docs/04.
    """
    # For each position, the offset of the next section-level (non-paren) marker,
    # scanning right to left so each entry sees the nearest one after it.
    next_section = [text_len] * len(candidates)
    following = text_len
    for j in range(len(candidates) - 1, -1, -1):
        next_section[j] = following
        if not candidates[j].marker_family.startswith("paren"):
            following = candidates[j].source_offset

    for j, c in enumerate(candidates):
        if (not c.marker_family.startswith("paren")
                and next_section[j] - c.source_offset >= min_content_chars):
            return _lead_in_start(candidates, j)
    return 0


def _article_adopts_section(parent: ParsedMarker, marker: ParsedMarker) -> bool:
    """True if an article should adopt a decimal section as its first child.

    Normally the first section (2.1, 6.01) opens the level via `is_child_start`
    because it ends in 1. But its real opener can be dropped or reordered: in one
    document "Section 6.01" is extracted *before* its own "ARTICLE VI" header, so
    the article first meets section 6.02. We still adopt it, provided the section's
    leading ordinal matches the article number (6.x under ARTICLE VI), so a whole
    article's sections are not lost for want of their .01. The leading-ordinal
    match keeps this from nesting 2.1 under an unrelated ARTICLE I.
    """
    return (
        parent.family == "article"
        and marker.family in ("section", "hier-decimal", "decimal")
        and len(marker.path) >= 2
        and bool(parent.path)
        and marker.path[0] == parent.path[0]
    )


def _kind(family: str) -> str:
    """Numbering kind for sibling comparison. Articles, regions, decimal sections,
    and each parenthesised style are distinct kinds, so "(i)" is never a sibling of
    "ARTICLE VIII" just because alpha i = 9 = 8 + 1, and Schedule A/B are siblings
    of each other but not of an article."""
    if family == "article":
        return "article"
    if family == "region":
        return "region"
    if family in ("section", "hier-decimal", "decimal"):
        return "decimal"
    return family  # paren-lower / paren-upper / paren-num


def _article_adopts_relative_section(parent: ParsedMarker, marker: ParsedMarker) -> bool:
    """True for article-relative numbering: some documents restart section numbers
    inside every article ("Section 1.01" under Article 2, 3, ... rather than 2.01,
    3.01). Adopt the opener of such a run (its minor starts at 1) even though its
    leading ordinal does not match the article number; the rest sibling-chain off
    it, and `decode` re-bases their paths onto the real article number."""
    return (
        parent.family == "article"
        and marker.family in ("section", "hier-decimal")
        and len(marker.path) >= 2
        and marker.path[0] != parent.path[0]
        and starts_sequence(marker)
    )


def _region_adopts_section(parent: ParsedMarker, marker: ParsedMarker) -> bool:
    """True if a region (Schedule/Annex/Exhibit) should adopt a section as its
    child. A region opens its own numbering namespace: the sections inside it are
    numbered independently of the main body and of the region's own letter, so we
    adopt any decimal section rather than trying to match numbers, which is what
    keeps a schedule's "7.2" from being lost or fused into the main hierarchy."""
    return parent.family == "region" and marker.family in ("section", "hier-decimal")


def _place(
    stack: list[tuple[ClauseNode, ParsedMarker]],
    marker: ParsedMarker,
    candidate: Candidate,
) -> tuple[int | None, str | None]:
    """Decide (depth, parent_id) for a marker, or (None, None) to skip it."""

    # Sibling of an open level (deepest first), same numbering kind only. One
    # dropped ordinal is tolerated (max_skip=1) so a single missing marker does not
    # reject the whole rest of the run (1.1 -> 1.3 still continues the sequence).
    # One, not more: a two-step gap (1.1 -> 1.4) is more likely two unrelated
    # numbers than two markers dropped in a row, so widening the tolerance would
    # start fusing distinct clauses.
    for level in range(len(stack) - 1, -1, -1):
        same_kind = _kind(stack[level][1].family) == _kind(candidate.marker_family)
        if same_kind and is_sibling_successor(stack[level][1], marker, max_skip=1):
            parent_id = stack[level - 1][0].id if level > 0 else None
            return level, parent_id

    # An article or a region (Schedule/Annex/Exhibit) is always top level. A region
    # also resets the stack, so entering the schedules closes the main body and
    # opens a fresh namespace instead of corrupting the main hierarchy.
    if candidate.marker_family in ("article", "region"):
        return 0, None

    # Child of the current top: a decimal section nests only by path (2 -> 2.1);
    # only a parenthesised sub-part may open a fresh sub-list under its section
    # ((a), (i)). This stops "2.1" from becoming a child of "1.1" just because it
    # ends in 1.
    if stack and (
        is_child_start(stack[-1][1], marker)
        or _article_adopts_section(stack[-1][1], marker)
        or _article_adopts_relative_section(stack[-1][1], marker)
        or _region_adopts_section(stack[-1][1], marker)
        or (starts_sequence(marker) and candidate.marker_family.startswith("paren"))
    ):
        return len(stack), stack[-1][0].id

    # With no open clause: a decimal/section can open the document, but a
    # parenthesised sub-part is subordinate by definition, so an orphan one is
    # skipped rather than promoted to a top-level clause.
    if not stack:
        if candidate.marker_family.startswith("paren"):
            return None, None
        return 0, None

    return None, None


def _canonical_path(
    marker: ParsedMarker, stack: list[tuple[ClauseNode, ParsedMarker]], depth: int
) -> tuple[int, ...]:
    """The path stored on the node. For article-relative numbering (a section
    whose leading ordinal differs from its enclosing article), re-base the leading
    component onto the real article number, so "Section 1.02" under Article 2 gets
    the canonical path (2, 2) and is globally unique. Otherwise the parsed path."""
    if (
        depth >= 1
        and marker.family in ("section", "hier-decimal")
        and stack
        and stack[0][1].family == "article"
        and marker.path
        and marker.path[0] != stack[0][1].path[0]
    ):
        return (stack[0][1].path[0],) + marker.path[1:]
    return marker.path


def decode(document: ParsedDocument) -> list[ClauseNode]:
    candidates = [c for c in generate_candidates(document) if c.at_block_start]
    candidates = candidates[body_start_index(candidates, len(document.text)):]

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
            marker_family=candidate.marker_family,
            path=_canonical_path(marker, stack, depth),
            depth=depth,
            parent_id=parent_id,
            source_offset=candidate.source_offset,
        )
        # The stack keeps the RAW marker so subsequent sections sibling-chain on the
        # body's own numbering; only the node's stored path is canonicalised.
        stack.append((node, marker))
        nodes.append(node)

    return nodes
