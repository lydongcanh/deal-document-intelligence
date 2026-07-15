"""explore_cuad.py — a first look at the CUAD dataset.

The point of this script is NOT to train anything. It is to understand the
*shape* of the data before we pick a model — the single most valuable habit in
applied ML.

CUAD frames clause extraction as **extractive question answering**:

    INPUT   context  : the full text of a contract
            question : a templated prompt naming ONE clause type
                       (e.g. ...related to "Governing Law"...)
    OUTPUT  answers  : the span(s) of the contract that answer it, as text
                       plus their character offset (answer_start) into context

One row = one (contract, clause-type) pair. With ~510 contracts × 41 clause
types you get tens of thousands of rows. Crucially, MOST rows have an empty
answer — that clause type simply doesn't appear in that contract. Those empties
are genuine, useful negatives (they teach the model "not present"), not noise.

Run:  poetry run python scripts/explore_cuad.py
"""

import re
from datasets import load_dataset

# We load the auto-generated Parquet copy (revision below) instead of the
# dataset's default loader. The default is a Python script hosted on the Hub
# that `datasets` would have to download and EXECUTE (trust_remote_code=True).
# The Parquet route needs no code execution and keeps working in datasets 4.x.
DATASET_ID = "theatticusproject/cuad-qa"
REVISION = "refs/convert/parquet"

# Every CUAD question embeds its clause type in quotes:
#   'Highlight the parts ... related to "Governing Law" that should be ...'
_CLAUSE_RE = re.compile(r'related to "(.+?)"')


def clause_type(question: str) -> str:
    """Pull the clause-type label out of the templated question."""
    m = _CLAUSE_RE.search(question)
    return m.group(1) if m else question[:40]


def oneline(text: str, limit: int) -> str:
    """Collapse whitespace and truncate — contracts are full of newlines."""
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("…" if len(collapsed) > limit else "")


def main() -> None:
    print("Loading CUAD train split (first run downloads + caches ~tens of MB)…")
    ds = load_dataset(DATASET_ID, split="train", revision=REVISION)

    # --- dataset-level shape -------------------------------------------------
    n = len(ds)
    contracts = set(ds["title"])
    clause_types = sorted({clause_type(q) for q in ds["question"]})
    has_answer = sum(1 for a in ds["answers"] if a["text"])

    print("\n===== DATASET SHAPE =====")
    print(f"rows (contract × clause-type pairs) : {n:,}")
    print(f"unique contracts                    : {len(contracts):,}")
    print(f"clause types (questions/contract)   : {len(clause_types)}")
    print(
        f"rows with >=1 answer span           : {has_answer:,} "
        f"({has_answer / n:.1%}) — the remaining {1 - has_answer / n:.1%} are true negatives"
    )

    print("\n===== THE CLAUSE TYPES CUAD COVERS =====")
    for i, ct in enumerate(clause_types, 1):
        print(f"{i:2d}. {ct}")

    # --- a few concrete annotated clauses ------------------------------------
    # We show the answer span *inside* its surrounding contract text with ⟦ ⟧
    # markers, so you see exactly what the model is expected to locate.
    print("\n===== SAMPLE ANNOTATED CLAUSES (answer shown ⟦in context⟧) =====")
    shown = 0
    for ex in ds:
        ans = ex["answers"]
        if not ans["text"]:
            continue  # skip the negatives for this illustrative sample
        span = ans["text"][0]
        start = ans["answer_start"][0]
        ctx = ex["context"]
        pre = ctx[max(0, start - 100):start]
        post = ctx[start + len(span):start + len(span) + 100]

        print(f"\n--- contract : {oneline(ex['title'], 60)}")
        print(f"    clause   : {clause_type(ex['question'])}")
        print(f"    span     : «{oneline(span, 200)}»")
        print(f"    context  : …{oneline(pre + '⟦' + span + '⟧' + post, 320)}…")

        shown += 1
        if shown >= 4:
            break


if __name__ == "__main__":
    main()
