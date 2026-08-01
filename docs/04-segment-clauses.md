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

Phase 1 (in progress): the deterministic core. Candidate anchors, numbering
grammar, a greedy stack decoder (not yet the scored constrained decoder described
above), exact-span materializer, and the validation invariants. No training data
needed. It handles the well-structured majority of formal agreements but is not
production-grade yet: see the known defects in Status. Wire the metrics in from
the start.

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

## Status: Phase 1 IN PROGRESS (not production-grade)

Built in `package/.../segmentation/`: candidate anchors, numbering grammar, a
greedy stack decoder, span materialisation (inclusive and direct), validation
invariants, and a `ClauseSegmenter` emitting `SegmentedClause`s with the full hierarchy
as typed fields (depth, parent, path, role), each clause's own `direct_spans`, and
page-level evidence. The demo runs parse, language, and segment end to end.

Evaluation: gold is section-level inventories auto-derived from each document's
own table of contents (`build_gold_from_toc.py`), independent of the body the
segmenter parses. 15 of 20 documents have gold (7 mergers, 6 SPAs); 5 use TOC
layouts the builder cannot parse and are excluded. `make seg-score` scores at the
section level, counting a clause correct only when number AND depth match,
aggregates, saves `artifacts/eval/clause_segmentation/score.json`, and fails below
a mean-F1 threshold. `make seg-measure` reports internal consistency and coverage
only, not correctness.

Current score: mean F1 0.93 (recall 0.93, precision 0.98) over the 15. Eight
documents are exact, four at 0.98-0.99, and two remain low for the specific,
understood reasons in Known defects below (Staffing 0.89, FRESH 0.19).

Fail-safe review gate: `assess_confidence` scores each document's tree from
gold-free structural signals (article order, section-number uniqueness, and the
validation invariants) and returns a `SegmentationConfidence` with a
`needs_review` flag, so an out-of-distribution document is routed to review or a
coarser fallback instead of being silently mis-segmented. On the graded set the
gate flags FRESH (0.31, the restart-per-article numbering) and PS (0.67, real
duplicate numbers) and clears every exact document, with no clean document
false-flagged. It is deliberately conservative: coverage (were real sections
dropped?) is not yet a signal, because the obvious proxy is dominated by in-clause
numbered lists and false-flags clean documents (measured), so a subtle miss like
Staffing (0.88) can still pass. A reliable coverage signal is a tracked follow-up.

Known defects (some found by external review, verified, and being worked):
- Greedy decoder, not the scored constrained decoder this doc describes. It has
  no proper skip tolerance beyond one dropped ordinal, and it drops rather than
  re-nests markers it cannot place.
- Scrambled reading order. The parser can emit an article header after the
  sections it introduces (Staffing: "ARTICLE VIII" arrives after "ARTICLE IX" and
  after 9.1). The header then cannot parent those sections, because its own text
  lives at a later source offset and an offset-enclosing span must start before
  its children. This belongs to the parser's reading order, not the decoder;
  reordering candidates here was tried and correctly rejected (it breaks the
  evidence-by-offset invariant).
- Article-relative section numbering. Some bodies restart section numbers per
  article ("Section 1.01" under every article) while the TOC lists them
  fully-qualified ("2.01"). The segmenter faithfully reads "1.01", so it neither
  nests nor matches gold (FRESH). The fix is a numbering namespace that qualifies
  a section by its enclosing article; it is a distinct feature, not a decoder bug.
- Inline sections are dropped. When the parser merges an article header with its
  first section into one block, that section is inline and not recovered (a
  general-inline attempt regressed the well-structured docs and was reverted).
- Regions (schedules, annexes, exhibits) are recognised as markers but have no
  numbering-grammar branch, so they get an empty path and are discarded; separate
  schedule/exhibit namespaces are not implemented.
- Per-node confidence and region namespace are still not surfaced on `SegmentedClause`
  (the rest of the output contract is now in place: typed hierarchy, direct spans,
  role, and page-level evidence). Per-node boundary/hierarchy confidence needs a
  scoring decoder or the learned model, so it stays deferred with those.
- Markers are English-only (not multilingual yet); the parser does not populate
  block geometry.

Fixed so far: sibling matching respects numbering kind and tolerates one dropped
ordinal; `starts_sequence` no longer over-nests decimal sections; orphan
parenthesised sub-parts are not promoted to top level. An article now adopts a
following section whose leading ordinal matches even when the .01 opener was
dropped or reordered, so a whole article's sections are no longer lost.
Body-start keys on the content run after a marker (text until the next section)
rather than a single block's length, so a section whose heading was split into a
short block is still recognised; it then backs up over the opening lead-in (short
article and section headers, plus the sub-parts between them), so a Definitions
article opening with short headings is no longer skipped. The
scorer evaluates only section-level markers (parenthesised sub-parts are scored at
their own level, not counted as false sections). The output contract now surfaces
the full clause tree: typed depth, parent, path, and role, each clause's own
direct spans, and page-level evidence (a clause spanning a page break records each
page), so consumers no longer dig hierarchy out of an untyped `meta`.

Phase 3 (a learned boundary model) is not started and is not justified until the
deterministic core and the evaluation are solid.
