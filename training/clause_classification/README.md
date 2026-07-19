# Clause Classification (Stage 5) — training pipeline

Turns public contract data (CUAD + LEDGAR) into a labelled dataset and fine-tunes
a multilingual clause classifier. Deep write-up (design, results, limitations):
[`../../docs/clause_classification.md`](../../docs/clause_classification.md).

## Run order (from the repo root)

```bash
make install-training     # datasets + torch + transformers
make clause-explore       # 0. (optional) eyeball the CUAD data
make clause-dataset       # 1. build the labelled, split, deduped dataset
make clause-baseline      # 2. baseline floor (keyword) — the number to beat
make clause-train         # 3. fine-tune Legal-XLM-R (1 epoch) → checkpoint
make clause-eval          # 4. score the trained model on the test split
```

Each target maps to exactly one script (below). `make clause-*` rebuilds the
dataset first if it's missing. Without `make`, run the scripts in the same order:
`poetry run python training/clause_classification/<file>`.

## Files

| File | Kind | Role | In → Out |
|------|------|------|----------|
| `explore_cuad.py` | step | inspect CUAD | HF CUAD → stdout |
| `taxonomy_mapping.py` | lib | LEDGAR → CUAD-41 label map | (imported) |
| `clause_example.py` | lib | `ClauseExample` row schema | (imported) |
| `build_clause_dataset.py` | step | CUAD+LEDGAR → labelled, split, deduped dataset | HF → `artifacts/data/clause_classification/{train,val,test}.jsonl` |
| `metrics.py` | lib | shared scoring (micro/macro over the 41 deal types) | (imported by both evaluators + training) |
| `evaluate.py` | step | baseline predictors on test | dataset → stdout |
| `train.py` | step | fine-tune a multilingual encoder | dataset → `artifacts/models/clause_classifier/` |
| `evaluate_model.py` | step | score the trained model on test | model + dataset → stdout |

**lib** = imported, no `__main__`. **step** = runnable (`python <file>` / a `make` target).

## Artifacts (all gitignored, under `artifacts/`)

- Dataset → `artifacts/data/clause_classification/`
- Checkpoint + tuned `threshold.json` → `artifacts/models/clause_classifier/`

## Graduation path

One stage today, so plain scripts + `make` are right-sized. When this grows to
several stages/models needing reproducible, versioned runs, adopt **DVC**
(`dvc.yaml` stages + `dvc repro` for ordering/versioning) and **MLflow / W&B**
for experiment tracking.
