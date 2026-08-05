# Document-type dataset + model plan (synthetic-primary, v1 pilot)

Committed approach for a publishable document-type classifier over our 23-type
taxonomy (`docs/03-document-type.md`). Training data is SYNTHETIC (LLM-generated);
evaluation uses small, human-verified REAL data. This is a PILOT plan: it validates a
few classes honestly, it is not production certification. Written to be judged by
Codex against the checklist at the end.

## Decision and why

- No open dataset exists for our taxonomy. Synthetic generation gives balance, full
  type coverage, and zero confidential data.
- It REDUCES but does not eliminate leakage: no eval document is ever shown to the
  generator (no direct prompt exposure), but the generator/base model may have seen
  public corpora in pretraining, so we add contamination checks (see Splits).
- The realism gap and generator bias are contained by real, human-verified evaluation
  below, not by avoiding synthetic.

## Hard constraints

- Publishable: generator output and base model must be redistributable. Legal-XLM-R
  is CC BY-SA (attribution + share-alike), which constrains the published model's
  licence; note it in the model card.
- **Content-only features.** The model reads document content only. Filename/folder
  are never features and never in eval.
- **Map to our taxonomy** (`type` leaf; `category`/`form` derived; `subtype`
  descriptive only, not used for routing in v1).
- **The guardrail: evaluation uses REAL, human-verified documents in three disjoint
  pools.** Synthetic never appears in any real pool. Weak metadata labels are
  candidates only; every real doc (adaptation, dev, test) is human-verified. Class
  status is three-tier (see Metrics): experimental / pilot_validated / production_validated.
- **English-only v1.** All real pilot sources are effectively English; Legal-XLM-R is
  multilingual, but a language ships only with its own real dev/test. Jurisdiction
  diversity is not language coverage.

## Standalone model interface (decoupled from the package)

Usable by anyone with `transformers`, no dependency on this package.

- **Input**: a text string. Lightweight-Markdown from a modern parser is the expected
  PRIMARY input; plain text (pdftotext, OCR, .txt, email) is a supported robustness
  FALLBACK. Still just a string: no ParsedDocument, no structured object, no parser
  dependency. Trained mostly on Markdown with a plain-text and degraded/noisy
  minority.
- **Frozen preprocessing**: the first **512 tokens** from the document start (type is
  usually clear from the opening), identical at train and inference. Long-document
  pooling is a v2 experiment, not v1. Heavy structure/layout (real tables, bboxes) is
  also v2.
- **Output**: a predicted label + score over a FROZEN label set in the model config
  (`id2label`/`label2id`), full distribution available. Exact labels: the **23
  taxonomy leaves + `other`** (24 classes). `unknown` is NOT a class; it is a
  documented confidence threshold the consumer applies. `mixed_bundle` is out of scope
  for v1.
- `category`/`form` are NOT model outputs; they are a documented lookup from `type`
  (a small table in the model card) so a standalone user derives them without this
  package.

Consequences:
- Text-only model in v1 (TF-IDF/linear baseline; Legal-XLM-R). Text extraction is the
  consumer's responsibility.
- Training data is portable `(text, type)` JSONL, no package types.
- The `type` string values are frozen public labels: finalised before training,
  stable across versions.
- Standard HF packaging + model card (input, truncation, output, threshold,
  category/form table, data, licence incl. base-model share-alike, per-class metrics
  and pilot/experimental status).
- In THIS package, `DocumentTypeDetector` is a thin adapter:
  `ParsedDocument.text -> model -> {label, score} -> DetectedDocumentType`. The
  package depends on the model by HF id; the model never depends on the package.

## Real evaluation (small, human-verified, three disjoint pools)

Real data is used only for evaluation and optional adaptation, split into three pools
that never mix:
- `real_adaptation`: optional small real fine-tune (a training condition).
- `real_dev`: thresholds, ablation, model selection, error analysis.
- `real_test`: evaluated ONCE, after every decision is frozen.

Sources give CANDIDATE labels, not gold: CUAD types come from contract names (so
name/title/text are correlated, not independent truth); EDGAR EX-2/EX-3 map to
acquisition/constitutional but include amendments and partial instruments; EDGAR
EX-10 means only "material contract" and cannot by itself separate commercial vs
employment vs financing vs IP; ContractNLI gives NDAs. Therefore:
- Every real document (adaptation, dev, AND test) is HUMAN-verified, not spot-checked
  and not LLM-voted. Inspect enough content to apply the annotation guide (a cover
  page or amendment can mislead; the opening is not always sufficient). Record
  reviewer, decision, evidence/title span, and exclusion reason for ambiguous docs. I
  assemble and pre-label; the maintainer confirms each.
- EX-10 is not used as a fine-grained label source; only human-verified rows count.

Pilot size ~15-20 real docs per class per pool is a PILOT signal, not production:
per-class confidence intervals will be wide. Production eligibility needs a real set
sized from a target CI width, with per-class release thresholds PRE-REGISTERED before
`real_test` is seen.

Network caveat: fetching CUAD/EDGAR needs the WARP/TLS workaround.

## Synthetic generation

