from __future__ import annotations

from enum import Enum


class ClauseRole(str, Enum):
    """What kind of node a clause is, independent of its numbering family.

    Lets a consumer pick a granularity (only sections, or sections plus their
    sub-clauses) without parsing numbers. Derived from the marker: an ARTICLE header,
    a numbered SECTION (1.1, Section 6.02), or a parenthesised SUBCLAUSE ((a), (i)).
    """

    ARTICLE = "article"
    SECTION = "section"
    SUBCLAUSE = "subclause"
