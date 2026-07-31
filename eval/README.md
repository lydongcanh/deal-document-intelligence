# eval/

Evaluation harnesses, one folder per feature, so this scales as we add stages.

```
eval/
  clause_classification/   # stage 5: is the clause model any good?
    gold_clause_eval.py    # (STALE: references the removed walking-skeleton demo; rebuild)
    gold/                  # authored dev docs + document-level labels
  clause_segmentation/     # stage 4: did we recover the right clauses?
    measure.py             # corpus-wide consistency + coverage (no labels needed)
    score.py               # correctness vs dev/acceptance labels
    gold/                  # dev/acceptance labels (see its README)
```

## Two principles that apply to every feature

Component versus system. A component eval scores a model in isolation on clean,
in-distribution data (for example the clause classifier on held-out CUAD
sentences, in `training/`). A system eval runs a real document through the actual
pipeline and scores the end result. A model can look great in isolation and still
fail end to end, so we keep both.

Dev/acceptance versus golden. A dev or acceptance set is small, possibly
in-distribution, and may be used during development for iteration signal and
regression detection. A golden benchmark is representative, larger, labelled by
independent reviewers, and held out from all tuning. Everything currently under
`eval/` is dev/acceptance, not golden. We name it honestly and do not claim
production readiness from it. See each feature's `gold/README.md` for its exact
scope.

## Run

```bash
make seg-measure     # segmentation: consistency + coverage over the corpus
make seg-score       # segmentation: correctness vs dev/acceptance labels
make clause-gold-eval  # clause classification (currently stale, pending rebuild)
```

Results write to `artifacts/eval/` (gitignored); labels live in the repo.
