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

## Flow diagram

Quality is assessed at parse time and gates everything after it: a document that is
blank, unreadable, or encrypted short-circuits to review before any further compute.
Language and document type are then independent sibling steps. The document-type
step predicts `type`; `form` and `category` are derived from it by lookup. `form` is
the router: it decides which stage-4+ pipeline the document enters. Solid arrows
carry the data contract named on the edge; dashed arrows are abstain / escalation
paths.

```mermaid
flowchart TD
    RAW["Deal file (PDF / DOCX / scan)"]

    subgraph UP["Upstream (bought, consumer-supplied)"]
        OCR["Ingest + OCR"]
    end

    subgraph DOCP["Per-document pipeline"]
        S1["1-2 Parse + reconstruct structure<br/>(Parser)"]
        QGATE{"quality ok?"}
        LANG["3a Detect language<br/>(LanguageDetector)"]
        TYPE["3b Detect document type<br/>(DocumentTypeDetector)"]
        ROUTE{"route by form"}
        C4["4 Segment clauses<br/>(ClauseSegmenter)"]
        C5["5 Classify clauses<br/>(ClauseClassifier)"]
        STMT["Table + figure extraction<br/>(planned)"]
        REC["Event / field extraction<br/>(planned)"]
        REP["Summarise + claim extraction<br/>(planned)"]
        CORR["Metadata + cross-refs<br/>(planned)"]
        S6["6 Extract entities"]
        S7["7 Relations + obligations / events"]
        S8["8 Normalise values + resolve aliases"]
        S9a["9a Aggregate to document intelligence"]
    end

    REVIEW["Human review / escalation"]

    subgraph DEALL["Deal-level (across the whole room)"]
        S9b["9b Cross-document resolve + aggregate"]
        DI["DealIntelligence"]
        S10["10 Persist (evidence, confidence, versions)"]
    end

    RAW --> OCR
    OCR -->|"raw text + layout"| S1
    S1 -->|"ParsedDocument + quality_status"| QGATE
    QGATE -.->|"blank / unreadable / encrypted"| REVIEW
    QGATE -->|"ok"| LANG
    LANG -->|"+ language"| TYPE
    TYPE -->|"type (+subtype); form + category derived"| ROUTE
    TYPE -.->|"Unknown"| REVIEW

    ROUTE -->|"contract"| C4
    ROUTE -->|"statement"| STMT
    ROUTE -->|"record"| REC
    ROUTE -->|"report"| REP
    ROUTE -->|"correspondence"| CORR

    C4 -->|"SegmentationResult"| C5
    C4 -.->|"needs_review (SegmentationConfidence)"| REVIEW
    C5 -->|"ClauseClassification[]"| S6
    STMT --> S6
    REC --> S6
    REP --> S6
    CORR --> S6

    S6 -->|"Entity[]"| S7
    S7 -->|"Relation[] / Obligation[]"| S8
    S8 -->|"resolved facts"| S9a
    S9a -->|"EvidenceBackedResult (one per doc)"| S9b
    S9b --> DI
    DI --> S10

    classDef built fill:#e6ffed,stroke:#2da44e,color:#03260f;
    classDef planned fill:#f6f8fa,stroke:#8c959f,stroke-dasharray:4 3,color:#24292f;
    classDef buy fill:#fff8e6,stroke:#d4a72c,color:#3b2f00;
    class C4,C5,LANG built;
    class STMT,REC,REP,CORR,S6,S7,S8,S9a,S9b,S10,TYPE planned;
    class OCR,S1 buy;
```

Legend: green = built in-package (segmentation, clause classification; language
detection also built, doc-type detection not yet); amber = bought / consumer-supplied;
grey dashed = interface-only or planned.

Cross-cutting on every stage (not drawn, to keep the diagram readable): each
extracted fact carries an evidence span (page + character offset), a confidence,
and a model / version stamp. That is what makes any output traceable to source.

## Stage input / output

| stage | input | output contract | status |
|---|---|---|---|
| 1-2 Parse + structure | raw file | `ParsedDocument` + `quality_status` | bought (demo: docling) |
| 3a Detect language | `ParsedDocument` | language attribute | built |
| 3b Detect document type | `ParsedDocument` (+ language) | `DetectedDocumentType` (predicts type + subtype; form, category derived) | planned |
| 4 Segment (form=contract) | `ParsedDocument` | `SegmentationResult` (clauses + confidence) | built |
| 5 Classify (form=contract) | `SegmentationResult` | `ClauseClassification[]` | built |
| statement / record / report / correspondence | `ParsedDocument` | form-specific facts | planned |
| 6 Entities | `ParsedDocument` + segments | `Entity[]` | interface-only |
| 7 Relations + obligations | `Entity[]` + segments | `Relation[]` / `Obligation[]` | interface-only |
| 8 Normalise + resolve | extracted facts | resolved, normalised facts | interface-only |
| 9a Document aggregate | all per-doc facts | `EvidenceBackedResult` | walking skeleton |
| 9b Deal aggregate | `EvidenceBackedResult[]` | `DealIntelligence` | walking skeleton |
| 10 Persist | results | stored records + provenance | engineering |
