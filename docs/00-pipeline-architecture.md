# Pipeline Architecture

A pipeline that turns each deal document into structured, evidence-backed data,
then aggregates it across the room to power AI-agent features.

## Input and output

- Input: a real deal document (PDF, DOCX, or scan), usually messy: OCR noise, headings, tables, pages.
- Output: structured facts per document, plus retrievable text. Every fact links back to its page and exact span, so it is verifiable.

## Approach

Hybrid: structured extraction as the backbone (precise, auditable, comparable, so
it powers checklists, red-flags, and conflict checks), plus embeddings and
retrieval for open-ended Q&A.

## Pipeline

Upstream (bought, not built here): parse the file and OCR it into raw text and
structure (headings, tables, pages), with page and character offsets. Our
pipeline starts from that parsed output.
