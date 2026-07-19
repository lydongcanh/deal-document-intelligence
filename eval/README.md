# eval/ — end-to-end (product) evaluation

There are **two kinds of evaluation** in this repo, and they answer different
questions. Keeping them apart is deliberate:

| Question | "How good is the clause **model**, in isolation?" | "Does the whole **product** work on a real document?" |
|---|---|---|
| Kind | **component / model** eval | **system / product** eval |
| Input | clean clause text from the held-out **test split** | a real document → the **full pipeline** (docling → segment → classify) |
| Metric | micro/macro-F1 over the 41 types | **document-level** clause presence (P/R/F1), critical-clause recall |
| Lives in | `training/clause_classification/evaluate_baselines.py` + `evaluate_model.py` | **`eval/gold_clause_eval.py`** (this folder) |

**Why both?** The component eval trains and tunes the model on *clean CUAD
sentences*. But production input is messy: OCR → segmentation → whatever the
segmenter hands the classifier. A model can look great in isolation and still
miss clauses end-to-end. The gold eval measures that gap — and it's the number
that reflects what a user actually experiences.

## The data, and why there are two "held-out" sets

Three splits come out of `build_clause_dataset.py`:

- **train** — the model learns from these (weights update).
- **val** (validation) — *never trained on*, but used **during development** to
  tune knobs without touching test: pick the best checkpoint, and tune the
  decision threshold (see `train.py`). Think "practice exam you may peek at."
- **test** — the **untouched** final holdout, scored once at the end for an
  unbiased grade. Never tune on it (that would leak/overfit to it).

All three are the **same kind of data** (CUAD sentences + LEDGAR provisions) — good
for developing the model, but *in-distribution*.

The **gold set** here (`gold/`) is different on purpose: it's a small set of whole
documents run through the **real pipeline**, scored at the document level. It is
**out-of-distribution and end-to-end**.

**Status: this is a development / acceptance set, NOT a blind test.** The current
`gold/` docs are **authored, synthetic** markdown (2 docs) and have been used to
tune thresholds and taxonomy — so their score is a *dev* estimate. A true blind
test needs real PDFs/DOCX/scans, never inspected during development, with gold
boundaries + evidence. Treat this as fast iteration signal, not a final grade.

## Run

```bash
make clause-gold-eval
# or: poetry run python eval/gold_clause_eval.py
```

## Contents

- `gold/docs/*.md` — authored gold documents (ground truth is known because we wrote them)
- `gold/labels.json` — the document-level clause types each doc contains
- `gold_clause_eval.py` — runs the full pipeline + scores presence on **predicted** clauses

v1 caveats: authored (not real Ansarada) docs; document-level *presence* only —
real PDFs and gold clause boundaries + evidence are the next increment.
