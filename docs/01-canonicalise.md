# Canonicalise

The first step our pipeline builds (parsing and OCR are upstream). It turns the
parser's output into one consistent internal document, so every later step is
vendor-agnostic.

## What it does

Normalize whatever the upstream parser produced (docling, Textract, Azure, and
so on) into a single canonical document: the full text, its blocks (headings,
paragraphs, tables), and page plus character offsets.

## Why

We accept any parser, and each emits a different shape. Without this, every
downstream step would need to handle each vendor's format. One canonical shape
with stable offsets also gives evidence a fixed thing to point at.

## Input and output

- In: the upstream parser's output for one document.
- Out: one canonical document (text, blocks, page and character offsets).
