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
`training/clause_classification/evaluate_baselines.py`. **Both micro and macro are over the
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

> ⚠️ **Superseded.** The v1/v1.1/v1.2 numbers below were computed *before* the
> sentence-extraction bug fix (~3% of training/eval text was truncated) and on a
> dev set. Keep them as history; the clean-data retrain will replace them.

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

### Gold evaluation — Phase A (end-to-end, on real documents)

`eval/gold_clause_eval.py` runs the **full pipeline** (docling → segment →
trained classifier) on a small authored gold set and scores **document-level
clause presence** on the segmenter's *predicted* clauses — not clean CUAD
sentences. This is the number that reflects the product.

| Metric (2 gold docs, predicted clauses) | Value |
|---|---|
| document-level presence P / R / F1 | 0.588 / 0.714 / **0.645** |
| critical-clause recall | 4 / 5 |

Well below the isolated test micro (0.663) — exactly the **train/inference gap**
this phase exists to expose. The failure modes are informative:
- **Missed** provisions (*Termination for Convenience*, *Exclusivity*,
  *Non-Compete*, *Warranty Duration*) — rarer types and heading-led clauses that
  read unlike CUAD prose.
- **Spurious** *Document Name / Effective Date / Expiration Date / Agreement Date*
  — metadata-ish types over-firing on titles/dates. That's the low (0.10)
  threshold **and** the taxonomy mixing metadata with provisions — both already
  on the Phase B list.

**This is a development / acceptance set, NOT a blind test.** These two authored
(synthetic, not real Ansarada) markdown documents have been used to diagnose
thresholds and motivate the taxonomy split, so their F1 is a *dev* estimate, not
an unbiased measure of product performance. Required future work: a **separate
blind system-test set** — real PDFs/DOCX/scans, document families, OCR noise,
long contracts, tables, amendments — never inspected during development, with
gold clause boundaries + evidence (not just presence). Rename target: `dev_set`.

### Per-label thresholds (v1.1 — no retraining)

The gold precision drag came from a single global cutoff (0.10). Tuning a
**per-label threshold** on val (`tune_thresholds.py`; 17/41 labels tuned, the
rest below MIN_SUPPORT kept global) — **no retraining** — moved the metrics:

| Metric | v1 (global 0.10) | v1.1 (per-label) |
|---|---|---|
| test macro-F1 | 0.246 | **0.283** |
| test micro-F1 | 0.663 | 0.605 |
| gold document-level F1 | 0.645 | **0.667** |
| gold critical-clause recall | 4/5 | **5/5** |

macro-F1 and end-to-end recall (now every critical clause) improved for free;
micro precision traded down a little. The **remaining precision drag is a
taxonomy problem** — metadata-ish types (*Document Name*, dates) still over-fire,
and a threshold can't fix a type that shouldn't be a "provision-presence" signal
at all. That's the next lever (the taxonomy split below), *not* more epochs — the
cheap decision-rule fix beat what an epochs-only retrain would have done here.

### Taxonomy split — metadata vs provisions (v1.2 — no retraining)

We added a categorisation layer (`contracts/clause_category.py`):
`METADATA_TYPES` (Document Name, Parties, Agreement/Effective/Expiration Date)
vs `PROVISION_TYPES` (the other 36). The gold eval now scores **provision
presence** and reports metadata separately.

| gold metric | all-types (v1.1) | provisions-only (v1.2) |
|---|---|---|
| precision | 0.579 | **0.727** |
| recall | 0.786 | 0.727 |
| F1 | 0.667 | **0.727** |
| critical-clause recall | 5/5 | 5/5 |

**Caveat — this is a metric-definition change, not a model improvement.** The
predictions are identical; we simply stopped counting metadata types as
"provisions". So read it as *two different metrics* (all-type vs provision-only
presence), not a before/after model lift. (Also: *Effective/Expiration Date* are
sometimes substantive provision *attributes*, not pure metadata — a future schema
may split "provision attributes" from both.) The metadata (title/parties/dates)
is now surfaced as document *attributes* — whose natural home is entity extraction. The provision errors that remain — missed
*License Grant / Non-Compete / Warranty Duration*, spurious *Minimum Commitment /
Post-Termination Services* — are **genuine classifier weaknesses on rarer types**,
not fixable by thresholds or taxonomy. *That* is what now justifies a proper
retrain (Phase B: `OTHER`-as-independent-output + multiple seeds), bundled into
one run.

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

## Path to production (stage 5)

Today this is a **validated walking-skeleton model** (beats the floor; packaged;
integrity-checked). Remaining work to "production-ready", in dependency order:

