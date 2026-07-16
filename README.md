# deal-document-intelligence

An **end-to-end, production-ready** system for turning deal / contract documents
(PDF, DOCX, scans) into structured, **evidence-backed** intelligence — clauses,
entities, obligations and events - plus the applications built on top of them
(search, comparison, policy checks, summaries, Q&A).

## Pipeline

```
UPSTREAM (commodity, consumer-supplied):  Ingest (PDF/DOCX/scan) → OCR
        ↓  OCR result
 1. Canonicalise OCR text
 2. Reconstruct document structure (blocks, headings, tables, pages, offsets)
 3. Detect language & document type
 4. Split into sections & clauses
 5. Classify clauses
 6. Extract entities
 7. Extract relations & obligations/events
 8. Normalise values & resolve aliases (coreference)
 9. Aggregate → (a) document intelligence  (b) deal intelligence [cross-document]
10. Persist results
        ↓
DOWNSTREAM consumers:  search, comparison, policy checks, summaries, Q&A

⟂ cross-cutting on EVERY stage: evidence spans + confidence + model/version
```

**Scope:** *deal-level is first-class* — entities are resolved and aggregated
across **all documents in a data room**, not one file at a time. *Multilingual
from the start* — stage 3 routes by detected language; models are multilingual
(XLM-R / mDeBERTa), value normalisation is locale-aware.

## Design principle: wrap commodities, build differentiation

We do not re-implement solved problems. Every stage is either **bought** (wrap the
best existing library) or **built** (custom — because it measurably beats generic
tools on *deal* documents). Custom effort concentrates on the contract-specific core.

| # | Stage | Decision | Tool / how |
|---|-------|----------|------------|
| — | Ingest + OCR (upstream) | **Buy** | consumer-supplied: Textract / Azure DI / docling |
| 1 | Canonicalise OCR text | **Buy + adapter** | consumer adapter → `CanonicalDocument` |
| 2 | Reconstruct structure | **Buy + own adapter** | parser output → blocks/headings/tables/offsets |
| 3 | Detect language & doc type | **Buy / light** | language ID + doc-type classifier (routes models) |
| 4 | Segment sections & clauses | **Build** | contract-aware, multilingual |
| 5 | Classify clauses | **Build** | multilingual encoder (XLM-R/mDeBERTa) fine-tuned on CUAD |
| 6 | Extract entities | **Hybrid** | multilingual NER baseline + custom deal entities |
| 7 | Relations & obligations/events | **Build** | deal-specific |
| 8 | Normalise + resolve aliases | **Hybrid** | locale-aware value normalisation + entity/coref resolution |
| 9 | Aggregate → doc + deal intelligence | **Build** | per-doc, then cross-document resolution & aggregation |
| 10 | Persist (evidence, confidence, versions) | **Engineering** | storage + provenance |

Applications (search/compare/policy/Q&A) are downstream consumers of the deal
intelligence, not pipeline stages.

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
├── parsing/parser.py         # 1-2  Parser interface            [consumer implements]
├── language/                 # 3    language + doc-type detect   [planned]
├── segmentation/segmenter.py # 4    Segmenter interface         [we implement]
├── classification/classifier.py # 5 Classifier interface        [we implement]
├── extraction/extractor.py   # 6    Extractor interface          [we implement]
├── linking/linker.py         # 7    Linker (relations/obligs.)   [we implement]
├── resolution/               # 8    normalise + alias resolution [planned]
├── aggregation/              # 9    document + deal intelligence [planned]
├── assembly/                 # 10   persist / evidence output
├── pipeline.py               #      composes any objects matching the interfaces
└── config.py
# planned contracts: language/doc_type on CanonicalDocument; model_version on items;
#                    deal.py, canonical_entity.py, deal_intelligence.py (deal-level)
demo/  eval/  scripts/  tests/   # models/ & data/ gitignored; docling wiring lives in demo/
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
