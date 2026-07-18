"""Fine-tune a multilingual encoder for multi-label clause classification.

Default model: Legal-XLM-RoBERTa-base (legal + multilingual). Labels are the 41
CUAD deal types + OTHER (ClauseType.UNKNOWN) = 42, trained as multi-label
(sigmoid + BCE). Tracks macro-F1 over the 41 deal types — the baseline to beat
is 0.162 (see docs/clause_classification.md).

    # quick loop validation (small subset, 1 epoch)
    poetry run python training/clause_classification/train.py --smoke

    # full run
    poetry run python training/clause_classification/train.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from datasets import Dataset
from sklearn.metrics import f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    set_seed,
)

from deal_document_intelligence.contracts import ClauseType

DATA = Path("artifacts/data/clause_classification")
LABELS = list(ClauseType)  # 41 deal types + UNKNOWN(=OTHER) = 42
L2I = {label: i for i, label in enumerate(LABELS)}
DEAL_IDX = [i for i, label in enumerate(LABELS) if label != ClauseType.UNKNOWN]


def _load(split: str, limit: int | None) -> tuple[list[str], list[list[float]]]:
    texts, vectors = [], []
    for line in (DATA / f"{split}.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        vec = [0.0] * len(LABELS)
        for name in row["labels"]:
            vec[L2I[ClauseType(name)]] = 1.0
        texts.append(row["text"])
        vectors.append(vec)
        if limit and len(texts) >= limit:
            break
    return texts, vectors


def _compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    probs = 1.0 / (1.0 + np.exp(-logits))
    preds = (probs > 0.5).astype(int)
    per = f1_score(labels, preds, average=None, zero_division=0)
    # micro over the deal columns only (exclude OTHER), matching metrics.py
    return {
        "micro_f1": f1_score(labels[:, DEAL_IDX], preds[:, DEAL_IDX],
                             average="micro", zero_division=0),
        "macro_deal_f1": float(np.mean([per[i] for i in DEAL_IDX])),
    }


def _sweep_threshold(logits, labels) -> tuple[float, float]:
    """Pick the decision threshold that maximises macro-F1 over deal types on val.

    Multi-label models with rare classes rank positives well before their sigmoid
    outputs cross 0.5, so a fixed 0.5 badly understates them — tune it instead.
    """
    probs = 1.0 / (1.0 + np.exp(-logits))
    best_t, best_f = 0.5, -1.0
    for t in [round(0.05 * k, 2) for k in range(1, 11)]:  # 0.05 … 0.50
        preds = (probs > t).astype(int)
        per = f1_score(labels, preds, average=None, zero_division=0)
        f = float(np.mean([per[i] for i in DEAL_IDX]))
        if f > best_f:
            best_f, best_t = f, t
    return best_t, best_f


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="joelniklaus/legal-xlm-roberta-base")
    ap.add_argument("--out", default="artifacts/models/clause_classifier")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--smoke", action="store_true", help="tiny subset + 1 epoch")
    args = ap.parse_args()

    set_seed(42)
    train_limit = 1500 if args.smoke else None
    val_limit = 500 if args.smoke else None
    epochs = 1.0 if args.smoke else args.epochs

    print(f"model={args.model}  smoke={args.smoke}  epochs={epochs}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=len(LABELS),
        problem_type="multi_label_classification",
        id2label={i: label.value for i, label in enumerate(LABELS)},
        label2id={label.value: i for i, label in enumerate(LABELS)},
    )

    def build(split: str, limit: int | None) -> Dataset:
        texts, vectors = _load(split, limit)
        ds = Dataset.from_dict({"text": texts, "labels": vectors})
        return ds.map(
            lambda b: tokenizer(b["text"], truncation=True, max_length=args.max_len),
            batched=True, remove_columns=["text"],
        )

    train_ds, val_ds = build("train", train_limit), build("val", val_limit)
    print(f"train={len(train_ds)}  val={len(val_ds)}")

    targs = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_deal_f1",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        fp16=False,  # MPS: keep fp32
    )
    trainer = Trainer(
        model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds,
        data_collator=DataCollatorWithPadding(tokenizer), compute_metrics=_compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()
    print("\n=== final validation metrics (threshold=0.5) ===")
    print(f"micro_f1       : {metrics['eval_micro_f1']:.3f}")
    print(f"macro_deal_f1  : {metrics['eval_macro_deal_f1']:.3f}")

    # tune the decision threshold on val, then report at the best threshold
    pred = trainer.predict(val_ds)
    best_t, best_f = _sweep_threshold(pred.predictions, pred.label_ids)
    print(f"best threshold : {best_t}  → macro_deal_f1 {best_f:.3f}  (baseline floor: 0.162)")

    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    Path(args.out, "threshold.json").write_text(json.dumps({"threshold": best_t}))
    print(f"\nsaved model → {args.out}")


if __name__ == "__main__":
    main()
