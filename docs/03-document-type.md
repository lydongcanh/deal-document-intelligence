# Detect document type

Status: the taxonomy is now defined (this document, 2026-08-03). The contract and
interface exist (`DocumentTypeDetector`, `DetectedDocumentType`), but no detector
is implemented yet, and the first-tier approach (heuristic vs LLM) is still to be
chosen. The full trained production detector remains deferred until the dataset
program and a deal-level consumer exist (see "The full production detector").

## What the stage does

Classify a whole document as one of a fixed set of deal document types, with a
confidence, an explicit Unknown path, and a review flag.

Its real job is to be the **router**. The type decides which processing pipeline a
document goes through, and how it is organised at the deal level. Run the wrong
pipeline (for example clause segmentation on a financial statement, which has no
clauses) and you get garbage. The type is what prevents that, so it has to come
before the heavy extraction stages, not after.

## Taxonomy

A document answers several independent questions, so a label carries several
fields. They vary independently and serve different consumers, which is why one
field is not enough.

- **type**: "what exactly is this?" The specific leaf label (nda, lease, financial
  statement, board minutes). The primary, user-facing output. It is the hardest to
  always get right, so the detector may abstain on it.
- **subtype** (optional): a finer label under a broad type, populated only when the
  text makes it clear. It exists because some types are too broad to pick an
  extractor on their own: a `certificate` of incorporation, an insurance
  certificate, and a share certificate hold unrelated fields; an environmental
  `report` and an audit `report` need different key-term schemas. Type stays a
  manageable set; subtype carries the refinement downstream extraction needs.
- **category**: "what area of the deal does it belong to?" The workstream grouping
  (corporate, financial, commercial, and so on). Coarse and easy to get right. It
  drives deal-level organisation (checklists, grouping, completeness) and acts as
  the graceful fallback: when the exact type is unclear we can still report the
  category.
- **form**: "how is it built, so how do we process it?" This routes to a processing
  pipeline FAMILY. Crucially, form is NOT derivable from category: articles of
  association are category `corporate` but form `contract` (clause-structured); a
  cap table is also `corporate` but form `statement` (a grid of figures). You need
  both.
- **quality_status**: a separate operational axis (`ok`, `low_ocr_quality`,
  `unreadable`, `blank`, `encrypted_or_restricted`, `unsupported_format`), assessed
  at parse/OCR time (stages 1-2), where the signal actually lives. It acts as a GATE
  at the start of this stage: a non-`ok` document short-circuits to review before any
  language, type, or segmentation compute is spent. This stage consumes it; it never
  computes it. It is kept apart from the semantic label on purpose: "cannot read it"
  is not "do not know its type", and conflating them poisons both routing and
  evaluation (an OCR failure must not count as a classification error).

Form selects a pipeline *family*, not a single implementation. The exact extractor
is chosen by form together with type/subtype: within `statement`, a P&L needs
line-item extraction while a cap table needs ownership-graph extraction; within
`record`, minutes need event extraction while a certificate needs field extraction.
Modality (native PDF, scan, spreadsheet, slide deck) and quality refine the route
further, and the eventual trained classifier should use layout and visual signals,
not text alone (as in LayoutLM-style models), especially for cap tables, registers,
certificates, presentations and financial statements.

What the detector actually predicts is only **type** (plus **subtype** when the text
is clear). **category** and **form** are static projections of type, filled by
lookup, not predicted independently: category is the workstream view (consumed at the
deal level for the room index and completeness checklists, and the fallback label
when type is abstained), form is the how-to-process view (consumed by the router).
The one wrinkle is the form-heterogeneous types: a litigation document may be a
pleading (`report`) or a settlement (`contract`), so its form is resolved from the
subtype. This is why the flow reads `form` early and the other fields later: form is
just the routing-facing projection of type; type itself drives the classification
ontology and the user-facing label immediately after routing, and category drives
deal-level grouping once that stage exists.

Each form still gets structural segmentation, just a different kind with a
different ontology:

| form | structural segmentation | classification / extraction |
|---|---|---|
| `contract` | clause / provision boundaries (stage 4) | clause-type classification + obligations |
| `statement` | statement / note / table regions | figures, line items, ownership graph |
| `record` | agenda + resolution items, or record fields | events / decisions, or schema fields |
| `report` | headings / sections, or slides | claims, figures, summary |
| `correspondence` | thread / quoted-message boundaries | metadata, cross-references |

### The types

