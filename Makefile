# Makefile — one command per pipeline step. Run `make` (or `make help`) to list.
#
# POETRY defensively unsets any inherited VIRTUAL_ENV so Poetry uses THIS
# project's .venv (harmless if none is set; fixes a shell that auto-activates
# a different venv).
POETRY := env -u VIRTUAL_ENV poetry
PY := $(POETRY) run python
DATASET := artifacts/data/clause_classification/train.jsonl

.DEFAULT_GOAL := help
.PHONY: help install install-training install-demo test \
        clause-explore clause-dataset clause-baseline clause-train \
        clause-tune-thresholds clause-eval clause-gold-eval demo

help:  ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---- setup ----
install:  ## Install core only (light: pydantic)
	$(POETRY) install
install-training:  ## Install the training stack (datasets, torch, transformers)
	$(POETRY) install --with training
install-demo:  ## Install the demo stack (docling)
	$(POETRY) install --with demo

test:  ## Run the test suite
	$(PY) -m pytest tests/ -q

# ---- stage 5: clause classification (run in this order) ----
clause-explore:  ## 0. Inspect the CUAD dataset
	$(PY) training/clause_classification/explore_cuad.py

$(DATASET): training/clause_classification/build_clause_dataset.py \
            training/clause_classification/taxonomy_mapping.py \
            training/clause_classification/clause_example.py
	$(PY) training/clause_classification/build_clause_dataset.py

clause-dataset: $(DATASET)  ## 1. Build the labelled dataset (CUAD + LEDGAR)

clause-baseline: $(DATASET)  ## 2. Score baseline predictors (the floor)
	$(PY) training/clause_classification/evaluate_baselines.py

clause-train: $(DATASET)  ## 3. Fine-tune Legal-XLM-R (1 epoch) -> checkpoint
	$(PY) training/clause_classification/train.py --epochs 1

clause-tune-thresholds:  ## 3b. Tune per-label thresholds on val (no retraining)
	$(PY) training/clause_classification/tune_thresholds.py

clause-eval:  ## 4. Score the trained model on the test split
	$(PY) training/clause_classification/evaluate_model.py

clause-gold-eval:  ## 5. End-to-end gold eval on real docs (doc-level presence)
	$(PY) eval/gold_clause_eval.py

# ---- demo ----
demo:  ## Run the demo (default: the sample lease). Pass DOC=path to override.
	$(PY) demo/main.py $(DOC)
