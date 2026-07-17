ok# Clause Classification (Stage 5): A Living Technical Report

> A working paper documenting the design, data, and results of the clause
> classification model. It is **updated as the work progresses** — see the
> [Changelog](#changelog) at the bottom. Numbers reflect the latest build.

## Abstract

Stage 5 of the deal-document-intelligence pipeline assigns a **clause type** to
each segmented clause. It is the first custom model we build, because it is the
stage where domain training most clearly beats generic tooling: the target
labels are M&A / due-diligence clause types that off-the-shelf models have no
notion of. This report describes the task, the data we assembled from two public
corpora (CUAD and LEDGAR), the construction methodology, and the resulting
dataset. As of this writing the **labelled dataset is built and inspected**;
model training and evaluation are the next steps.

## 1. Task

- **Input.** The text of a single segmented clause (produced by stage 4).
- **Output.** Zero or more clause types from a controlled vocabulary
  (**multi-label**); the absence of any deal type is represented explicitly by
  an `OTHER` label.
- **Framing.** Multi-label text **classification** — *not* extractive QA. This
  matches the pipeline's segment-then-classify design: by stage 5 the clause has
  already been isolated, so the model classifies it rather than locating it.

## 2. Why this model first

Among the pipeline's differentiator stages, clause classification is the best
first investment for the Ansarada (M&A due-diligence) use case:

1. **Generic tools are weak here.** Types like *Change of Control*, *ROFR/ROFO*,
   *MFN*, *Cap on Liability* are meaningless to off-the-shelf classifiers.
2. **Labelled domain data exists** — rare, and decisive.
3. **It is foundational** — clause type routes downstream stages (which entities
   matter, which obligations to expect, deal-level rollups).
4. **Immediate measurable win** — it replaces a keyword baseline that already
   visibly misfires (e.g. "non-**exclusive**" → *Exclusivity*).

## 3. Data

### 3.1 Sources

| Source | Content | Format | Role here |
|--------|---------|--------|-----------|
| **CUAD** (`theatticusproject/cuad-qa`) | 510 commercial contracts, 41 M&A due-diligence clause types, lawyer-annotated | extractive QA | **deal-critical positives** |
| **LEDGAR** (`coastalcph/lex_glue`, `ledgar`) | ~60k contract provisions, 100 provision types | classification | **negatives (`OTHER`) + 5 overlap types** |

Both are loaded via their Parquet revisions where needed, so no remote-code
execution is required.

### 3.2 Taxonomy

The canonical label space is **CUAD's 41 clause types** (`ClauseType` in the
package), because those *are* the M&A due-diligence taxonomy Ansarada reviews.
A 42nd label, `OTHER` (represented by `ClauseType.UNKNOWN`), captures clauses
that are none of the 41.

### 3.3 Finding: LEDGAR–CUAD overlap is small

Inspecting LEDGAR's 100 labels showed they are mostly generic/administrative
provisions (*Counterparts*, *Headings*, *Notices*, *Severability*, *Waivers*…).
Only **five** map to CUAD types with high confidence:

```
Change In Control → Change Of Control    Governing Laws → Governing Law
Effective Dates   → Effective Date        Insurances     → Insurance
Non-Disparagement → Non-Disparagement
```

Broader-but-ambiguous labels (LEDGAR *Assignments*, *Terminations*, *Warranties*)
are **deliberately left as `OTHER`** to avoid label noise, since they are wider
than CUAD's *Anti-Assignment*, *Termination for Convenience*, *Warranty Duration*.

Consequence: **CUAD supplies the deal-critical positives; LEDGAR supplies a large
pool of realistic negatives** (plus the five overlap types). The negatives teach
the model what is *not* a deal clause, sharpening precision on the ones that are.

### 3.4 Dataset construction

Implemented in `training/clause_classification/` (`ClauseDatasetBuilder`):

- **CUAD → positives.** For every answer span, the containing **sentence** is
  extracted; `(contract, sentence)` pairs are merged so a sentence carrying two
  clause types becomes a single **multi-label** example.
- **LEDGAR → overlap + negatives.** Each provision is mapped via §3.3; mapped
  provisions become positives for the overlap type, the rest become `OTHER`.
  `OTHER` is **capped** (currently 15,000) to limit class imbalance.

### 3.5 Splits (leakage-free)

Examples are assigned to train/val/test by a deterministic hash of their
**source document id** (`md5(doc_id) % 10` → 0 = test, 1 = val, else train). All
clauses from one contract therefore land in the same split, preventing
train/test leakage across clauses of the same document.

### 3.6 Multilingual strategy

The project targets multilingual documents, but **no public multilingual
contract-clause dataset exists**. The plan is therefore: train on English
(CUAD + LEDGAR) with a **multilingual encoder** (XLM-R / mDeBERTa) and rely on
**cross-lingual transfer**, validating on non-English contracts once available.
The data-prep is language-agnostic so non-English data can be added later.

## 4. Dataset statistics (current build)

| Metric | Value |
|--------|-------|
| Total examples | **31,005** |
| Train / Val / Test | 24,664 / 3,293 / 3,048 |
| Source: CUAD / LEDGAR | 10,560 / 20,445 |
| Deal-type positives | 18,094 (across all 41 types) |
| `OTHER` negatives | 15,000 |
| Multi-label examples | 1,468 |

Most frequent clause types:

| Clause type | Examples | | Clause type | Examples |
|---|---|---|---|---|
| Governing Law | 3,630 | | Anti-Assignment | 650 |
| Insurance | 1,659 | | Audit Rights | 642 |
| Parties | 1,444 | | Change Of Control | 599 |
| Effective Date | 909 | | Document Name | 519 |
| License Grant | 775 | | Agreement Date | 475 |
| Cap On Liability | 670 | | Expiration Date | 467 |

### Baseline results (the floor to beat)

Evaluated on the held-out **test** split (3,048 examples) via
`training/clause_classification/evaluate.py`:

| Baseline | micro-F1 | macro-F1 (deal types, excl. OTHER) |
|----------|----------|------------------------------------|
| all-`OTHER` (floor) | 0.458 | 0.000 |
| keyword matching | 0.459 | **0.166** |

**The number the trained model must beat is macro-F1 = 0.166.** The keyword
baseline is predictably brittle: strong where a type name appears verbatim
(*Insurance* F1 0.85) but collapsing otherwise — *Governing Law* recall is 0.04
because clauses say "the laws of the State of …", not "governing law" — and 0.00
on types with no obvious keyword (*Cap on Liability*, *ROFR/ROFO*, *Document
Name*). That gap is the headroom a trained model should capture.

### Trained model — v1 (Legal-XLM-R-base, 1 epoch)

Fine-tuned `Legal-XLM-RoBERTa-base` (multi-label, sigmoid + BCE) for **1 epoch**
on the full 24,664 training examples (~29 min on an M3, MPS). Decision threshold
tuned on val (best = **0.10** — rare multi-label classes rank positives below
0.5). Scored on the **test** split via `evaluate_model.py`:

| Model | micro-F1 | macro-F1 (deal types) |
|-------|----------|-----------------------|
| keyword baseline | 0.459 | 0.166 |
| **Legal-XLM-R (1 epoch)** | **0.677** | **0.252** |

**Beats the floor** (+0.086 macro, +0.218 micro). Frequent/clear types are
already strong — *Governing Law* 0.95, *Insurance* 0.90, *Cap on Liability*
0.85, *Parties* 0.82, *Audit Rights* 0.71 — while the rare tail is the headroom:
*ROFR/ROFO* 0.00, *Anti-Assignment* recall 0.26. A longer run (3 epochs) is the
obvious next lever.

## 5. Roadmap

- [x] **Data prep** — build the labelled, split dataset *(done — this report)*
- [x] **Evaluation harness + baseline floor** — multi-label P/R/F1 (micro, macro,
      per-type) on the test split → keyword baseline **macro-F1 = 0.166** (the floor)
- [x] **Train** a multilingual encoder → Legal-XLM-R-base, 1 epoch, checkpoint in
      `models/clause_classifier/`
- [x] **Measure the lift** vs baseline → test **macro-F1 0.252 vs 0.166**, micro
      **0.677 vs 0.459**
- [ ] **Longer run (3 epochs)** to lift the rare-type tail *(optional next lever)*
- [ ] **Package `Classifier` implementation** loading the checkpoint, to replace
      the demo's `KeywordClassifier` in the pipeline

## 6. Known limitations (to revisit)

- **Sentence extraction is heuristic** — CUAD positives are the sentence around
  an answer span, which may over- or under-capture the true clause boundary.
- **Train/inference distribution gap** — training text is CUAD sentences and
  LEDGAR provisions; at inference the input is a stage-4 segmented clause. Worth
  monitoring; may motivate training on segmented clauses later.
- **`Governing Law` is inflated** by LEDGAR's mapped provisions.
- **`OTHER` cap (15,000) is arbitrary** — a class-balance lever to tune.
- **Multilingual transfer is unvalidated** — no non-English test data yet.
- **Rare-type tail is weak** — several low-support deal types (e.g. *ROFR/ROFO*)
  score ~0 after 1 epoch; more epochs and/or class weighting are the levers.
- **Pretraining exposure** — Legal-XLM-R was pretrained (unsupervised) on legal
  text that may overlap our sources, so test metrics could be mildly optimistic.
- **Tokenizer warning** — transformers 4.57 emits a benign "mistral regex"
  warning for this tokenizer; results confirm tokenization is correct.

## 7. Reproducibility

```bash
poetry install                 # datasets + huggingface-hub
poetry run python training/clause_classification/build_clause_dataset.py
# → data/clause_classification/{train,val,test}.jsonl
poetry run python training/clause_classification/evaluate.py
# → baseline metrics on the test split

poetry install --with training                          # torch, transformers, ...
poetry run python training/clause_classification/train.py --smoke   # validate loop
poetry run python training/clause_classification/train.py --epochs 1 # full 1-epoch run
poetry run python training/clause_classification/evaluate_model.py   # trained model on test
```

## Changelog

- **2026-07-16** — Initial report. Dataset built from CUAD + LEDGAR (31,005
  examples); taxonomy, construction, splits, and statistics documented. Training
  and evaluation not yet started.
- **2026-07-16** — Added the evaluation harness (`evaluate.py`) and baselines.
  Floor on the test split: keyword **macro-F1 (deal types) = 0.166**,
  micro-F1 = 0.459; all-`OTHER` micro-F1 = 0.458, macro = 0.000. This is the
  number the trained model must beat.
- **2026-07-17** — Trained v1: `Legal-XLM-R-base`, 1 epoch, full data (~29 min,
  M3/MPS), threshold tuned to 0.10. Test: **macro-F1 (deal types) = 0.252**,
  **micro-F1 = 0.677** — beats the 0.166 floor. Strong on frequent types
  (Governing Law 0.95, Insurance 0.90); rare tail (ROFR 0.00) is the headroom.
  Added `train.py` and `evaluate_model.py`.