Only types that are both useful and distinguishable from the text are listed,
grouped by form. Two rules shaped the set: collapse variants that run the identical
pipeline (SPA, asset purchase and merger become one "acquisition agreement"; teaser,
CIM and management deck become one "information memorandum / presentation"), and
split only where the field schema genuinely differs, carried by `subtype` rather
than a new top-level type. This is a decided baseline, not an exhaustive list; a new
type earns a row only when it is common in real rooms AND routes or extracts
differently from every existing one.

| type | category | form |
|---|---|---|
| Acquisition agreement (SPA / asset / merger) | transaction | contract |
| Shareholders / investment agreement | corporate | contract |
| Commercial agreement (customer / supplier / distribution) | commercial | contract |
| Employment agreement | employment | contract |
| Lease / property agreement | property | contract |
| Financing agreement (loan / facility / security) | financial | contract |
| IP / licence agreement | ip | contract |
| NDA / confidentiality | transaction | contract |
| Insurance policy | insurance | contract |
| Disclosure letter & schedules | transaction | contract |
| Articles / bylaws / constitution | corporate | contract |
| Financial statements (audited + management accounts) | financial | statement |
| Financial model / debt schedule | financial | statement |
| Tax document (returns, computations) | financial | statement |
| Cap table & statutory registers | corporate | statement |
| Board / shareholder minutes & resolutions | corporate | record |
| Certificate (incorporation / share / good-standing / insurance) | corporate | record |
| Regulatory licence / permit / filing | legal_regulatory | record |
| Information memorandum / presentation | diligence | report |
| Report (auditor / environmental / expert / legal DD) | diligence | report |
| Litigation / dispute document | legal_regulatory | report |
| DD questionnaire / Q&A export | diligence | record |
| Letter / email / memo | correspondence | correspondence |

### Coverage note

Collapsing must not tip into under-coverage. Standard due-diligence workstreams a
first draft dropped are added back above because they are common, distinct, and
would otherwise be silently misfiled: regulatory licences/permits, litigation and
disputes, insurance, and disclosure schedules. Some are form-heterogeneous and lean
on subtype rather than a new top-level type: a litigation "document" can be a
pleading (`report`), a settlement (`contract`), or correspondence, disambiguated by
subtype.

For the long tail (employee benefits and pension, IP registrations, compliance
policies, and so on) the rule is: map it to the nearest type plus a subtype, or to
`Other`, but decide it consciously. Every candidate class goes through a coverage
check so the classifier never silently forces an unmodelled document into `report`,
`certificate`, or `Other` by default.

Contract-form types are the exception to needing subtypes for routing: a customer
MSA and a supplier MSA run the identical clause pipeline, and which side we are on
is an entity-role question (derived from the parties), not a document-type one. So
those stay collapsed, with subtype optional.

### Special labels

These matter as much as the real types, because they keep the detector honest
instead of forcing a wrong label. They are distinct states, not one catch-all:

- `Unknown`: a readable document, but insufficient confidence to pick a taxonomy
  label. Abstain and send to review. This is the fail-safe, the same philosophy as
  the segmentation confidence gate.
- `Other`: confidently a valid document that falls outside the supported taxonomy.
- `Mixed / bundle`: one file that holds several *independent* documents (three
  unrelated contracts scanned into one PDF, a certificate followed by board
  minutes). The test is legal/logical independence. A 200-page acquisition agreement
  with its own disclosure schedules, exhibits, and signature-page certificates is
  NOT a bundle: those are parts of one instrument, and our clause segmenter already
  keeps them together as regions rather than splitting them off. A bundle result
  should carry page spans (for example pages 1-4 certificate, 5-12 board minutes,
  13-28 employment agreement) so the file can be split while each part keeps its
  provenance.

Document usability lives on the separate `quality_status` axis above, not here: an
`unreadable`, `blank`, `encrypted_or_restricted`, or `unsupported_format` file is a
usability state, not a wrong type guess, and must be scored separately.

### Where clause work applies

The stage-4/5 clause pipeline, boundary detection plus CUAD-style clause-type
classification, applies ONLY to `form: contract`. That is a claim about the CLAUSE
ontology, not about segmentation in general: every form gets some structural
segmentation (see the forms table), just not clause segmentation. Running the
clause segmenter or a CUAD classifier on a financial statement, a cap table, or
minutes is what produces garbage, because those have no clauses and no CUAD clause
types apply.

Constitutional documents (articles, bylaws) are a subtle case: they ARE
clause-structured, so boundary segmentation works on them, but their provisions
(share capital, pre-emption rights, director appointment, quorum, dividends) are
NOT CUAD clause types. A CUAD-trained classifier cannot be assumed to understand
them; that form needs its own constitutional-provision taxonomy for the
classification step. Segmentation transfers; classification does not.

