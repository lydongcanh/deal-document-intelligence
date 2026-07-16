"""Baseline Segmenter (stage 4) — groups blocks into clauses at heading
boundaries. Crude on purpose: it's the library/rules baseline the real
contract-aware segmenter must beat. Satisfies the `Segmenter` interface.
"""

from __future__ import annotations

import re

from deal_document_intelligence.contracts import (
    Block,
    BlockType,
    CanonicalDocument,
    ClauseUnit,
    EvidenceSpan,
)

_NUMBER_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)")


class RuleBasedSegmenter:
    def segment(self, document: CanonicalDocument) -> list[ClauseUnit]:
        groups: list[list[Block]] = []
        current: list[Block] = []
        for block in document.blocks:
            if block.type == BlockType.HEADING and current:
                groups.append(current)
                current = []
            current.append(block)
        if current:
            groups.append(current)

        clauses: list[ClauseUnit] = []
        for i, group in enumerate(groups):
            start, end = group[0].char_start, group[-1].char_end
            text = document.slice(start, end)
            head = group[0].text if group[0].type == BlockType.HEADING else None
            number = None
            if head and (m := _NUMBER_RE.match(head)):
                number = m.group(1)
            span = EvidenceSpan(
                page=group[0].page, char_start=start, char_end=end,
                text=text, block_id=group[0].id,
            )
            clauses.append(
                ClauseUnit(
                    id=f"c{i}", text=text, char_start=start, char_end=end,
                    evidence=[span], number=number, heading=head,
                )
            )
        return clauses
