"""Build the stage-5 clause-classification dataset from CUAD + LEDGAR.

Data before model. This turns two public corpora into model-ready examples
(clause text → clause type labels), split leakage-free by source contract.

    CUAD   → deal-critical POSITIVES. Each answer span is expanded to its
             containing sentence; (contract, sentence) pairs are merged so a
             sentence carrying two clause types becomes one multi-label example.
    LEDGAR → the ~5 overlapping deal types (reinforcement) + a capped pool of
             realistic NEGATIVES (everything else → UNKNOWN/OTHER).

Output: data/clause_classification/{train,val,test}.jsonl  (gitignored)

Run:  poetry run python training/clause_classification/build_clause_dataset.py
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

from clause_example import ClauseExample
from datasets import load_dataset
from taxonomy_mapping import map_ledgar_label

from deal_document_intelligence.contracts import ClauseType

_CLAUSE_RE = re.compile(r'related to "(.+?)"')


class ClauseDatasetBuilder:
    CUAD_ID = "theatticusproject/cuad-qa"
    CUAD_REV = "refs/convert/parquet"
    LEDGAR_ID = "coastalcph/lex_glue"
    LEDGAR_CFG = "ledgar"

    def __init__(
        self, out_dir: Path = Path("data/clause_classification"), other_max: int = 15000
    ) -> None:
        self.out_dir = out_dir
        self.other_max = other_max

    def build(self) -> list[ClauseExample]:
        examples = self._from_cuad() + self._from_ledgar()
        for ex in examples:
            ex.split = self._split_for(ex.doc_id)
        self._write(examples)
        self._report(examples)
        return examples

    # ---- CUAD → deal-critical positives (sentence-level, multi-label) -------
    def _from_cuad(self) -> list[ClauseExample]:
        groups: dict[tuple[str, str], set[ClauseType]] = {}
        for split in ("train", "test"):
            ds = load_dataset(self.CUAD_ID, split=split, revision=self.CUAD_REV)
            for row in ds:
                answers = row["answers"]
                if not answers["text"]:
                    continue
                ctype = self._clause_type(row["question"])
                if ctype is None:
                    continue
                context, title = row["context"], row["title"]
                for text, start in zip(answers["text"], answers["answer_start"]):
                    sentence = self._sentence_at(context, start, start + len(text))
                    if sentence:
                        groups.setdefault((title, sentence), set()).add(ctype)
        return [
            ClauseExample(
                text=sentence, labels=sorted(types, key=lambda t: t.value),
                source="cuad", doc_id=title,
            )
            for (title, sentence), types in groups.items()
        ]

    # ---- LEDGAR → overlap types + capped OTHER negatives --------------------
    def _from_ledgar(self) -> list[ClauseExample]:
        ds = load_dataset(self.LEDGAR_ID, self.LEDGAR_CFG, split="train")
        names = ds.features["label"].names
        examples: list[ClauseExample] = []
        n_other = 0
        for i, row in enumerate(ds):
            ctype = map_ledgar_label(names[row["label"]])
            if ctype == ClauseType.UNKNOWN:
                if n_other >= self.other_max:
                    continue
                n_other += 1
            examples.append(ClauseExample(
                text=row["text"], labels=[ctype], source="ledgar", doc_id=f"ledgar-{i}",
            ))
        return examples

    # ---- helpers ------------------------------------------------------------
    @staticmethod
    def _clause_type(question: str) -> ClauseType | None:
        m = _CLAUSE_RE.search(question)
        if not m:
            return None
        try:
            return ClauseType(m.group(1))
        except ValueError:
            return None

    @staticmethod
    def _sentence_at(context: str, start: int, end: int) -> str:
        left = max(context.rfind(". ", 0, start), context.rfind("\n", 0, start))
        s = left + 2 if left != -1 else 0
        rights = [r for r in (context.find(". ", end), context.find("\n", end)) if r != -1]
        e = (min(rights) + 1) if rights else len(context)
        return " ".join(context[s:e].split())

    @staticmethod
    def _split_for(doc_id: str) -> str:
        bucket = int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % 10
        return "test" if bucket == 0 else "val" if bucket == 1 else "train"

    def _write(self, examples: list[ClauseExample]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for split in ("train", "val", "test"):
            path = self.out_dir / f"{split}.jsonl"
            rows = [e.model_dump_json() for e in examples if e.split == split]
            path.write_text("\n".join(rows) + ("\n" if rows else ""))

    def _report(self, examples: list[ClauseExample]) -> None:
        by_split = Counter(e.split for e in examples)
        by_source = Counter(e.source for e in examples)
        multi = sum(1 for e in examples if len(e.labels) > 1)
        label_freq = Counter(t for e in examples for t in e.labels)
        print(f"\n=== CLAUSE DATASET ===  {len(examples):,} examples")
        print(f"splits : {dict(by_split)}")
        print(f"source : {dict(by_source)}")
        print(f"multi-label examples: {multi:,}")
        other = label_freq.pop(ClauseType.UNKNOWN, 0)
        print(f"OTHER (UNKNOWN) examples: {other:,}")
        print(f"deal-type positives: {sum(label_freq.values()):,} across {len(label_freq)} types")
        print("top clause types:")
        for ctype, n in label_freq.most_common(12):
            print(f"  {n:>5}  {ctype.value}")


if __name__ == "__main__":
    ClauseDatasetBuilder().build()
