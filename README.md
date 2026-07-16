# deal-document-intelligence

An **end-to-end, production-ready** system for turning deal / contract documents
(PDF, DOCX, scans) into structured, **evidence-backed** intelligence — clauses,
entities, obligations and events - plus the applications built on top of them
(search, comparison, policy checks, summaries, Q&A).

## Pipeline

```
PDF / DOCX / scan
        ↓
document parsing & OCR
        ↓
canonical blocks, headings, tables, pages & offsets
        ↓
clause segmentation
        ↓
clause classification
        ↓
entity + obligation/event extraction
        ↓
relation linking & value normalisation
        ↓
evidence-backed JSON
        ↓
search, comparison, policy checks, summaries & Q&A
```

## Design principle: wrap commodities, build differentiation

We do not re-implement solved problems. Every stage is either **bought** (wrap the
best existing library) or **built** (custom — because it measurably beats generic
tools on *deal* documents). Custom effort concentrates on the contract-specific core.

| # | Stage | Decision | Tool / how |
|---|-------|----------|------------|
| 1 | Ingestion | **Buy** | file/format handling |
| 2 | Parsing + OCR | **Buy** | `docling` / `unstructured` (+ Tesseract/EasyOCR for scans) |
| 3 | Structure (blocks/headings/tables/offsets) | **Buy + own adapter** | parser output → our `CanonicalDocument` |
| 4 | Clause segmentation | **Build** | contract-aware numbering/heading/cross-ref logic |
| 5 | Clause classification | **Build** | fine-tuned encoder on CUAD |
| 6 | Entities + obligations/events | **Hybrid** | `GLiNER`/spaCy/Presidio baselines; custom deal roles/obligations/events |
| 7 | Relation linking + normalisation | **Hybrid** | `dateparser`/`price-parser`/`pint` for values; custom linking |
| 8 | Evidence-backed JSON | **Build** (schema) | our Pydantic output contract |
| 9 | Apps (search/compare/policy/Q&A) | **Hybrid** | vector store + embeddings + LLM; custom policy/comparison + evidence grounding |

**Discipline:** baseline every stage with a library first → measure on real deal
documents → build custom only where the metric justifies it.

## Architecture — a library of interfaces, not a framework

This package is meant to be **consumed** without dictating vendors. Two rules:

- **Data flows through typed Pydantic contracts** (`contracts/`, one class per
  file). Every extracted fact carries provenance (page + character offset), so
  any value is traceable to source text.
- **Each stage is an interface** (`Protocol`) with documented input/output.
  Commodity stages (parsing/OCR/structure) ship **no implementation** — the
  consumer plugs in whatever they want (docling, AWS Textract, Azure DI, …). The
  package only *implements* the differentiator stages (segmentation,
  classification, extraction, linking). Vendor wiring lives outside the package.

```
src/deal_document_intelligence/
├── contracts/                # ⭐ one Pydantic model per file (the data backbone)
│   ├── canonical_document.py # + block.py, bbox.py, block_type.py, evidence_span.py
│   ├── clause_unit.py        # + clause_type.py
│   ├── entity.py             # + entity_type.py, obligation.py, event.py, relation*.py
│   ├── extractions.py        #   stage-6 output bundle
│   └── evidence_backed_result.py   # stage-8 output + verify_evidence()
├── parsing/parser.py         # 1-3  Parser interface        [consumer implements]
├── segmentation/segmenter.py # 4     Segmenter interface     [we implement]
├── classification/classifier.py # 5  Classifier interface    [we implement]
├── extraction/extractor.py   # 6     Extractor interface      [we implement]
├── linking/linker.py         # 7     Linker interface         [we implement]
├── assembly/ applications/   # 8-9   assembled by Pipeline / downstream consumers
├── pipeline.py               #       Pipeline: composes any objects matching the interfaces
└── config.py
demo/  eval/  scripts/  tests/  # models/ & data/ gitignored; vendor wiring (docling) lives in demo/, not in-package
```

## Build strategy — walking skeleton first

1. **Phase 0 — contracts.** Define the Pydantic schemas (`CanonicalDocument`,
   `ClauseUnit`, `EvidenceSpan`, `EvidenceBackedResult`). Nails every stage's in/out.
2. **Phase 1 — walking skeleton.** One real document flows through *all* stages
   using libraries / generic baselines end-to-end. Produces real output **and** a
   measured baseline to beat.
3. **Phase 2 — deepen the differentiators.** Replace baselines at stages 4–7 with
   custom, measured models (CUAD fine-tune for stage 5) where they beat generic.
   HF publishing, if any, is an artefact of this phase — not the goal.
4. **Phase 3 — applications & hardening.** Search/Q&A, API, observability
   (Arize Phoenix for the LLM parts), deployment, data governance.

## Data & confidentiality

Real deal documents are **confidential** and must never train a model we
intend to publish. Anything trained for public release uses openly-licensed data
(e.g. **CUAD** - 510 contracts, 41 clause types, extractive-QA, CC BY 4.0).

## Status

- [x] Repo scaffold + Poetry (Python 3.13), dependencies pinned to latest
- [x] CUAD explored — `poetry run python scripts/explore_cuad.py`
- [x] Phase 0 — contracts + module tree
- [x] Phase 1 — walking skeleton (docling demo, all stages, evidence-backed JSON)
- [ ] Phase 2 — custom models (segmentation, clause classification, extraction)
- [ ] Phase 3 — applications & production hardening

## Setup

```bash
poetry install                                   # light stack (core package only)
poetry install --with training                   # + model-training stack
poetry install --with demo                       # + docling, for the demo
poetry run python scripts/explore_cuad.py        # sanity-check the data
poetry run python demo/walking_skeleton.py       # run the end-to-end demo
```
