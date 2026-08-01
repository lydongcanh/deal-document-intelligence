# Clause segmentation: dev/acceptance labels

This is a small development and acceptance set, not a golden benchmark. Be honest
about what it is and is not.

What it is: section-level inventories (articles and N.M sections) derived
automatically from each document's own table of contents by
`build_gold_from_toc.py`. The TOC is the drafter's authoritative list and is
independent of the segmenter (which parses the body, not the TOC), so it is a
usable, non-circular reference for the section level. It is used to get a
correctness signal and catch regressions.

What it is NOT: a full segmentation gold, and not representative. It is
section-level only (no sub-parts, no schedules/exhibits, no body offsets or
parent-child edges below the section level), it is auto-derived rather than
human-verified, and every document is a US SEC public-company filing (merger or
SPA), born-digital, English. Good scores prove we do well on that slice at the
section level, not that we are production-ready. Not every TOC parses (5 of 20
documents use layouts the builder does not handle and are excluded). A true
golden dataset (human-verified, diverse, with sub-part and region labels) is a
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