**Phase A — trustworthy evaluation (the gate)**
- [x] End-to-end **gold set** + harness (`eval/`) — v1: authored docs, doc-level labels
- [x] Score classification on **predicted** clauses — gap surfaced (F1 0.645 vs 0.663 isolated)
- [x] **Document-level metrics**: presence/absence P/R/F1, critical-clause recall
- [ ] Extend gold set to **real PDFs** + gold clause **boundaries & evidence** (not just presence)
- [ ] Narrow to a **vertical slice** (few clause types, English commercial agreements) first

**Phase B — the real model**
- [ ] Retrain multi-epoch + early stopping + **multiple seeds / confidence intervals** (deduped split)
- [ ] Redesign `OTHER` as derived (41 independent outputs, exclude from loss/metrics)
- [x] Per-label thresholds (no retrain) — test macro 0.246→0.283, gold F1 0.645→0.667, crit 4/5→5/5
- [ ] Calibration (ECE/Brier) + precision/recall operating points; taxonomy split for metadata over-firing
- [x] Taxonomy split (metadata vs provisions) — gold provision F1 0.667→0.727 (precision 0.579→0.727)
- [ ] Rare-type tail (class weighting / more data); compare solution families (encoder vs LLM vs hybrid)
- [ ] Tokenizer audit + lock; multilingual validation

**Phase C — productionize**
- [ ] Provenance + model registry + publish (checkpoint hash, base revision, dataset/split version, card, license)
- [ ] Serving (batching, latency/memory, API) + monitoring (drift, abstention — Arize Phoenix)
- [ ] CI (tests + lint + type-check + a tiny deterministic model-inference test)
- [ ] Data governance (confidential docs) + human-in-the-loop correction / active learning

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
  tokenizer (no skew). **Decision (for now): keep the legacy tokenizer** — the
  fix's gain is small and switching needs a data re-tokenise + retrain. This must
  be **locked** before the production multi-seed campaign.
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
poetry run python training/clause_classification/evaluate_baselines.py  # baseline metrics
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
- **2026-07-18** — Started Phase A. Added a `README.md` + repo `Makefile` (one
  command per step, `make help`), and an end-to-end gold harness
  (`eval/gold_clause_eval.py` + `eval/gold/`, `make clause-gold-eval`). First
  result on **predicted** clauses: document-level presence **F1 0.645** (P 0.588
  / R 0.714), critical-clause recall **4/5** — below the isolated test micro
  (0.663), quantifying the train/inference gap. Over-fires metadata types
  (Document Name, dates); misses rarer provisions.
- **2026-07-18** — **Per-label thresholds** (no retraining): `tune_thresholds.py`
  picks each type's cutoff on val (17/41 tuned); classifier + `evaluate_model.py`
  now apply them (evaluate_model predicts *via* the classifier — one source of
  truth). Result: test macro **0.246→0.283**, gold F1 **0.645→0.667**, critical
  recall **4/5→5/5** (micro traded 0.663→0.605). The cheap decision-rule lever
  beat an epochs-only retrain for the gold failure; remaining precision drag is a
  taxonomy issue (metadata types), the next lever. Also renamed
  `evaluate.py`→`evaluate_baselines.py` and added a repo `Makefile` + folder READMEs.
- **2026-07-18** — **Taxonomy split** (`contracts/clause_category.py`): METADATA (5)
  vs PROVISION (36). Gold eval scores provision presence; metadata reported
  separately. Gold provision F1 **0.667→0.727** (precision 0.579→0.727), critical
  recall 5/5. Remaining provision errors are genuine model weaknesses on rare
  types → now the justification for a Phase-B retrain (bundle OTHER-as-independent
  -output + multiple seeds).
- **2026-07-18** — Third review pass. **Data bug fixed:** `_sentence_at` stepped
  2 chars past a `\n` boundary (only ". " is 2), truncating the first character
  of ~3% of examples ("This"→"his"); fixed + dataset rebuilt (0 truncations) +
  regression test added. ⚠️ **All earlier v1/v1.1/v1.2 numbers predate this fix
  (partly-corrupted data) and are superseded — they'll be recomputed after a
  clean retrain.** Also fixed/added: (3) checkpoint selection now uses macro
  **average-precision** (threshold-independent) not F1@0.5; (5) threshold
  tie-break prefers the higher cutoff (precision) + loaded thresholds validated
  ∈[0,1]; (4) classifier accepts a bare HF id (org/model), not just local paths;
  (9) `metrics.score` raises on gold/pred length mismatch; (13) `IntegrityError`
  in its own module; (10) 41-vs-42 wording synced + `LABEL_SCHEMA` id +
  duplicate-label guard; (7) `run_manifest.json` (git SHA, seed, schema, metrics)
  written per checkpoint. Reframed docs: the taxonomy 0.667→0.727 is a
  metric-definition change (not a model lift); the gold set is a **dev/acceptance
  set, not a blind test**. Retrained on the OTHER-derived 41-output design but
  **stopped** when this bug surfaced — the retrain is re-queued on clean data.
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
