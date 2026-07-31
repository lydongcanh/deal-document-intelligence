from __future__ import annotations

from deal_document_intelligence.contracts import ParsedDocument
from deal_document_intelligence.segmentation.candidate import Candidate
from deal_document_intelligence.segmentation.markers import scan


def generate_candidates(document: ParsedDocument) -> list[Candidate]:
    """Generate candidate boundary anchors from a parsed document.

    Step 1 of segmentation. High recall on purpose: we surface every possible
    marker, at block starts and inline, each with an exact source offset. Filtering
    false positives (cross-references, dates, percentages) is a later step.
    """

    candidates: list[Candidate] = []
    n = 0
    for block in document.blocks:
        # Offset of the first non-space character, so we can flag block-start markers.
        first_non_space = len(block.text) - len(block.text.lstrip())
        for family, marker_text, start, _end in scan(block.text):
            # block.text == document.text[block.char_start:block.char_end], so a
            # position inside the block maps to source by adding block.char_start.
            candidates.append(
                Candidate(
                    id=f"cand-{n}",
                    source_offset=block.char_start + start,
                    block_id=block.id,
                    marker_text=marker_text,
                    marker_family=family,
                    at_block_start=(start == first_non_space),
                )
            )
            n += 1
    return candidates