"Extract key terms from every document", a common product claim, is really a
type-conditioned extractor: the type (and subtype) decide which terms even make
sense (purchase price on an acquisition agreement, EBITDA on a financial statement,
holdings on a cap table). So the type feeds key-term extraction too, not just
segmentation.

## Why the full trained detector is still deferred

The taxonomy above is buildable now with a heuristic or LLM first tier that needs
no training data. What stays deferred is the trained production model, for two
honest reasons.

1. There is no ready-made dataset. Language ID was a solved commodity we could wrap
   in one file. Clause classification was a moderate build because CUAD had already
   done the expert labelling at the right granularity. Document type has neither: no
   public dataset carries whole-document type labels in a taxonomy like ours. A
   trained detector means first building the labels, which is a data-engineering and
   ML program (weeks), not a wrap.
2. Its payoff is back-loaded. The biggest value of document type is at the deal-level
   aggregation stage (checklists, grouping, comparison, completeness), which we have
   not built yet. Building the trained detector now would be building the router
   before the roads it feeds.

## Revisit trigger (not a date)

Deferring by calendar time changes nothing. We revisit the trained model when a
consumer exists: when we build the deal-level aggregation stage that uses document
type as its organising key, or if a specific downstream need to branch on type
appears sooner. That milestone, not a number of days, is the trigger.

## What we deliberately will NOT do

Train a quick classifier only on the clean ready-made sets (Gretel plus CUAD, MAUD,
ContractNLI). It looks like a solution but is a workaround: single source per class
teaches formatting not meaning, it misses the real deal-room types, its scores are
optimistic, and it does not upgrade into the production model. It would be throwaway.

## The full production detector (for when we revisit)

A composite, silver-labelled corpus, then a normal train and evaluate loop. Phases:

1. Label schema: use the taxonomy above (type / category / form, plus Unknown,
   Other, Mixed-bundle). Keep document type separate from folder placement.
2. Licence and privacy clearance per source (commercial-training rights, rights in
   the underlying content, PII).
3. Batch every source document through our existing canonical parser, so training
   data matches production data.
4. Ingest the clean ready-made sets and map their labels to our taxonomy.
5. Build the silver-labelling machinery on public filings (SEC EDGAR, UK Companies
   House): crawl, split bundles, derive a label from several agreeing signals
   (metadata, title, headings, first-page text, rules, optional LLM vote), abstain on
   disagreement, map to our taxonomy. This is the largest lift.
6. Synthetic gap-fill for classes public sources lack (optional for a first version).
7. Deduplicate and split by organisation and template (and a held-out source or
   jurisdiction), so evaluation is not leaked.
8. Human-verified gold evaluation set (1,000 to 2,000 docs, two reviewers, a
   labelling guide, adjudication), not labelled with the silver rules.
9. Baselines (title and headings, full text, structured JSON), then the model with
   long-document handling, hierarchical domain-then-type, and abstention.
10. Evaluate with macro and weighted F1, per-class, top-3, calibration, unknown
    detection, and slice metrics (no filename, unseen org/template/source, scanned,
    long, bundles).

Rough size: 4 to 8 weeks for a solid first production version, dominated by the
silver-labelling machinery (5), the human gold set (8), and getting source diversity
and grouped splits right (5, 7). The model training itself (9, 10) is the small,
familiar part.

## Candidate datasets (from research)

Whole-document type labels, assessed for fit and licence:

- CUAD (CC BY 4.0): clean licence, doc types derivable from filenames (25 commercial
  types), but only 510 docs and no NDA/lease/employment. Good as a small validation
  seed, not a training corpus.
- Stanford Material Contracts Corpus (CC BY-NC-SA): best content fit (~1M contracts,
  8 categories), but NonCommercial, so unusable for a shipped model. Useful only as a
  taxonomy blueprint.
- SEC EDGAR Exhibit-10 (public domain): the practical training source via
  title-as-weak-label. Catch: noisy labels, US public-company skew (few leases and
  NDAs).
- UK Companies House (OGL metadata; verify document-content reuse): strong for
  accounts, incorporation, charges, resolutions; will not supply contracts.
- ContractNLI (CC BY 4.0): doc-level but all NDAs; clean NDA examples only.
- Gretel synthetic finance (Apache 2.0): synthetic, finance and messaging formats; a
  few financial classes and pipeline testing, not deal-room types.
- Ruled out (clause-level, not doc-type): LEDGAR, LexGLUE, MAUD, ACORD.
