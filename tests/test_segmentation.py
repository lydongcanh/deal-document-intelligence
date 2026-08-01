"""Segmentation step 1: candidate boundary anchors.

Fast, no docling. Builds a tiny ParsedDocument by hand (with correct offsets)
and checks that generate_candidates finds the right markers, flags block-start
versus inline, and keeps every offset exactly source-aligned.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import Block, BlockType, ParsedDocument
from deal_document_intelligence.contracts import ClauseRole, SegmentedClause
from deal_document_intelligence.interfaces import ClauseSegmenter
from deal_document_intelligence.segmentation import (
    Candidate,
    DeterministicClauseSegmenter,
    assess_confidence,
    clause_tree,
    decode,
    generate_candidates,
    is_child_start,
    is_sibling_successor,
    parse_marker,
    validate_tree,
)

SEP = "\n\n"


def _doc(block_texts: list[str]) -> ParsedDocument:
    """Join blocks like the parser does, with correct char offsets."""
    blocks: list[Block] = []
    cursor = 0
    for i, text in enumerate(block_texts):
        start = cursor
        end = start + len(text)
        blocks.append(Block(id=f"b{i}", type=BlockType.PARAGRAPH, text=text,
                            page=1, char_start=start, char_end=end))
        cursor = end + len(SEP)
    return ParsedDocument(doc_id="d", text=SEP.join(block_texts), blocks=blocks)


def test_candidates_families_and_block_start() -> None:
    doc = _doc([
        "ARTICLE I",
        "THE MERGER",
        "1.1. The Merger. The parties agree; see Section 4.2 for details.",
        "(a) first sub-part",
        "(b) second sub-part",
    ])
    cands = generate_candidates(doc)
    by_marker = {c.marker_text: c for c in cands}

    # Leading markers are found and flagged as block starts.
    assert by_marker["ARTICLE I"].marker_family == "article"
    assert by_marker["ARTICLE I"].at_block_start is True
    assert by_marker["1.1."].marker_family == "hier-decimal"
    assert by_marker["1.1."].at_block_start is True
    assert by_marker["(a)"].marker_family == "paren-lower"
    assert by_marker["(b)"].at_block_start is True

    # The inline cross-reference is surfaced but NOT a block start.
    assert by_marker["Section 4.2"].marker_family == "section"
    assert by_marker["Section 4.2"].at_block_start is False


def test_every_candidate_is_source_aligned() -> None:
    doc = _doc([
        "1.1. Definitions. In this Agreement, '2.5%' is not a clause and 1.1.2026 is a date.",
        "2.1. Term. Five years.",
    ])
    cands = generate_candidates(doc)
    assert cands  # something was found
    for c in cands:
        assert isinstance(c, Candidate)
        end = c.source_offset + len(c.marker_text)
        assert doc.text[c.source_offset:end] == c.marker_text


def test_parse_marker_into_paths() -> None:
    assert parse_marker("article", "ARTICLE III").path == (3,)
    assert parse_marker("section", "Section 7.2").path == (7, 2)
    assert parse_marker("hier-decimal", "1.1.").path == (1, 1)
    assert parse_marker("decimal", "2.").path == (2,)
    assert parse_marker("paren-num", "(3)").path == (3,)
    assert parse_marker("paren-upper", "(B)").path == (2,)
    # "(a)" is unambiguously alpha; "(i)" keeps both readings.
    assert parse_marker("paren-lower", "(a)").path == (1,)
    i = parse_marker("paren-lower", "(i)")
    assert i.path == (9,) and i.alt_path == (1,)      # alpha i=9, roman one
    assert parse_marker("paren-lower", "(ii)").path == (2,)  # multi-letter -> roman


def test_sibling_and_child_relations() -> None:
    pm = parse_marker
    # siblings
    assert is_sibling_successor(pm("hier-decimal", "1.1"), pm("hier-decimal", "1.2"))
    assert not is_sibling_successor(pm("hier-decimal", "1.1"), pm("hier-decimal", "1.3"))
    assert is_sibling_successor(pm("paren-lower", "(a)"), pm("paren-lower", "(b)"))
    assert is_sibling_successor(pm("paren-lower", "(i)"), pm("paren-lower", "(ii)"))
    assert is_sibling_successor(pm("article", "ARTICLE I"), pm("article", "ARTICLE II"))
    # children (within family; decimal paths embed the parent number)
    assert is_child_start(pm("decimal", "2."), pm("hier-decimal", "2.1"))
    assert is_child_start(pm("hier-decimal", "1.1"), pm("hier-decimal", "1.1.1"))
    assert not is_child_start(pm("hier-decimal", "1.1"), pm("hier-decimal", "1.2"))


def test_decode_builds_hierarchy_and_skips_toc() -> None:
    body = "x" * 400  # real clause bodies are long; TOC entries are short titles
    doc = _doc([
        "ARTICLE V",    # a table-of-contents entry: an article title, no body
        "ARTICLE IX",   # another TOC entry
        "ARTICLE I",
        f"1.1. Term. {body}",
        f"1.2. Rent. {body}",
        f"(a) first sub-part {body}",
        f"(b) second sub-part {body}",
        f"1.3. End. {body}",     # return to ancestor: sibling of 1.2, not of (b)
        "ARTICLE II",
        f"2.1. Foo. {body}",
    ])
    nodes = decode(doc)
    by_marker = {n.marker_text: n for n in nodes}

    # TOC entries (ARTICLE V, ARTICLE IX) are skipped; body starts at ARTICLE I.
    assert nodes[0].marker_text == "ARTICLE I"
    assert "ARTICLE V" not in by_marker and "ARTICLE IX" not in by_marker

    # depths
    assert by_marker["ARTICLE I"].depth == 0
    assert by_marker["1.1."].depth == 1
    assert by_marker["(a)"].depth == 2
    assert by_marker["(b)"].depth == 2

    # parents, including cross-family nesting and return-to-ancestor
    assert by_marker["1.1."].parent_id == by_marker["ARTICLE I"].id
    assert by_marker["(a)"].parent_id == by_marker["1.2."].id
    assert by_marker["1.3."].depth == 1
    assert by_marker["1.3."].parent_id == by_marker["ARTICLE I"].id
    assert by_marker["2.1."].parent_id == by_marker["ARTICLE II"].id


def test_missing_ordinal_does_not_reject_the_rest() -> None:
    # A dropped 1.2 must not cause 1.3 and 1.4 to be rejected (regression).
    body = "x" * 400
    doc = _doc(["ARTICLE I", f"1.1. A {body}", f"1.3. C {body}", f"1.4. D {body}"])
    depths = {n.marker_text: n.depth for n in decode(doc)}
    assert depths.get("1.3.") == 1 and depths.get("1.4.") == 1


def test_section_ending_in_one_is_not_over_nested() -> None:
    # "2.1"/"3.1" must not become runaway children of "1.1" just for ending in 1.
    body = "x" * 400
    doc = _doc(["ARTICLE I", f"1.1. A {body}", f"2.1. B {body}", f"3.1. C {body}"])
    assert all(n.depth <= 1 for n in decode(doc))  # no 0,1,2,3 runaway


def test_article_adopts_section_when_opener_is_missing() -> None:
    # An article's real first section (6.01) can be dropped or reordered by the
    # parser. The article must still adopt 6.02 as its child, or the whole
    # article's sections collapse (regression seen on a real SPA).
    body = "x" * 400
    doc = _doc([
        "ARTICLE V", f"5.1 A {body}",
        "ARTICLE VI", f"6.02 B {body}", f"6.03 C {body}",
    ])
    by = {n.marker_text: n for n in decode(doc)}
    assert by["ARTICLE VI"].depth == 0
    assert by["6.02"].depth == 1 and by["6.02"].parent_id == by["ARTICLE VI"].id
    assert by["6.03"].depth == 1


def test_body_start_backs_up_over_short_headers_and_subparts() -> None:
    # The first substantial block is 1.02; ARTICLE I and 1.01 are short heading
    # blocks and 1.01's (a) sub-part sits between them. Body-start must back up
    # past the sub-part to open at ARTICLE I, not truncate to 1.02.
    body = "x" * 400
    doc = _doc([
        "ARTICLE I",            # short header
        "1.01 The Merger.",     # short opener
        f"(a) sub-part {body}",  # 1.01's child, between 1.01 and 1.02
        f"1.02 Effect. {body}",  # first block >= 100 chars
    ])
    nodes = decode(doc)
    by = {n.marker_text: n for n in nodes}
    assert nodes[0].marker_text == "ARTICLE I"
    assert by["ARTICLE I"].depth == 0
    assert by["1.01"].depth == 1 and by["1.02"].depth == 1
    assert by["(a)"].depth == 2


def test_body_start_uses_content_run_not_block_length() -> None:
    # The body's first section heading ("1.1 Term.") is a short block; its body is
    # a separate long block. A block-length test would skip the short heading; the
    # content run (text until the next section) is long, so body-start keeps it and
    # backs up to its article. The two leading short TOC articles are skipped.
    body = "x" * 400
    doc = _doc([
        "ARTICLE I",   # table-of-contents entries: short, nothing between them
        "ARTICLE II",
        "ARTICLE I",   # the body article (short header)
        "1.1 Term.",   # short section heading ...
        body,          # ... whose body is a separate long block
        "1.2 Rent.",
        body,
    ])
    nodes = decode(doc)
    by = {n.marker_text: n for n in nodes}
    assert nodes[0].marker_text == "ARTICLE I"
    assert by["1.1"].depth == 1 and by["1.2"].depth == 1
    assert len(nodes) == 3  # body ARTICLE I, 1.1, 1.2; the TOC articles are skipped


def test_spans_materialise_and_validate() -> None:
    body = "x" * 400
    doc = _doc([
        "ARTICLE I",
        f"1.1. Term. {body}",
        f"1.2. Rent. {body}",
        f"(a) first sub-part {body}",
        f"(b) second sub-part {body}",
        f"1.3. End. {body}",
        "ARTICLE II",
        f"2.1. Foo. {body}",
    ])
    nodes = clause_tree(doc)
    by_marker = {n.marker_text: n for n in nodes}

    # inclusive span ends where the next non-descendant begins
    assert by_marker["1.1."].char_end == by_marker["1.2."].source_offset
    assert by_marker["(a)"].char_end == by_marker["(b)"].source_offset
    # 1.2's inclusive span covers its (a)/(b) children, ending at 1.3
    assert by_marker["1.2."].char_end == by_marker["1.3."].source_offset

    # direct text of 1.2 is its own lead-in only: excludes the (a)/(b) region
    ds = by_marker["1.2."].direct_spans
    direct = "".join(doc.text[s:e] for s, e in ds)
    assert direct.startswith("1.2. Rent.")
    assert "first sub-part" not in direct and "second sub-part" not in direct

    # every inclusive span is in bounds and non-empty, and the tree is sound
    for n in nodes:
        assert n.char_end is not None
        assert 0 <= n.source_offset < n.char_end <= len(doc.text)
    assert validate_tree(nodes, doc) == []


def test_confidence_trusts_a_clean_tree() -> None:
    body = "x" * 400
    doc = _doc([
        "ARTICLE I", f"1.1 Term. {body}", f"1.2 Rent. {body}",
        "ARTICLE II", f"2.1 Foo. {body}", f"2.2 Bar. {body}",
    ])
    conf = assess_confidence(doc, clause_tree(doc))
    assert conf.score > 0.95 and conf.needs_review is False
    assert conf.reasons == []


def test_confidence_flags_out_of_order_articles() -> None:
    # Articles emitted out of order (a scrambled reading order) must be flagged,
    # not silently trusted.
    body = "x" * 400
    doc = _doc([f"ARTICLE II {body}", f"ARTICLE I {body}"])
    conf = assess_confidence(doc, clause_tree(doc))
    assert conf.needs_review is True
    assert conf.signals["article_order"] < 1.0
    assert any("out of order" in r for r in conf.reasons)


def test_clause_segmenter_satisfies_interface_and_contract() -> None:
    body = "x" * 400
    doc = _doc([
        "ARTICLE I",
        f"1.1. Term. {body}",
        f"1.2. Rent. {body}",
        f"(a) sub-part {body}",
    ])
    seg = DeterministicClauseSegmenter()
    assert isinstance(seg, ClauseSegmenter)  # structural conformance to the Protocol

    units = seg.segment(doc)
    assert units and all(isinstance(u, SegmentedClause) for u in units)
    for u in units:
        # each unit's inclusive text slices back to source exactly
        assert doc.text[u.char_start:u.char_end] == u.text
        # every evidence span is source-aligned by offset
        assert u.evidence and all(doc.text[e.char_start:e.char_end] == e.text for e in u.evidence)
        # direct spans are the unit's own text, and reconstruct it
        assert u.direct_spans and all(u.char_start <= s < e <= u.char_end for s, e in u.direct_spans)
        # SegmentedClause is structural only: no classification fields to guess about
        assert not hasattr(u, "clause_type")

    by_num = {u.number: u for u in units}
    assert by_num["1.1"].heading == "Term"
    # hierarchy is first-class now, not buried in meta
    assert by_num["ARTICLE I"].role is ClauseRole.ARTICLE and by_num["ARTICLE I"].depth == 0
    assert by_num["1.1"].role is ClauseRole.SECTION and by_num["1.1"].path == [1, 1]
    assert by_num["(a)"].role is ClauseRole.SUBCLAUSE and by_num["(a)"].depth == 2
    assert by_num["(a)"].parent_id == by_num["1.2"].id
