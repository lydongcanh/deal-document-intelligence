# Clause segmentation: dev/acceptance labels

This is a small development and acceptance set, not a golden benchmark. Be honest
about what it is and is not.

What it is: hand-labelled clause structure for a few documents, written from the
source PDF, used to get a first correctness signal and to catch regressions when
we change the segmentation rules.

What it is NOT: representative. Every document here is a US SEC public-company
filing (merger or SPA), born-digital, English. Good scores prove we do well on
this slice, not that we are production-ready on leases, employment agreements,
NDAs, scanned or messy documents, non-US drafting, or other languages. A true
golden dataset (diverse, larger, multiple reviewers, held out from tuning) is a
later program.

## Label format

One JSON file per document:

```json
{
  "source": "<path under demo/documents/>",
  "page_range": [1, 20],
  "note": "scope and provenance",
  "clauses": [
    {"number": "ARTICLE I", "depth": 0, "heading": "THE MERGER"},
    {"number": "1.1", "depth": 1, "heading": "The Merger"}
  ]
}
```

- `number` must match the segmenter's number (marker without a trailing dot).
- `depth` 0 = article, 1 = section. The scorer currently checks the section
  level (depth 0-1), where numbers are unique. Sub-parts ((a), (i)) are deferred.
- Label from the source, never from the segmenter's output.
- Labels may be partial (a page range, or only some articles); the scorer reports
  recall on what is labelled and lists unlabelled predictions separately.

## Scoring

    make seg-score      # or: python eval/clause_segmentation/score.py

Reports, per document: recall on labelled sections, wrong-depth matches, missed
sections, and predicted sections that are not labelled.
