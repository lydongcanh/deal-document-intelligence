"""A docling-based Parser, for the demo.

This is a CONSUMER implementation of the package's `Parser` interface
(package/deal_document_intelligence/parsing/parser.py). The package ships no
parser on purpose: parsing/OCR is a commodity. Here we wire docling to the
contract. Swapping to AWS Textract or Azure would just mean writing another
class with the same `parse` method.

The one thing worth getting right is offsets. We build the canonical `text`
ourselves by concatenating docling's text items in order, and we record each
item's char span as we go. That guarantees the invariant every later stage
relies on: `document.text[block.char_start:block.char_end] == block.text`.
"""

from __future__ import annotations

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from deal_document_intelligence.contracts import Block, BlockType, ParsedDocument

# docling labels its text items; map the ones we care about onto our BlockType.
# Anything unmapped falls back to OTHER, so an unexpected label never crashes us.
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

# Blocks are joined by a blank line in the canonical text.
_SEPARATOR = "\n\n"


class DoclingParser:
    """Parses a file into a ParsedDocument using docling."""

    def __init__(self, ocr: bool = False, page_range: tuple[int, int] | None = None) -> None:
        # OCR is only needed for scanned/image PDFs. Our lease is born-digital
        # (it has a real text layer), so we leave OCR off: it is faster and it
        # avoids pulling an OCR model. Set ocr=True for scans.
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = ocr
        # page_range=(first, last), 1-indexed inclusive, to parse a slice of a
        # long document. Handy for testing on the first pages of a 200-page file.
        self._page_range = page_range
        # The converter loads docling's layout models on first use.
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
        )

    def parse(self, source: Path) -> ParsedDocument:
        source = Path(source)
        if self._page_range:
            result = self._converter.convert(str(source), page_range=self._page_range)
        else:
            result = self._converter.convert(str(source))
        docling_doc = result.document

        parts: list[str] = []
        blocks: list[Block] = []
        cursor = 0  # next free char offset in the canonical text

        for index, item in enumerate(docling_doc.texts):
            text = (item.text or "").strip()
            if not text:
                continue

            # docling's label is an enum-like; take its string value.
            label = getattr(item.label, "value", str(item.label))
            # Page number lives in provenance; default to 1 (Block requires >= 1).
            prov = getattr(item, "prov", None)
            page = (prov[0].page_no if prov else None) or 1

            char_start = cursor
            char_end = char_start + len(text)
            blocks.append(
                Block(
                    id=f"b{index}",
                    type=_LABEL_TO_BLOCK_TYPE.get(label, BlockType.OTHER),
                    text=text,
                    page=page,
                    char_start=char_start,
                    char_end=char_end,
                    level=getattr(item, "level", None),
                )
            )
            parts.append(text)
            cursor = char_end + len(_SEPARATOR)

        return ParsedDocument(
            doc_id=source.stem,
            text=_SEPARATOR.join(parts),
            blocks=blocks,
            page_count=max((b.page for b in blocks), default=None),
        )