- Generate per type via an LLM, with controlled diversity: jurisdiction, parties,
  industry, length, section ordering, formatting, drafting register, and realistic
  noise.
- Realism: prefer generate content -> render into varied PDF/DOCX/email formats ->
  re-extract, so the model does not learn clean-Markdown, class-specific heading
  shortcuts. For the pilot, direct generation with varied formatting and multiple
  extractor styles is the interim, and this shortcut risk is flagged.
- Versioned and auditable: record generator model+version, prompt/template id, seed,
  params, and critic result per document. Prompts/templates live in a registry.
- Anti-collapse: dedup + critic pass rejects near-duplicates and low-quality drafts;
  track diversity metrics (near-duplicate rate, vocabulary spread) per class.
- Measurable quality gates, defined BEFORE generation: exact + near-duplicate
  rejection thresholds; max share of any prompt/template family per class;
  title/class-name shortcut frequency cap; per-class human audit sample size;
  confusion-oriented hard negatives; TF-IDF feature inspection for synthetic-heading /
  prompt artifacts. The critic must NOT be only the generator's own model family.

## Labels and coverage

- The published v1 model trains ALL 23 leaves + `other` (a 24-output model must not
  have empty heads). The 2-3 class warm-up is an UNPUBLISHED pipeline smoke test, not
  a released model, so it never freezes a smaller public label set.
- Synthetic rows are labelled by construction; still audited by the critic pass.
- Generate broadly (all 23), but PILOT-VALIDATE only classes with real dev+test.
  - v1 pilot-validated target (8, contract-form, whole-document text):
    acquisition_agreement, commercial_agreement, ip_agreement, employment_agreement,
    nda, financing_agreement, constitutional, shareholders_agreement.
  - Experimental (15, synthetic-trained, no real eval yet; several blocked by the
    parser gap): financial_statements, financial_model, cap_table, tax_document,
    minutes, certificate, regulatory, litigation, report, information_memorandum,
    disclosure_schedule, correspondence, insurance_policy, lease_agreement,
    diligence_qa.
- OTHER / abstention are three distinct mechanisms: closed-set prediction over the 24
  labels, `other` (out-of-taxonomy, a trained class from generated + real OOD docs),
  and confidence-based `unknown` abstention (risk-coverage curve on real_dev). From
  the FIRST pilot: generate synthetic `other`, include human-verified real OOD in
  real_dev and real_test, and tune the `unknown` threshold on real_dev.

## Per-example record (JSONL)

```
{ "id", "origin": "synthetic|real",
  "text" (or "artifact_ref"),          # the actual model input, portable
  "type", "subtype",
  "extractor", "extractor_version",    # which text extractor produced `text`
  "split": "train|real_adaptation|real_dev|real_test",
  "text_sha256", "source_document_sha256", "n_chars", "n_pages",
  "org_id", "document_family_id", "parent_document_id", "content_version",
  "template_cluster_id", "jurisdiction", "language",
  "publish_text": bool, "redistributable": bool,
  # real rows:      "source","license","license_url","source_ref",
  #                 "raw_label","label_method","review_status","reviewer","guide_version"
  # synthetic rows: "generator_model","generator_version","prompt_id","seed",
  #                 "params","critic_result","output_license" }
```

Parser policy: the model is extractor-INDEPENDENT, so we do NOT mandate one parser.
We intentionally support multiple extractors, record `extractor`/`extractor_version`
per row, and report per-extractor robustness. If one document is extracted by several
extractors, all representations stay in the SAME pool and count as paired robustness
measurements, not independent test documents. PII / signatures / addresses in public
filings are handled at the rights/privacy gate before any publish. (There is no
canonical production parser yet; see Parser note.)

## Splits and contamination

- Synthetic -> `train` only. Real -> the three real pools only. Synthetic never enters
  a real pool.
- Overlap is REDUCED, not impossible: no eval doc is shown to the generator (no direct
  prompt exposure), but the base/generator model may have seen public corpora in
  pretraining. Controls:
  - dedup synthetic against real_dev/real_test by normalised exact hash AND
    near-duplicate similarity;
  - prefer real_test docs dated after the generator/base-model knowledge cutoff;
  - keep document families, amendments, parties, and templates grouped within a single
    pool.
- Freeze an immutable split manifest.

## Evaluation via ablation

For each pilot class, compare on `real_dev` (never `real_test`):
1. train on synthetic only,
2. train on synthetic + `real_adaptation` fine-tune.
This measures the realism gap and whether a little real data closes it. `real_test`
is evaluated once at the end on the single frozen final model.

## Modelling ladder

Data -> baseline -> transformer. The published model is the CHEAPEST that meets the
release gates: a calibrated linear model is publishable in its own right; the
transformer ships only if it clearly beats the baseline on the gates.
1. Floor: majority class.
2. Baseline: TF-IDF + linear (Logistic Regression / linear SVM). Strong for
   document-type; fast; interpretable. XGBoost skipped (no edge on sparse text).
3. Candidate: Legal-XLM-R, on the frozen first-512-token input (same as the
   interface). No silent truncation beyond the frozen policy.

## Metrics and release gates

