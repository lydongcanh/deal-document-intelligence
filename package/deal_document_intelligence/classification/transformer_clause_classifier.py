"""A Classifier backed by a fine-tuned transformer checkpoint (stage 5).

Loads a multi-label sequence-classification model (e.g. the Legal-XLM-R model
trained in `training/clause_classification/`) and assigns clause types. This is a
differentiator model, so it lives IN the package — but torch/transformers are an
OPTIONAL dependency: `pip install deal-document-intelligence[classification]`.
The import of torch/transformers is deferred to construction so that core
installs (contracts + interfaces + pipeline) never need them.

The model is multi-label; `ClauseUnit.clause_type` is the primary (top) type,
and the full scored multi-label set is exposed as typed `clause.predictions`
(`list[ClausePrediction]`).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClausePrediction,
    ClauseType,
    ClauseUnit,
)


class TransformerClauseClassifier:
    def __init__(
        self,
        model_dir: str | Path = "artifacts/models/clause_classifier",
        threshold: float | None = None,
        max_length: int = 256,
        batch_size: int = 32,
        device: str | None = None,
    ) -> None:
        import torch  # deferred: only needed for this differentiator model
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        # Accept a local checkpoint dir OR a HuggingFace Hub id (from_pretrained
        # handles both). A bare "org/model" is a Hub id, NOT a local path — only
        # a value that clearly points at the filesystem (a Path, a ./ ../ / ~
        # prefix, or an existing path) is treated as local and checked to exist.
        model_ref = str(model_dir)
        is_local = (
            isinstance(model_dir, Path)
            or model_ref.startswith(("./", "../", "/", "~"))
            or Path(model_ref).exists()
        )
        if is_local and not Path(model_ref).exists():
            raise FileNotFoundError(
                f"clause-classifier not found at {model_ref!r}. Train it with "
                "training/clause_classification/train.py, or pass a valid local path "
                "or a HuggingFace Hub id (org/model)."
            )
        if max_length <= 0 or batch_size <= 0:
            raise ValueError("max_length and batch_size must be positive")

        self.model_dir = Path(model_ref)
        self._torch = torch
        self.max_length = max_length
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(model_ref)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_ref)
        if device is None:  # prefer CUDA, then Apple MPS, then CPU
            device = (
                "cuda" if torch.cuda.is_available()
                else "mps" if torch.backends.mps.is_available()
                else "cpu"
            )
        self.device = device
        self.model.to(self.device).eval()

        if threshold is None:
            tpath = self.model_dir / "threshold.json"
            threshold = json.loads(tpath.read_text())["threshold"] if tpath.exists() else 0.5
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        self.threshold = threshold

        id2label = self.model.config.id2label
        self.labels = [
            ClauseType(id2label[i] if i in id2label else id2label[str(i)])
            for i in range(self.model.config.num_labels)
        ]
        if len(set(self.labels)) != len(self.labels):
            raise ValueError("model id2label contains duplicate clause types")

        # Optional PER-LABEL thresholds (tuned on val — see tune_thresholds.py).
        # Each clause type gets its own precision/recall cutoff; any label not
        # listed falls back to the single scalar `threshold`. This is how we stop
        # trigger-happy types over-firing while keeping rare types sensitive.
        # Values are validated: finite and within [0, 1], else ignored.
        self.label_thresholds: dict[ClauseType, float] = {}
        lpath = self.model_dir / "thresholds.json"
        if lpath.exists():
            for name, value in json.loads(lpath.read_text()).items():
                try:
                    v, ct = float(value), ClauseType(name)
                except (ValueError, TypeError):
                    continue
                if math.isfinite(v) and 0.0 <= v <= 1.0:
                    self.label_thresholds[ct] = v

        # Modest provenance. TODO(prod): also stamp checkpoint hash, base-model
        # revision, and dataset/split version for full legal-grade auditability.
        per_label = "per-label" if self.label_thresholds else f"{self.threshold}"
        self.version = f"clause-clf@{self.model_dir.name}|thr={per_label}|max_len={self.max_length}"

    def _threshold_for(self, label: ClauseType) -> float:
        return self.label_thresholds.get(label, self.threshold)

    def classify(
        self, clauses: list[ClauseUnit], document: CanonicalDocument
    ) -> list[ClauseUnit]:
        torch = self._torch
        with torch.no_grad():
            for start in range(0, len(clauses), self.batch_size):
                batch = clauses[start:start + self.batch_size]
                enc = self.tokenizer(
                    [c.text for c in batch], truncation=True, max_length=self.max_length,
                    padding=True, return_tensors="pt",
                ).to(self.device)
                probs = torch.sigmoid(self.model(**enc).logits).cpu().tolist()
                for clause, row in zip(batch, probs):
                    self._assign(clause, row)
        return clauses

    def _assign(self, clause: ClauseUnit, probs: list[float]) -> None:
        # Deal types above their per-label cutoff. OTHER is never a positive:
        # a clause is OTHER only when nothing fires (derived below).
        scored = sorted(
            ((self.labels[j], p) for j, p in enumerate(probs)
             if self.labels[j] != ClauseType.UNKNOWN
             and p >= self._threshold_for(self.labels[j])),
            key=lambda x: -x[1],
        )
        if scored:
            clause.clause_type, best = scored[0]
        else:
            clause.clause_type, best = ClauseType.UNKNOWN, None  # derived OTHER
        clause.classification_confidence = round(best, 4) if best is not None else None
        clause.model_version = self.version
        clause.predictions = [
            ClausePrediction(clause_type=label, score=round(p, 4)) for label, p in scored
        ]
