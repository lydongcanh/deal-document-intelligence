"""Peek at CUAD to see what document-type signal it offers for the REAL eval.

CUAD is our cleanest openly-licensed real source (CC BY 4.0). Its per-contract type
is not an explicit field; it is encoded in the contract's title/name. This script
streams a few rows (so it does not download the whole set) and prints the fields and
sample titles, so we can decide how to map CUAD -> our taxonomy for the real eval.

WARP must be OFF for the HuggingFace fetch.
Run:  poetry run python training/document_type/explore_cuad_types.py
"""

from __future__ import annotations

from collections import Counter

from datasets import load_dataset

CUAD_ID = "theatticusproject/cuad-qa"


def main() -> None:
    ds = load_dataset(CUAD_ID, split="test", streaming=True, trust_remote_code=True)
    keys: list[str] = []
    titles: list[str] = []
    for i, ex in enumerate(ds):
        if i == 0:
            keys = list(ex.keys())
        if i >= 60:
            break
        titles.append(str(ex.get("title", "")))

    print("fields:", keys)
    uniq = sorted(set(titles))
    print(f"\n{len(uniq)} unique contract titles in the first 60 rows:")
    for t in uniq[:25]:
        print("  ", t[:100])

    # crude keyword scan: do titles carry a recognisable type?
    kw = [
        "nda",
        "non-disclosure",
        "confidential",
        "license",
        "licence",
        "supply",
        "services",
        "distribution",
        "reseller",
        "employment",
        "lease",
        "merger",
        "purchase",
        "shareholder",
        "joint venture",
        "franchise",
        "agency",
    ]

    hits = Counter()
    for t in uniq:
        low = t.lower()
        for k in kw:
            if k in low:
                hits[k] += 1

    print("\ntype keywords found in titles:", dict(hits))


if __name__ == "__main__":
    main()