Macro/weighted F1, per-class F1 WITH confidence intervals, top-3, calibration,
abstention risk-coverage, and category/form routing accuracy. Per-class thresholds are
PRE-REGISTERED before `real_test` is seen. Class status (three tiers):
- `experimental`: always review, never routed (kept in the model for observability,
  `needs_review=True`, never silently replaced by another class).
- `pilot_validated`: has real dev+test and meets its pre-registered threshold; routing
  permitted ONLY behind an explicit pilot / feature flag.
- `production_validated`: default automatic routing; requires a real eval sized from a
  target CI width, not the pilot 15-20.

## Parser note (blocks some experimental classes)

No canonical production parser exists yet: the demo parser skips tables and does not
set `mime_type`, and `ParsedDocument` has no `quality_status`. Table/scan/spreadsheet
classes (financial_statements, cap_table, financial_model) cannot get a trustworthy
real eval until this is fixed, so they stay experimental in v1.

## Contract fixes before freezing the label schema

- Drop the "category fallback on abstention" claim (category is derived from a known
  type; it cannot exist when type abstains). A separate coarse-category head is a
  later option.
- `needs_review` auto-set for UNKNOWN / MIXED_BUNDLE / experimental / low confidence.
- Experimental-label routing: the adapter keeps the predicted label for observability,
  sets `needs_review=True`, and does NOT auto-route or substitute a pilot class.
- `subtype` is descriptive only in v1 (routing uses `form`).
- MIXED_BUNDLE page-spans are out of v1 scope (no field yet).

## Codex review checklist

1. Are the three real pools genuinely disjoint, with `real_test` touched once?
2. Is every real dev/test label human-verified (not weak/LLM-voted)?
3. Is the label inventory exact (23 leaves + `other`; `unknown` threshold;
   `mixed_bundle` out of scope)?
4. Contamination: dedup synthetic vs real, cutoff preference, grouped families?
5. Is status honestly "pilot", with pre-registered thresholds and CI-based sizing for
   any "production" claim?
6. Generator anti-collapse and format-shortcut controls adequate?
7. Licensing: synthetic-output terms, base-model share-alike, real-source reuse.
8. Extractor policy: multiple extractors recorded, robustness reported.

## Build order (finishable, cheapest first)

1. This plan (conditional go from Codex).
2. Freeze scope: exact 24 labels, English-only, truncation, subtype policy, synthetic
   quality thresholds, annotation guide, and the rights/privacy policy.
3. UNPUBLISHED pipeline smoke test on 2-3 classes + `other`: small synthetic batch,
   a tiny human-verified real dev/test (including real OOD), run the baseline end to
   end. Proves the recipe cheaply before generating everything.
4. If the recipe holds, generate synthetic training data for ALL 23 leaves + `other`.
5. Assemble + human-verify real `adaptation`/`dev`/`test` for the pilot classes and
   real OOD; group by document family; freeze the immutable split manifest.
6. Baseline (majority + TF-IDF linear); pre-register and tune per-class + `unknown`
   thresholds on `real_dev` only.
7. Ablation (synthetic vs synthetic + `real_adaptation`) on `real_dev`.
8. Rights/privacy gate: confirm output terms/versions, final licences, attribution,
   redistribution + PII handling per row, before any publish.
9. Transformer if it beats the baseline; evaluate `real_test` ONCE; publish
   model/card/dataset only if pre-registered gates are met (English-only, honest
   pilot_validated status).
10. Expand real coverage toward production_validated; keep other classes experimental.

## Code (v1 scaffolding)

`training/document_type/` (run scripts from repo root):
- `labels.py` — frozen 24-label contract (23 leaves + `other`) + `id2label`; asserts
  it matches the package taxonomy on import (the mechanical check).
- `example.py` — `DocTypeExample`, the portable JSONL row; enforces type-in-labels and
  the contamination invariant (synthetic -> `train`, real -> `real_*` only).
- `preprocessing.py` — frozen input view (`document_opening`, first 512 tokens),
  shared by baseline and transformer.
- `generation_prompts.py` — versioned prompt registry + diversity axes for the pilot
  classes + `other`.
- `metrics.py` — macro/weighted/per-class F1, bootstrap CIs, top-k, majority floor.
- `baseline.py` — TF-IDF + Logistic Regression; trains on synthetic `train`, evaluates
  on `real_dev` over a fixed eval-label set (`real_test` guarded by `--allow-test`),
  asserts split-file match + verified eval rows, dumps top features per class, and
  saves the pipeline + a run manifest.
- `preflight.py` — MUST pass before training: unique ids, split-file match, hash match,
  exact + near-duplicate contamination across pools, no group spanning pools, per-class
  train support, real rows verified; writes an immutable dataset manifest.

Deferred to their build-order steps (not needed for the disposable smoke test):
- calibration + `unknown` operating point (Brier/ECE, selective-risk curve) at the
  threshold-tuning step;
- the full frozen-artifact release receipt (single-use `real_test`) at publish time;
- multiple prompt families per class + a sampling runner before BULK generation.

Not built yet: the generator runner (needs an LLM API or a manual seed batch) and the
real pools (need the CUAD/EDGAR fetch).
