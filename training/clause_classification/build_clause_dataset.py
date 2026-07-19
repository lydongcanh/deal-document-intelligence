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
        self, out_dir: Path = Path("artifacts/data/clause_classification"), other_max: int = 15000
    ) -> None:
        self.out_dir = out_dir
        self.other_max = other_max

    def build(self) -> list[ClauseExample]:
        examples = self._from_cuad() + self._from_ledgar()
        for ex in examples:
            ex.split = self._split_for(ex.doc_id)
        examples = self._dedup_across_splits(examples)
        self._write(examples)
        self._report(examples)
        return examples

    @staticmethod
    def _dedup_across_splits(examples: list[ClauseExample]) -> list[ClauseExample]:
        """Keep each exact text in ONE split only (train > val > test priority).

        Splitting by source contract stops clauses of the *same* contract leaking
        across splits, but identical boilerplate sentences recur across *different*
        contracts (e.g. "governed by the laws of the State of Delaware"), landing
        the same text in multiple splits. This keeps each exact text once, in the
        highest-priority split it appears in, and **merges the labels** of all its
        duplicates so conflicting/partial annotations aren't silently dropped.

        Known limitation: the train>val>test priority preferentially removes dupes
        from eval sets (a small selection bias — a few dozen rows). Stronger future
        work: group near-duplicates and contract families, assign each whole group
        to one split, and persist a split manifest.
        """
        priority = {"train": 0, "val": 1, "test": 2}
        best_split: dict[str, str] = {}
        labels_by_text: dict[str, set] = {}
        for ex in examples:
            if ex.text not in best_split or priority[ex.split] < priority[best_split[ex.text]]:
                best_split[ex.text] = ex.split
            labels_by_text.setdefault(ex.text, set()).update(ex.labels)
        kept, emitted = [], set()
        for ex in examples:
            if ex.text in emitted or ex.split != best_split[ex.text]:
                continue
            emitted.add(ex.text)
            ex.labels = sorted(labels_by_text[ex.text], key=lambda t: t.value)
            kept.append(ex)
        return kept

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
        """Expand [start:end] to its surrounding sentence.

        The boundary *before* the span may be ". " (2 chars) or "\\n" (1 char);
        we must step past exactly the matched boundary's length, or we clip the
        first character of the sentence (the bug that truncated "Supply"→"upply").
        s <= start and e >= end always, so the answer span stays contained.
        """
        dot = context.rfind(". ", 0, start)
        nl = context.rfind("\n", 0, start)
        if dot >= nl:
            s = dot + 2 if dot != -1 else 0  # ". " is 2 chars (or no boundary → 0)
        else:
            s = nl + 1                        # "\n" is 1 char
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
