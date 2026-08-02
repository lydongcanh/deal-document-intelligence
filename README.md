# deal-document-intelligence

A **walking skeleton toward a production** system for turning deal / contract
documents (PDF, DOCX, scans) into structured, **evidence-backed** intelligence —
clauses, entities, obligations and events - plus the applications built on top of
them (search, comparison, policy checks, summaries, Q&A). The architecture and
contracts target production; most stages are still library baselines and the one
trained model (stage 5) is an early checkpoint — see `docs/` for status.

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
| 1 | Canonicalise OCR text | **Buy + adapter** | consumer adapter → `ParsedDocument` |
| 2 | Reconstruct structure | **Buy + own adapter** | parser output → blocks/headings/tables/offsets |
| 3 | Detect language & doc type | **Buy / light** | language ID (built) + doc-type classifier (deferred) |
| 4 | Segment sections & clauses | **Build** | contract-aware deterministic core built; English-only so far |
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
package/deal_document_intelligence/    # the library (one package)
├── contracts/                     #   typed Pydantic models, one per file (~27)
│   ├── parsed_document.py         #   stage 1-2 output; + block, bbox, block_type, evidence_span
│   ├── segmented_clause.py        #   stage-4 clause (structural); + clause_role, direct spans
│   ├── clause_classification.py   #   stage-5 output, keyed by clause id (separate contract)
│   ├── segmentation_result.py     #   stage-4 return: clauses + SegmentationConfidence (review gate)
│   ├── entity.py / relation*.py   #   stage 6-7 facts + their types
│   ├── evidence_backed_result.py  #   stage-9a per-document result + verify_evidence()
│   └── deal_intelligence.py       #   stage-9b cross-document + canonical_entity, entity_mention
├── interfaces/                    #   one Protocol per stage — the whole pipeline contract:
│                                  #   Parser, LanguageDetector, DocumentTypeDetector,
│                                  #   ClauseSegmenter, ClauseClassifier, EntityExtractor,
│                                  #   RelationExtractor, EntityResolver, DealAggregator
├── segmentation/                  # 4  IMPLEMENTED: DeterministicClauseSegmenter + core
├── classification/                # 5  IMPLEMENTED: TransformerClauseClassifier (CUAD)
├── pipeline.py                    #      single-document Pipeline (stages wired via Protocols)
└── deal_pipeline.py               #      DealPipeline (many docs → DealIntelligence)
# Other stages (parse, language, extraction, resolution, aggregation) are
# interface-only today: consumer-supplied or not yet built.
training/   # 🔬 model building, per stage (data prep, train, evaluate, explore)
demo/       # ▶️ runnable consumer (docling parser + built stages)
eval/       # 📏 per-feature evaluation (e.g. clause_segmentation: gold + scorer)
tests/      # ✅ tests (root, outside the package — standard)
docs/       # 📄 living technical reports
artifacts/  #   gitignored: data/ (datasets) · models/ (checkpoints) · outputs/ (logs)
```

## Build strategy — walking skeleton first

1. **Phase 0 — contracts.** Define the Pydantic schemas (`ParsedDocument`,
   `SegmentedClause`, `EvidenceSpan`, `EvidenceBackedResult`). Nails every stage's in/out.
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
- [x] CUAD explored — `training/clause_classification/explore_cuad.py`
- [x] Phase 0 — contracts + module tree
- [x] Phase 0.5 — pipeline revised to 10 stages; contracts + interfaces evolved (deal-level, multilingual, `model_version` provenance)
- [x] Phase 1 — walking skeleton: docling demo, all stages, document + deal-level (cross-doc) intelligence, evidence-backed JSON
- [ ] Phase 2 — custom models (segmentation, clause classification, extraction)
  - [~] stage 4 — clause segmentation deterministic core built + measured: mean F1
    **0.98** at the section level on a narrow slice (15 US SEC merger/SPA filings,
    born-digital, English; gold auto-derived from each document's own table of
    contents). Ships typed hierarchy, exact spans, region namespaces, and a
    fail-safe confidence gate. NOT yet validated on OCR, non-English, or other
    document types; see `docs/04-segment-clauses.md` for the honest scope and the
    known defects. The learned boundary model (Phase 3) is not started.
  - [x] stage 5 — dataset built (leakage-checked) + Legal-XLM-R trained (1 epoch): test macro-F1 **0.246** vs 0.162 floor (all 41 deal types)
- [ ] Phase 3 — applications & production hardening

## Setup

Common workflows are wrapped in a **Makefile** — run `make help` to list them
(`make clause-dataset`, `make clause-train`, `make test`, …). Raw commands:

```bash
poetry install                                   # light core (pydantic only)
poetry install -E classification                  # + trained clause classifier (torch/transformers)
poetry install --with training                   # + model-training stack
poetry install --with demo                       # + docling, for the demo
poetry install --with dev && poetry run pytest    # tests
poetry run python training/clause_classification/explore_cuad.py   # sanity-check the data
poetry run python demo/main.py                   # run the parse → language → segment demo
```
Generated artifacts (datasets, model checkpoints, run outputs) live under
`artifacts/` and are gitignored.
