"""A docling-based Parser adapter — lives in the DEMO (a consumer), not the
package. This is exactly how a real consumer would plug their vendor of choice
(docling / AWS Textract / Azure DI) into `deal_document_intelligence`.

It satisfies `deal_document_intelligence.parsing.parser.Parser` structurally:
one `parse(source) -> CanonicalDocument` method, no inheritance.

Design choice: we build the canonical `text` ourselves by concatenating docling's
text items and tracking offsets as we go. That way `document.text[start:end]`
is guaranteed to equal a block's text — evidence integrity holds no matter what
docling reports internally. The same adapter handles PDF/DOCX/scans/markdown,
since docling's converter auto-detects the format.
"""

from __future__ import annotations

from pathlib import Path

from docling.document_converter import DocumentConverter

from deal_document_intelligence.contracts import Block, BlockType, CanonicalDocument

_LABEL_TO_BLOCK_TYPE = {
    "title": BlockType.HEADING,
    "section_header": BlockType.HEADING,
    "list_item": BlockType.LIST_ITEM,
    "page_header": BlockType.PAGE_HEADER,
    "page_footer": BlockType.PAGE_FOOTER,
    "caption": BlockType.CAPTION,
    "text": BlockType.PARAGRAPH,
    "paragraph": BlockType.PARAGRAPH,
}

_SEPARATOR = "\n\n"


class DoclingParser:
    def __init__(self) -> None:
        self._converter = DocumentConverter()

    def parse(self, source: Path) -> CanonicalDocument:
        dl = self._converter.convert(str(source)).document

        parts: list[str] = []
        blocks: list[Block] = []
        cursor = 0
        for i, item in enumerate(dl.texts):
            text = (item.text or "").strip()
            if not text:
                continue

            label = getattr(item.label, "value", str(item.label))
            prov = getattr(item, "prov", None)
            page = (prov[0].page_no if prov and prov[0].page_no else None) or 1

            start = cursor
            end = start + len(text)
            blocks.append(
                Block(
                    id=f"b{i}",
                    type=_LABEL_TO_BLOCK_TYPE.get(label, BlockType.OTHER),
                    text=text,
                    page=page,
                    char_start=start,
                    char_end=end,
                    level=getattr(item, "level", None),
                )
            )
            parts.append(text)
            cursor = end + len(_SEPARATOR)

        return CanonicalDocument(
            doc_id=Path(source).stem,
            text=_SEPARATOR.join(parts),
            blocks=blocks,
            source_path=str(source),
            page_count=max((b.page for b in blocks), default=None),
        )
