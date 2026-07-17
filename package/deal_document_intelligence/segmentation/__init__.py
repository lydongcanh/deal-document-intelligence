"""Stage 4 — Clause segmentation.  [BUILD]

Split the document into clause units using contract-aware numbering / heading /
cross-reference logic. Generic sentence splitters don't understand clause
hierarchy, so this is custom (rules first, model later).
"""
