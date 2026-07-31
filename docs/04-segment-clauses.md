# Segment clauses

Turn a parsed contract into its clause tree: the numbered provisions and their
sub-parts, each tied to an exact source span. This is the unit the classifier,
the extractors, and a human reviewer all work in.

## Scope

This stage applies to contract documents (SPA, merger, NDA, lease, employment,
loan, and similar agreements). Clauses are a contract feature. Financial
statements, presentations, spreadsheets, cap tables, and tender or RFP forms have
no clauses and route to different extraction. A coarse "is this a contract" gate
(eventually the document-type stage) decides what enters here.

## What a clause is

A self-contained provision: one numbered or headed chunk stating a single
obligation, right, definition, or condition. Granularity for us is the Section
level (for example "6.1 Termination"), with its sub-parts ((a), (i)) grouped
underneath as children. Too fine (every "(a)") is noise; too coarse (a whole
Article) is useless.

## The core problem

This is hierarchical boundary detection, not regex over text. A numbering
pattern signals a possible marker, never a guaranteed boundary. These all
contain clause-like patterns but none starts a clause:

- a cross-reference: "See Section 4.2."
- a date: "dated 1.1.2026"
- a percentage: "an interest rate of 1.5%"
- a table-of-contents line, a footnote number, a page number.

So the job is: find candidate boundaries, judge which are real using document-wide
context, and reconstruct a consistent hierarchy.

### Grounding (real merger agreement, docling output)

We checked a real SEC merger agreement, and it shaped the design:

- docling's block labels vary by document (this one used `section_header`,
  `text`, `page_footer`; the toy lease used `heading`, `list_item`). So block
  labels are a hint, not the truth.
- Section clauses appear as a `text` block starting with a number, for example
  "1.1. The Merger. Subject to the terms...", title and body in one block.
- Articles appear as `section_header` "ARTICLE I" then a title line.
- Real noise is present: a repeated "Table of Contents" running header, page
  footers (A-1, A-ii), a whole table-of-contents region, and WHEREAS recitals
  before Article I.

Lead with the numbering in the text; use docling's labels only as a secondary
signal, because the numbering is stable across documents and the labels are not.

## Production design

A deterministic legal-numbering parser plus a fine-tuned encoder boundary model,
followed by a stack-based constrained decoder. No generative model in the
extraction path, so every result is reproducible and tied to the source.

```text
ordered parsed blocks/runs (text, style, page, source offsets)
        -> candidate boundary anchors (exact offsets)
        -> document-level numbering grammar
        -> boundary + hierarchy classifier (deterministic first; learned later)
        -> constrained decoder (stack + numbering state, hard/soft rules)
        -> exact source-span clause tree
```

1. Candidate anchors. Propose a boundary at block starts, heading-style runs,
   indentation or style changes, inline markers inside a block, and transitions
   into recitals, schedules, annexes, exhibits, or signatures. Each keeps an
   exact source offset. Candidate generation must work at character offsets
   inside a block, because PDF extraction can put "7.1 Term... 7.2 Renewal..." in
   one block.

2. Numbering grammar (document level). Infer the active numbering families
   (decimal 1/2/3, hierarchical 1.1/1.2, parenthesized alpha (a)/(b), roman
   (i)/(ii)), keeping several candidate grammars until evidence resolves them.
   For each anchor compute: continues sequence, starts a child, returns to an
   ancestor, changes family, skips an ordinal, restarts after a schedule. This
   document-level state is one of the strongest signals.

3. Boundary and hierarchy decision. Combine numbering and layout features to
   decide, per candidate: is it a boundary (none / clause start / region start /
   non-body start), and its hierarchy move (root / child / sibling / return /
   reset). Deterministic rules first; a learned model later (see build plan).

4. Constrained decoder. Do not accept per-candidate decisions directly. Run a
   document-level decode (Viterbi or beam) holding the active clause stack and
   the numbering state, so boundaries are globally consistent.
   Hard constraints: no jump from level 1 to level 3 without a parent, no child
   without an active parent, no overlapping spans, monotonic offsets, no clause
   from a TOC or a running header, a schedule reset must not corrupt the main
   hierarchy. Soft scores: reward expected numbering continuation, matching
   indentation and typography at a level; penalize skipped ordinals, abrupt
   family changes, suspiciously short clauses, many boundaries inside prose.

5. Materialize exact spans. Never generate or rewrite text; select offsets. For
   each clause store the inclusive span (the clause plus all descendants) and the
   direct spans (its own text only). Direct text is an array of spans, not one
   range, because a parent sentence often resumes after a lettered list.

## Output contract

A tree of clause units. Each node carries: number, level, parent, marker span,
title span, inclusive span, direct spans (array), child ids, and confidence
(boundary and hierarchy). Text is always derived from the source by offset:
`inclusive_text = source[start:end]`. This is the same evidence-by-offset
invariant the parser already guarantees.

## Failure cases to handle explicitly

- Table of contents: detect by dot leaders, trailing page numbers, dense clause
  references, titles repeated later, position near the front. Return as
  references, not operative clauses.
- Inline clauses: multiple clauses in one extracted block; segment at inner
  offsets.
- Definitions: represent the definitions section as a clause with defined-term
  children; let consumers decide if terms count as clauses.
- Lists versus subclauses: tag clause / subclause / enumeration item / bullet so
  callers can pick a minimum level.
- Tables: one ordered container by default; numbers inside cells do not trigger
  boundaries.
- Schedules, annexes, exhibits: separate numbering namespace (main:7.2 versus
  schedule-1:7.2). Clause numbers are not globally unique.
- Footnotes: attach to the containing clause; keep footnote markers out of the
  hierarchy.
