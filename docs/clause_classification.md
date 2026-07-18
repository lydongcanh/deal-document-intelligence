# Clause Classification (Stage 5): A Living Technical Report

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
dataset, and the trained baseline model. As of this writing the dataset is built
(leakage-checked), and a first model — **Legal-XLM-R fine-tuned for 1 epoch** —
**beats the keyword baseline** (test macro-F1 0.246 vs 0.162 over all 41 deal
types) and is packaged as a pipeline `Classifier`. It is a **walking-skeleton
model, not production-grade**: rare-type performance and a proper multi-epoch
retrain on the deduped split are open work.

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

### 3.5 Splits (leakage-checked)

Examples are assigned to train/val/test by a deterministic hash of their
**source document id** (`md5(doc_id) % 10` → 0 = test, 1 = val, else train), so
all clauses of one contract land in the same split. That alone is **not
sufficient**: identical boilerplate sentences recur across *different* contracts
(a review found 11/12/1 exact-text overlaps train↔val/train↔test/val↔test), so a
second pass **dedups exact text across splits** (train > val > test priority),
keeping each unique text in a single split (labels of duplicates are merged).
After it, cross-split exact-text overlap is **0/0/0**.

Caveats (future work): (a) splitting-by-`doc_id` only groups **CUAD** by
contract — LEDGAR rows have no source-document identity in `lex_glue`, so each
LEDGAR provision is its own "document"; (b) exact-text dedup does not catch
**paraphrased/templated** near-duplicates; (c) the train>val>test dedup priority
is a small selection bias. Stronger approach: group near-duplicates + contract
families, assign each group to one split, and persist a split manifest.

### 3.6 Multilingual strategy

The project targets multilingual documents, but **no public multilingual
contract-clause dataset exists**. The plan is therefore: train on English
(CUAD + LEDGAR) with a **multilingual encoder** (XLM-R / mDeBERTa) and rely on
**cross-lingual transfer**, validating on non-English contracts once available.
The data-prep is language-agnostic so non-English data can be added later.

## 4. Dataset statistics (current build)

Post-dedup build (cross-split exact-text overlap 0/0/0):

| Metric | Value |
|--------|-------|
| Total examples | **30,900** |
| Train / Val / Test | 24,584 / 3,280 / 3,036 |
| Source: CUAD / LEDGAR | 10,455 / 20,445 |
| Deal-type positives | 17,976 (across all 41 types) |
| `OTHER` negatives | 15,000 |
| Multi-label examples | 1,459 |

Most frequent clause types:

| Clause type | Examples |
|---|---|
| Governing Law | 3,627 |
| Insurance | 1,658 |
| Parties | 1,428 |
| Effective Date | 906 |
| License Grant | 762 |
| Cap On Liability | 669 |
| Anti-Assignment | 642 |
| Audit Rights | 641 |
| Change Of Control | 599 |
| Document Name | 481 |
| Agreement Date | 473 |
| Expiration Date | 464 |

### Baseline results (the floor to beat)

Evaluated on the held-out **test** split (3,036 examples) via
`training/clause_classification/evaluate.py`. **Both micro and macro are over the
41 deal types with `OTHER` excluded** (so the easy, abundant OTHER class can't
inflate the number):

| Baseline | micro-F1 | macro-F1 (all 41 deal types) |
|----------|----------|------------------------------------|
| all-`OTHER` (floor) | 0.000 | 0.000 |
| keyword matching | 0.318 | **0.162** |

**The number the trained model must beat is macro-F1 = 0.162.** The keyword
baseline is predictably brittle: strong where a type name appears verbatim
(*Insurance* F1 0.85) but collapsing otherwise — *Governing Law* recall is 0.04
because clauses say "the laws of the State of …", not "governing law" — and 0.00
on types with no obvious keyword (*Cap on Liability*, *ROFR/ROFO*, *Document
Name*). That gap is the headroom a trained model should capture.

### Trained model — v1 (Legal-XLM-R-base, 1 epoch)

