# Detect document type (deferred)

Status: the contract and interface exist (`DocumentTypeDetector`,
`DetectedDocumentType`), but no detector is implemented yet. This document
records why, and the strategy to revisit.

## What the stage would do

Classify a whole document as one of a fixed set of deal document types (NDA,
lease, employment, share purchase, and so on), with a confidence, an explicit
unknown path, and a review flag. It routes downstream choices (which taxonomy,
which entity roles) and, more importantly, organises documents at the deal
level.

## Why we deferred it

Two honest reasons.

1. There is no ready-made dataset. Language ID was a solved commodity we could
   wrap in one file. Clause classification was a moderate build because CUAD had
   already done the expert labelling at the right granularity. Document type has
   neither: no public dataset carries whole-document type labels in a taxonomy
   like ours. So a real detector means first building the labels, which is a
   data-engineering and ML program (weeks), not a wrap.
2. Its payoff is back-loaded. The biggest value of document type is at the
   deal-level aggregation stage (checklists, grouping, comparison, completeness),
   which we have not built yet. Building a production detector now would be
   building the router before the roads it feeds.

## Revisit trigger (not a date)

Deferring by calendar time changes nothing. We revisit when a consumer exists:
when we build the deal-level aggregation stage that uses document type as its
organising key, or if a specific downstream need to branch on type appears
sooner. That milestone, not a number of days, is the trigger.

## What we deliberately will NOT do

Train a quick classifier only on the clean ready-made sets (Gretel plus CUAD,
MAUD, ContractNLI). It looks like a solution but is a workaround: single source
per class teaches formatting not meaning, it misses the real deal-room types,
its scores are optimistic, and it does not upgrade into the production model. It
would be throwaway.

## The best solution, for when we revisit

A composite, silver-labelled corpus, then a normal train and evaluate loop.
Phases:

1. Taxonomy and label schema: 12 to 16 types, definitions, confusable pairs, add
   Unknown and Mixed-bundle. Separate document type from folder placement.
2. Licence and privacy clearance per source (commercial-training rights, rights
   in the underlying content, PII).
3. Batch every source document through our existing canonical parser, so
   training data matches production data.
4. Ingest the clean ready-made sets and map their labels to our taxonomy.
5. Build the silver-labelling machinery on public filings (SEC EDGAR, UK
   Companies House): crawl, split bundles, derive a label from several agreeing
   signals (metadata, title, headings, first-page text, rules, optional LLM
   vote), abstain on disagreement, map to our taxonomy. This is the largest lift.
6. Synthetic gap-fill for classes public sources lack (optional for a first
   version).
7. Deduplicate and split by organisation and template (and a held-out source or
   jurisdiction), so evaluation is not leaked.
8. Human-verified gold evaluation set (1,000 to 2,000 docs, two reviewers, a
   labelling guide, adjudication), not labelled with the silver rules.
9. Baselines (title and headings, full text, structured JSON), then the model
   with long-document handling, hierarchical domain-then-type, and abstention.
10. Evaluate with macro and weighted F1, per-class, top-3, calibration, unknown
    detection, and slice metrics (no filename, unseen org/template/source,
    scanned, long, bundles).

Rough size: 4 to 8 weeks for a solid first production version, dominated by the
silver-labelling machinery (5), the human gold set (8), and getting source
diversity and grouped splits right (5, 7). The model training itself (9, 10) is
the small, familiar part.

## Candidate datasets (from research)

Whole-document type labels, assessed for fit and licence:

- CUAD (CC BY 4.0): clean licence, doc types derivable from filenames (25
  commercial types), but only 510 docs and no NDA/lease/employment. Good as a
  small validation seed, not a training corpus.
- Stanford Material Contracts Corpus (CC BY-NC-SA): best content fit (~1M
  contracts, 8 categories), but NonCommercial, so unusable for a shipped model.
  Useful only as a taxonomy blueprint.
- SEC EDGAR Exhibit-10 (public domain): the practical training source via
  title-as-weak-label. Catch: noisy labels, US public-company skew (few leases
  and NDAs).
- UK Companies House (OGL metadata; verify document-content reuse): strong for
  accounts, incorporation, charges, resolutions; will not supply contracts.
- ContractNLI (CC BY 4.0): doc-level but all NDAs; clean NDA examples only.
- Gretel synthetic finance (Apache 2.0): synthetic, finance and messaging
  formats; a few financial classes and pipeline testing, not deal-room types.
- Ruled out (clause-level, not doc-type): LEDGAR, LexGLUE, MAUD, ACORD.

## Taxonomy note

The current `DocumentType` enum is contract-focused (NDA, share_purchase,
merger, employment, lease, and so on). A production version likely broadens to
data-room document types (statutory accounts, board resolution, insurance
policy, invoice), fitted to what the data can actually support.
