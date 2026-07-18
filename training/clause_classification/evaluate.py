"""Evaluate baseline predictors on the test split, using the shared metrics.

Scores any predictor mapping clause text → set[ClauseType]. The trained model is
scored the same way in evaluate_model.py — both import scoring from `metrics`.

Run:  poetry run python training/clause_classification/evaluate.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from metrics import OTHER, report, score

from deal_document_intelligence.contracts import ClauseType

DATA = Path("artifacts/data/clause_classification")
Predictor = Callable[[str], set[ClauseType]]
Example = tuple[str, set[ClauseType]]


def load_split(split: str = "test") -> list[Example]:
    examples: list[Example] = []
    for line in (DATA / f"{split}.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        examples.append((row["text"], {ClauseType(x) for x in row["labels"]}))
    return examples


def score_predictor(predictor: Predictor, examples: list[Example]) -> dict:
    gold = [labels for _, labels in examples]
    pred = [predictor(text) for text, _ in examples]
    return score(gold, pred)


def all_other_baseline(text: str) -> set[ClauseType]:
    return {OTHER}


_KEYWORDS: dict[str, ClauseType] = {
    "governing law": ClauseType.GOVERNING_LAW,
    "insurance": ClauseType.INSURANCE,
    "audit": ClauseType.AUDIT_RIGHTS,
    "change of control": ClauseType.CHANGE_OF_CONTROL,
    "change in control": ClauseType.CHANGE_OF_CONTROL,
    "non-compete": ClauseType.NON_COMPETE,
    "not to compete": ClauseType.NON_COMPETE,
    "exclusiv": ClauseType.EXCLUSIVITY,
    "renew": ClauseType.RENEWAL_TERM,
    "effective date": ClauseType.EFFECTIVE_DATE,
    "expiration": ClauseType.EXPIRATION_DATE,
    "assign": ClauseType.ANTI_ASSIGNMENT,
    "license": ClauseType.LICENSE_GRANT,
    "warrant": ClauseType.WARRANTY_DURATION,
    "minimum": ClauseType.MINIMUM_COMMITMENT,
    "most favored": ClauseType.MOST_FAVORED_NATION,
    "solicit": ClauseType.NO_SOLICIT_OF_EMPLOYEES,
    "disparage": ClauseType.NON_DISPARAGEMENT,
    "escrow": ClauseType.SOURCE_CODE_ESCROW,
    "by and between": ClauseType.PARTIES,
    "for convenience": ClauseType.TERMINATION_FOR_CONVENIENCE,
}


def keyword_baseline(text: str) -> set[ClauseType]:
    low = text.lower()
    hits = {ctype for kw, ctype in _KEYWORDS.items() if kw in low}
    return hits or {OTHER}


if __name__ == "__main__":
    examples = load_split("test")
    print(f"test examples: {len(examples):,}")
    report("baseline: all-OTHER (floor)", score_predictor(all_other_baseline, examples))
    report("baseline: keyword", score_predictor(keyword_baseline, examples))
