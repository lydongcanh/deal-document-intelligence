# deal-document-intelligence

Turns deal / contract documents (PDF, DOCX, scans) into structured,
evidence-backed data (clauses, entities, obligations, events), then aggregates it
across a whole data room. The architecture and contracts target production; most
stages are still library baselines or interface-only. See `docs/` for the full
design and honest per-stage status.

## Pipeline

```
UPSTREAM (bought): ingest + OCR  ->  ParsedDocument
 1-2  Canonicalise + reconstruct structure (blocks, headings, tables, offsets)
 3    Detect language, then document type   (type routes the rest)
 4    Segment into clauses                   (contracts only)
 5    Classify clauses
 6-7  Extract entities, relations, obligations / events
 8    Normalise values + resolve aliases across the room
 9    Aggregate -> document + deal intelligence
 10   Persist (evidence, confidence, model / version)
```

Cross-cutting: every fact carries an evidence span (page + character offset), a
confidence, and a model / version stamp, so any output is traceable to source.
Deal-level is first-class (entities resolved across all documents, not one file at
a time) and the design is multilingual from stage 3 on.

## Design principle

Wrap commodities, build differentiation. Each stage is either bought (wrap the best
library: ingest / OCR, parsing) or built (custom, where it measurably beats generic
tools on deal documents: segmentation, classification, extraction, linking).
Baseline with a library first, measure on real documents, build custom only where
the metric justifies it.

## Architecture

A library of typed contracts and stage interfaces, not a framework.

- `contracts/`: Pydantic models, one class per file. Every fact carries provenance.
- `interfaces/`: one `Protocol` per stage. Commodity stages ship no implementation;
  the consumer plugs in a vendor (docling, Textract, Azure DI). The package
  implements only the differentiator stages.
- `segmentation/`, `classification/`: the implemented differentiator stages.
- `pipeline.py` (single document) and `deal_pipeline.py` (room -> `DealIntelligence`).

Supporting: `training/` (model building), `demo/` (runnable docling consumer),
`eval/` (per-feature scoring), `tests/`, `docs/` (living reports), `artifacts/`
(gitignored data / models / outputs).

## Status

- Phase 0 (contracts + 10-stage pipeline): done.
- Phase 1 (walking skeleton: one document through all stages, document + deal level,
  evidence-backed JSON): done.
- Phase 2 (differentiator models): in progress.
  - Stage 4 clause segmentation: deterministic core built, mean F1 0.98 at the
    section level on a narrow slice (SEC merger / SPA filings, English, TOC-derived
    gold). Not yet validated on OCR, non-English, or other document types. Paused;
    see `docs/04-segment-clauses.md`.
  - Stage 5 clause classification: dataset built (leakage-checked) + Legal-XLM-R
    trained (early checkpoint).
  - Stage 3 document type: taxonomy defined (`docs/03-document-type.md`); detector
    not built.
- Phase 3 (applications + hardening): not started.

## Data

Real deal documents are confidential and never train a model we intend to publish.
Anything for public release uses openly-licensed data (e.g. CUAD, CC BY 4.0).

## Setup

Common workflows are in the Makefile (`make help`). Quick start:

```bash
poetry install --with demo && poetry run python demo/main.py   # parse -> language -> segment demo
poetry install --with dev  && poetry run pytest                # tests
```
