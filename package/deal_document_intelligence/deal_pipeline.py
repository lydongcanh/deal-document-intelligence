"""Deal-level pipeline (stage 9b) — runs the single-document Pipeline over every
document in a deal, then aggregates the per-document results into
`DealIntelligence` (with cross-document entity resolution).

Deal-level is first-class: this is how a whole data room, not one file, becomes
structured intelligence.
"""

from __future__ import annotations

from pathlib import Path

from deal_document_intelligence.aggregation.deal_aggregator import DealAggregator
from deal_document_intelligence.contracts import DealIntelligence
from deal_document_intelligence.pipeline import Pipeline


class DealPipeline:
    def __init__(self, pipeline: Pipeline, aggregator: DealAggregator) -> None:
        self.pipeline = pipeline
        self.aggregator = aggregator

    def run(self, sources: list[Path]) -> DealIntelligence:
        documents = [self.pipeline.run(source) for source in sources]
        return self.aggregator.aggregate(documents)
