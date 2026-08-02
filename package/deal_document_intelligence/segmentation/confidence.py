"""Assess how much to trust a clause segmentation, for the review gate.

The signals are deliberately general and gold-free, so the score means the same
thing on documents we have never seen:

- uniqueness: section numbers should be unique; repeats mean the tree conflated
  distinct clauses (a restart-per-article scheme reuses "1.01" under every
  article, which shows up here strongly).
- article order: top-level nodes should run in increasing order; an article that
  arrives after a later one signals a broken or scrambled reading order.
- validity: the invariants in `validate_tree`. Any violation means the tree is
  structurally unsound, so it hard-caps the score.

The signals multiply (any one weak signal pulls the score down) and a validation
failure caps it, because the gate should fail safe: when unsure, ask for review.

Coverage (did we drop real sections?) is deliberately NOT a signal here. The
obvious proxy, the fraction of block-start decimal markers left unplaced, is
dominated by in-clause numbered lists ("1.", "2.", ...) and cross-references that
the decoder rightly ignores, so it false-flags clean documents (measured). A
reliable coverage signal needs the expected sequence and is a tracked follow-up;
until then the gate is conservative and does not claim to catch every subtle miss.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import ParsedDocument, SegmentationConfidence
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.validation import validate_tree

# Route to review below this. A policy knob, not a learned value: the signals
# multiply, so 0.85 trips when one signal falls to ~0.85 (e.g. one section number
# in seven is a duplicate) while everything else is clean. On the graded set it
# flags the genuinely-degraded documents and no exact one; tune it to trade review
# volume against miss rate.
REVIEW_THRESHOLD = 0.85
# A tree that fails a structural invariant is untrustworthy regardless of the other
# signals, so cap it far below the threshold (0.2, review guaranteed) rather than
# zero, which would erase the finer signal ordering among broken trees.
_INVALID_CAP = 0.2


def _article_order(nodes: list[ClauseNode]) -> float:
    """Fraction of adjacent articles that are in increasing order. Only articles
    are compared: regions legitimately restart numbering (a Schedule A after
    Article XI is not disorder), and a stray top-level section is a different
    concern. A scrambled reading order (Article VIII emitted after IX) shows here."""
    arts = [n for n in nodes if n.depth == 0 and n.marker_family == "article" and n.path]
    pairs = list(zip(arts, arts[1:]))
    if not pairs:
        return 1.0
    return sum(1 for a, b in pairs if b.path > a.path) / len(pairs)


def _region_member_ids(nodes: list[ClauseNode]) -> set[str]:
    """Ids of region nodes and everything under them. A schedule is a separate
    numbering namespace, so its sections must not be compared against the main
    body (a schedule's 1.1 is not a duplicate of the body's 1.1)."""
    by_id = {n.id: n for n in nodes}
    members: set[str] = set()
    for n in nodes:
        cur, seen = n, set()
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            if cur.marker_family == "region":
                members.add(n.id)
                break
            cur = by_id.get(cur.parent_id)
    return members


def _uniqueness(nodes: list[ClauseNode]) -> float:
    """Fraction of main-body section-level nodes whose (depth, number) is unique."""
    region = _region_member_ids(nodes)
    keys = [(n.depth, n.path) for n in nodes
            if n.depth <= 1 and n.path and n.id not in region]
    if not keys:
        return 1.0
    return len(set(keys)) / len(keys)


def assess_confidence(
    document: ParsedDocument, nodes: list[ClauseNode]
) -> SegmentationConfidence:
    """Score a materialised clause tree (nodes with `char_end`) for trust.

    `nodes` must be the materialised tree (from `clause_tree`), because the
    validity signal checks span invariants.
    """
    order = _article_order(nodes)
    unique = _uniqueness(nodes)
    issues = validate_tree(nodes, document)

    score = order * unique
    if issues:
        score *= _INVALID_CAP

    reasons: list[str] = []
    if order < 1.0:
        reasons.append("articles or top-level sections appear out of order")
    if unique < 1.0:
        reasons.append("duplicate section numbers in the tree")
    if issues:
        reasons.append(f"failed {len(issues)} structural invariant(s)")

    score = round(score, 3)
    return SegmentationConfidence(
        score=score,
        needs_review=score < REVIEW_THRESHOLD,
        signals={
            "article_order": round(order, 3),
            "uniqueness": round(unique, 3),
            "valid": 0.0 if issues else 1.0,
        },
        reasons=reasons,
    )
