"""One dataset row: the portable `(text, type)` example plus its provenance.

Invariants enforced here so a bad row cannot silently enter the dataset:
  1. `type` is one of the 24 frozen model labels (23 leaves + `other`).
  2. Contamination guard: synthetic rows live ONLY in `train`; real rows live ONLY in
     a real_* pool.
  3. Origin-dependent provenance: synthetic rows carry generator provenance; real rows
     carry source/licence provenance AND are human-verified. Missing provenance is a
     hard error, not an optional field.
  4. `text_sha256` is always computed from `text`, so it is present and correct.

Cross-row checks (unique ids, dedup, grouping, split-file match, class support) live in
`preflight.py`, which must pass before any training.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from labels import MODEL_LABELS
from preprocessing import sha256


class Origin(StrEnum):
    SYNTHETIC = "synthetic"
    REAL = "real"


class Split(StrEnum):
    TRAIN = "train"  # synthetic only
    REAL_ADAPTATION = "real_adaptation"  # optional real fine-tune
    REAL_DEV = "real_dev"  # thresholds, ablation, model selection
    REAL_TEST = "real_test"  # touched once, at the very end


class ReviewStatus(StrEnum):
    VERIFIED = "verified"
    PENDING = "pending"
    EXCLUDED = "excluded"


class LabelMethod(StrEnum):
    HUMAN_VERIFIED = "human_verified"
    SILVER_CANDIDATE = "silver_candidate"


_REAL_POOLS = {Split.REAL_ADAPTATION, Split.REAL_DEV, Split.REAL_TEST}
_REQUIRED_SYNTHETIC = ("generator_model", "generator_version", "prompt_id", "critic_result", "output_license")
_REQUIRED_REAL = ("source", "license", "license_url", "source_ref", "raw_label",
                  "reviewer", "guide_version", "source_document_sha256")


class DocTypeExample(BaseModel):
    id: str
    origin: Origin
    text: str  # the actual model input (plain or light-Markdown)
    type: str  # one of MODEL_LABELS
    split: Split

    subtype: str | None = None
    extractor: str | None = None
    extractor_version: str | None = None

    # dedup / grouping provenance (checked in preflight)
    text_sha256: str | None = None
    source_document_sha256: str | None = None
    n_chars: int | None = None
    n_pages: int | None = None
    org_id: str | None = None
    document_family_id: str | None = None
    parent_document_id: str | None = None
    content_version: str | None = None
    template_cluster_id: str | None = None
    jurisdiction: str | None = None
    language: str = "en"

    # rights / privacy
    publish_text: bool = False
    redistributable: bool = False

    # real rows
    source: str | None = None
    license: str | None = None
    license_url: str | None = None
    source_ref: str | None = None
    raw_label: str | None = None
    label_method: LabelMethod | None = None
    review_status: ReviewStatus | None = None
    reviewer: str | None = None
    guide_version: str | None = None

    # synthetic rows
    generator_model: str | None = None
    generator_version: str | None = None
    prompt_id: str | None = None
    seed: int | None = None
    params: dict = Field(default_factory=dict)
    critic_result: str | None = None
    output_license: str | None = None

    @model_validator(mode="after")
    def _check(self) -> DocTypeExample:
        if not self.text.strip():
            raise ValueError("empty text")
        if self.type not in MODEL_LABELS:
            raise ValueError(f"type {self.type!r} is not a v1 model label")
        self._check_contamination()
        self._check_provenance()
        self._fill_hash()
        return self

    def _check_contamination(self) -> None:
        if self.origin is Origin.SYNTHETIC and self.split is not Split.TRAIN:
            raise ValueError("synthetic rows must be in the train split")
        if self.origin is Origin.REAL and self.split not in _REAL_POOLS:
            raise ValueError("real rows must be in a real_* split")

    def _check_provenance(self) -> None:
        if self.origin is Origin.SYNTHETIC:
            missing = [f for f in _REQUIRED_SYNTHETIC if getattr(self, f) is None]
            if self.seed is None:
                missing.append("seed")
            if missing:
                raise ValueError(f"synthetic row missing provenance: {missing}")
            return
        missing = [f for f in _REQUIRED_REAL if getattr(self, f) is None]
        if missing:
            raise ValueError(f"real row missing provenance: {missing}")
        if self.review_status is not ReviewStatus.VERIFIED:
            raise ValueError("a stored real row must be human-verified (review_status=verified)")
        if self.label_method is not LabelMethod.HUMAN_VERIFIED:
            raise ValueError("a stored real row must have label_method=human_verified")

    def _fill_hash(self) -> None:
        computed = sha256(self.text)
        if self.text_sha256 is None:
            self.text_sha256 = computed
        elif self.text_sha256 != computed:
            raise ValueError("text_sha256 does not match text")

    def eval_ready(self) -> bool:
        """A real row usable for evaluation: human-verified."""
        return self.origin is Origin.REAL and self.review_status is ReviewStatus.VERIFIED
