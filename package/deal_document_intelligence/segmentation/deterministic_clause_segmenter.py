from __future__ import annotations

import bisect
import re

from deal_document_intelligence.contracts import (
    ClauseRole,
    EvidenceSpan,
    ParsedDocument,
    SegmentationResult,
    SegmentedClause,
)
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.confidence import assess_confidence
from deal_document_intelligence.segmentation.spans import clause_tree

_ROLE_BY_FAMILY = {
    "article": ClauseRole.ARTICLE,
    "region": ClauseRole.REGION,
    "section": ClauseRole.SECTION,
    "hier-decimal": ClauseRole.SECTION,
    "decimal": ClauseRole.SECTION,
}

# A clause title is a short phrase ("Termination", "Governing Law"); a candidate
# longer than this is the clause's body prose running on, not a heading, so drop
# it rather than store a sentence as the title. ~100 chars is roughly one line.
_MAX_HEADING_CHARS = 100


def _role(marker_family: str) -> ClauseRole:
    """Article, region, numbered section, or parenthesised sub-clause."""
    return _ROLE_BY_FAMILY.get(marker_family, ClauseRole.SUBCLAUSE)


def _number(node: ClauseNode) -> str:
    """The clause's number. For article-relative sections the decoder re-based the
    path onto the real article, so reflect that in the displayed number too:
    'Section 1.02' under Article 2 becomes 'Section 2.02', keeping the drafter's
    zero-padding. Every other marker keeps its source rendering."""
    raw = node.marker_text.strip().rstrip(".")
    lead = re.search(r"\d+", raw)
    if lead and node.path and int(lead.group()) != node.path[0]:
        raw = raw[: lead.start()] + str(node.path[0]) + raw[lead.end() :]
    return raw


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

    return head if head and len(head) <= _MAX_HEADING_CHARS else None


def _evidence(
    document: ParsedDocument, block_starts: list[int], start: int, end: int
) -> list[EvidenceSpan]:
    """One evidence span per page the clause covers, so a clause that runs across
    a page break is no longer recorded as a single page. Each span is clipped to
    the clause's extent on that page and stays source-aligned by offset."""
    by_page: dict[int, tuple[int, int]] = {}
    i = max(bisect.bisect_right(block_starts, start) - 1, 0)
    for block in document.blocks[i:]:
        if block.char_start >= end:
            break
        lo, hi = max(start, block.char_start), min(end, block.char_end)
        if lo < hi:
            prev = by_page.get(block.page)
            by_page[block.page] = (
                (lo, hi) if prev is None else (min(prev[0], lo), max(prev[1], hi))
            )
    return [
        EvidenceSpan(page=page, char_start=lo, char_end=hi, text=document.text[lo:hi])
        for page, (lo, hi) in sorted(by_page.items())
    ]


class DeterministicClauseSegmenter:
    """DeterministicClauseSegmenter: the ClauseSegmenter interface implementation (stage 4).

    Runs the deterministic core (candidates -> grammar -> decoder -> spans) and
    converts the clause tree into the package's `SegmentedClause` contract. Each unit
    carries its inclusive text (the clause plus its sub-parts, so it is meaningful
    on its own) with page-level evidence, plus the full hierarchy as typed fields
    (depth, parent, path, role) and its own `direct_spans`, so a consumer can walk
    the tree or pick a granularity without re-parsing numbers.
    """

    def segment(self, document: ParsedDocument) -> SegmentationResult:
        block_starts = [b.char_start for b in document.blocks]
        nodes = clause_tree(document)
        units: list[SegmentedClause] = []
        for node in nodes:
            start, end = node.source_offset, node.char_end or node.source_offset
            units.append(
                SegmentedClause(
                    id=node.id,
                    text=document.text[start:end],
                    char_start=start,
                    char_end=end,
                    number=_number(node),
                    heading=_heading(document.text, node),
                    depth=node.depth,
                    parent_id=node.parent_id,
                    path=list(node.path),
                    role=_role(node.marker_family),
                    direct_spans=list(node.direct_spans),
                    evidence=_evidence(document, block_starts, start, end),
                )
            )
        # Bundle the trust score so a caller cannot take the clauses without it.
        return SegmentationResult(clauses=units, confidence=assess_confidence(document, nodes))