- OCR fragmentation: merged or split paragraphs, lost line breaks, "1 . 2",
  "(i)" versus "(l)" versus "(1)". The model must not depend on perfect
  paragraphs.

## Validation invariants (enforced every run)

- Every clause span is source-aligned (`source[start:end]` matches).
- No illegal overlap; every child is inside its parent; no cycles.
- Selected boundaries are monotonic.
- Every body block is accounted for; text conservation is 100% by construction,
  excluding explicitly classified non-body regions.

## Metrics

- Exact boundary F1 (offset must be correct, not fuzzy text overlap).
- Hierarchy edge F1 (predicted parent-child versus gold).
- Exact clause-span match (start and end both correct).
- Document-perfect rate (whole tree correct), the most revealing metric, since
  one missed boundary corrupts several clauses.
- False-merge and false-split rates, tracked separately (different downstream
  cost).
- Text-conservation rate (target 100% by construction).

## Build plan (staged, measurement-driven)

Phase 1 (now): the deterministic core. Candidate anchors, numbering grammar,
constrained decoder, exact-span materializer, and the validation invariants. No
training data needed. This is production-grade for the well-structured majority
of formal agreements. Wire the metrics in from the start.

Phase 2: measure on real documents (the merger and SPA sets, plus a small
labelled evaluation set). See where the core actually fails.

Phase 3 (only where Phase 2 shows measured failure): the learned boundary model.
A bidirectional encoder (for example ModernBERT, long context) with `[CAND]`
tokens classified in overlapping windows, fused with numbering and layout
features, separate heads for boundary, hierarchy, and role. Add it targeted at
the failing slice (scanned, OCR-fragmented, lightly numbered, non-standard),
not across the board.

Throughout: confidence and fallback. Low-confidence or out-of-scope documents
are flagged for review or a coarser fallback, never silently mis-segmented. That
fail-safe behaviour, plus the measurement, is what makes it production-ready on a
defined population rather than a claim about all documents.

## Data strategy (for Phase 3)

- Annotate candidate boundaries and hierarchy relations, not copied clause
  strings.
- Weak supervision from native DOCX numbering metadata, PDF bookmarks, heading
  styles, consistent explicit numbering, and TOC-to-body title matching. Caveat:
  our SEC-filing PDFs usually have no outline and are not DOCX, so for this
  corpus weak labels lean on numbering sequences, heading styles, and TOC
  matching, which are noisier.
- Hard negatives on purpose: cross-references, dates, percentages, currency,
  numbered factual lists, page numbers, table-row numbers, footnote markers, TOC
  entries, signature fields, version numbers.
- Split train and evaluation by near-duplicate or template family, not random
  document, or twenty agreements from one template leak across splits.
- Active learning: prioritise documents where the model is uncertain, the
  decoder overrides the model, multiple grammars stay plausible, or rules and
  model disagree.

## What we deliberately will not do

- Ship regex on numbering plus hardcoded string stripping (for example matching
  the literal "Table of Contents") as the solution. That is a demo hack that
  breaks on the next document.
- Put a generative model in the extraction path. An LLM may assist weak
  labelling or annotation, but production boundaries come from candidate
  classification plus deterministic constrained decoding, so results are
  reproducible and source-tied.
- Reach for a multimodal model (for example LayoutLMv3) by default. It is
  justified only when segmentation genuinely needs raw page-image features; we
  already have text, reading order, and geometry.

## Status

Phase 1 (deterministic core) is implemented in `package/.../segmentation/`:
candidate anchors, numbering grammar, stack decoder, span materialisation
(inclusive and direct), validation invariants, and a `ClauseSegmenter` that
satisfies the Segmenter interface and emits `ClauseUnit`s (hierarchy in `meta`).
The demo runs parse, language, and segment end to end. On the first 20 pages of a
real merger agreement it recovers the Article/section/sub-part tree with clean
spans and zero validation issues.

Body-start is family-agnostic (v2): the first content-bearing numbered block,
backing up one step to an introducing article. It keys on content and structure,
not on specific numbering tokens, so it handles "1.1.", "Section 1.1", and
"Clause 5" alike. An article always resets to the top level, so a stray
table-of-contents article cannot swallow the body. Robust multi-signal TOC
detection (page-number patterns, many markers per block, titles repeated later)
is still a follow-up.

Phase 2 (measurement) run via `make seg-measure` over the 20-document merger and
SPA corpus: 20/20 parse, 0 validation issues, average ~364 clauses. The
family-agnostic body-start fixed three previously under-segmented documents at
once (iRobot 23->317, BurgerFi 99->433, PS Business Parks 116->522), a general
fix rather than a per-document patch.

Correctness (not just coverage) via `make seg-score`: gold is derived from each
document's own table of contents (independent of the segmenter, which parses the
body), scored at the section level. Moneygram and iRobot both reach recall 1.00,
precision 1.00, F1 1.00. Getting there found and fixed a real bug the scorer
surfaced: a sub-part "(i)" (alpha i = 9) was matching "ARTICLE VIII" (8) as a
sibling, because sibling-matching ignored the numbering family. The fix, siblings
must be the same numbering kind, is general. Notably the measurement redirected
us away from building a TOC detector, which would not have moved the number.

Honest limits: two documents, both mergers, one numbering style each, section
level only (sub-parts not yet scored), SPAs not yet labelled. Gold and scorer
live in `eval/clause_segmentation/` (labels mirror `demo/documents/` subfolders).

Still tracked: robust multi-signal TOC detection (removes iRobot's spurious
leading article, which the section-level metric does not penalise); a deeper
stack-robustness pass so orphan sub-parts are re-nested rather than skipped;
extending gold to SPAs. Phase 3 (a learned boundary model) is justified only if
the gold numbers show a real gap the rules cannot close, and so far they do not.