Fine-tuned `Legal-XLM-RoBERTa-base` (multi-label, sigmoid + BCE) for **1 epoch**
(~29 min on an M3, MPS). Decision threshold tuned on val (best = **0.10** — rare
multi-label classes rank positives below 0.5). Scored on the **test** split via
`evaluate_model.py` (micro/macro over the 41 deal types, `OTHER` excluded):

| Model | micro-F1 | macro-F1 (all 41 deal types) |
|-------|----------|-----------------------|
| keyword baseline | 0.318 | 0.162 |
| **Legal-XLM-R (1 epoch)** | **0.663** | **0.246** |

**Beats the floor** (macro +0.084, micro +0.345). Frequent/clear types are
already strong — *Governing Law* 0.95, *Insurance* 0.90, *Cap on Liability*
0.85, *Parties* 0.82, *Audit Rights* 0.71 — while the rare tail is the headroom:
*ROFR/ROFO* 0.00, *Anti-Assignment* recall 0.27. **Caveat:** this checkpoint was
trained on the pre-dedup split and re-evaluated on the clean test split (the
delta was negligible); a clean multi-epoch retrain is the proper next run.

## 5. Roadmap

- [x] **Data prep** — build the labelled, split dataset *(done — this report)*
- [x] **Evaluation harness + baseline floor** — multi-label P/R/F1 (micro, macro,
      per-type) on the test split → keyword baseline **macro-F1 = 0.162** (the floor)
- [x] **Train** a multilingual encoder → Legal-XLM-R-base, 1 epoch, checkpoint in
      `artifacts/models/clause_classifier/`
- [x] **Measure the lift** vs baseline → test **macro-F1 0.246 vs 0.162**, micro
      **0.677 vs 0.459**
- [x] **Package `Classifier` implementation** — `TransformerClauseClassifier`
      (torch/transformers behind the `[classification]` extra); drops into the
      pipeline via the `Classifier` interface (`demo/walking_skeleton.py --trained`)

**Next priority is NOT "3 more epochs."** A second review argued (persuasively)
for: (1) build a small **end-to-end real-document gold set** (OCR → blocks →
clause boundaries → labels → evidence) so isolated-F1 gains are validated against
the *actual* product; (2) narrow to a **vertical slice** (e.g. termination /
change-of-control / governing-law / assignment / liability in English commercial
agreements) and make it reliable end-to-end; (3) add **document-level** metrics
(presence/absence, critical-clause recall, evidence exact-match); (4) fix
OTHER-as-output, per-label thresholds, tokenizer + provenance; *then* retrain
with multiple seeds + early stopping (a single 3-epoch run can't separate a real
gain from run variance). Taxonomy also mixes metadata (Document Name, Agreement
Date) with true provision types — worth separating.

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
- **Tokenizer warning** — transformers 4.57 flags a "mistral regex" on this fast
  tokenizer. A controlled check showed `fix_mistral_regex=True` **does change
  tokenization** (1/2 sample clauses) — so it is *not* cosmetic. It is harmless
  *for us* only because training and inference load the identical (unfixed)
  tokenizer (no skew). **Do not apply the fix without retraining.**
- **`OTHER` as an independent output** — the model has a 42nd sigmoid for
  OTHER/UNKNOWN, so it can predict OTHER *and* a deal type simultaneously.
  Cleaner (at next retrain): 41 independent deal outputs, derive OTHER when none
  fire, exclude OTHER from BCE, and measure abstention separately.
- **Single global threshold (0.10)** — one threshold across 41 labels with very
  different frequencies/calibration is weak. Future: per-label thresholds (with
  min-support guards), calibration (ECE/Brier), and precision- vs recall-oriented
  operating points driven by due-diligence costs (a missed clause ≠ a false one).

## 7. Reproducibility

```bash
poetry install --with training     # datasets + torch + transformers (training stack)
poetry run python training/clause_classification/build_clause_dataset.py
# → artifacts/data/clause_classification/{train,val,test}.jsonl
poetry run python training/clause_classification/evaluate.py          # baseline metrics
poetry run python training/clause_classification/train.py --smoke     # validate the loop
poetry run python training/clause_classification/train.py --epochs 1  # full 1-epoch run
poetry run python training/clause_classification/evaluate_model.py    # trained model on test
```

## Changelog

- **2026-07-16** — Initial report. Dataset built from CUAD + LEDGAR (31,005
  examples); taxonomy, construction, splits, and statistics documented. Training
  and evaluation not yet started.
- **2026-07-16** — Added the evaluation harness (`evaluate.py`) and baselines.
  Floor on the test split: keyword **macro-F1 (deal types) = 0.162**,
  micro-F1 = 0.459; all-`OTHER` micro-F1 = 0.458, macro = 0.000. This is the
  number the trained model must beat.
- **2026-07-17** — Trained v1: `Legal-XLM-R-base`, 1 epoch, full data (~29 min,
  M3/MPS), threshold tuned to 0.10. Test: **macro-F1 (deal types) = 0.246**,
  **micro-F1 = 0.677** — beats the 0.162 floor. Strong on frequent types
  (Governing Law 0.95, Insurance 0.90); rare tail (ROFR 0.00) is the headroom.
  Added `train.py` and `evaluate_model.py`.
- **2026-07-17** — Packaged the model as `classification/transformer_clause_classifier.py`
  (`TransformerClauseClassifier`, torch/transformers behind the `[classification]`
  extra; lazy import so core installs stay light). Wired into the demo via
  `--trained`. (Original observation on the demo doc: strong on frequent types
  Governing
  Law 0.83, Parties 0.74), weak on the rare tail (Minimum Commitment → Insurance)
  — the train/inference gap (short heading-led clauses are OOD vs CUAD prose) and
  the recall-tuned threshold (0.10) both show. Integration itself is clean;
  quality levers remain: longer training, threshold-per-use-case, clause-like
  training inputs.
- **2026-07-18** — Second review pass. Fixed: (1) `evaluate_model.py` **crash**
  (`NameError: deal`) by centralising scoring in `metrics.py` (both evaluators +
  training share one definition); (2) micro-F1 now **excludes OTHER** — honest
  deal-only numbers **baseline micro 0.318 / macro 0.162**, **trained micro 0.663
  / macro 0.246** (earlier micro figures were OTHER-inflated); (3) pipeline
  **validation modes** off/warn/**strict** + typed `ValidationIssue`/`IntegrityError`
  (renamed `validate()`→`validate_integrity()`, added unique-id / clause_id FK /
  text==slice / primary-vs-top-prediction / page-block checks); (4) dedup now
  **merges duplicate labels**; (5) classifier accepts a **local path or HF id**;
  (6) added ML-workflow tests (metric, dedup, strict validation). Documented as
  future work: OTHER-as-independent-output, per-label thresholds/calibration,
  tokenizer audit, model provenance, and a **strategic pivot** (gold set +
  narrow vertical + document-level metrics before more epochs).
- **2026-07-17** — External-review pass. Fixed: (1) eval metric now averages the
  **fixed 41 deal types** in every path (train/threshold/eval) — corrected test
  numbers **baseline 0.162, trained 0.246** (were 0.166/0.252 over 40, since
  *Source Code Escrow* is absent from test); (2) dataset now **dedups exact text
  across splits** → cross-split overlap 0/0/0 (was 11/12/1); (3) **evidence
  integrity enforced** — `verify()` bounds-checks, `EvidenceBackedResult.validate()`
  checks doc_id, required evidence, and relation foreign keys, and the pipeline
  surfaces issues in `meta["validation_issues"]`; (4) multi-label output is now
  typed (`ClausePrediction`, `ClauseUnit.predictions`); (5) core deps slimmed to
  **pydantic only** (datasets/hub → training group); (6) classifier is CUDA-aware
  and validates its inputs. **Outstanding:** the current checkpoint predates the
  dedup, so a clean multi-epoch retrain is the proper next run.
