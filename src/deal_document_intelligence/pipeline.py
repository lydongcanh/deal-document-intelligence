"""Pipeline orchestration — composes stage implementations via their interfaces.

The stages are injected as objects satisfying the per-stage Protocols (defined
in each stage package). This is what lets a walking-skeleton pipeline (library
baselines) and a production pipeline (custom models) be the same class with
different constructor arguments — and lets consumers bring their own parser
(docling/AWS/Azure/…) without the package depending on any of them.

    stages 1-3  → Parser      (source file → CanonicalDocument)
    stage 4     → Segmenter   (document → clauses)
    stage 5     → Classifier  (clauses → typed clauses)
    stage 6     → Extractor   (document + clauses → entities/obligations/events)
    stage 7     → Linker      (everything → relations)
    stage 8     → assembled here into an EvidenceBackedResult
    stage 9     → applications consume the result; not part of this pipeline
"""

from __future__ import annotations

from pathlib import Path

from deal_document_intelligence.classification.classifier import Classifier
from deal_document_intelligence.contracts import EvidenceBackedResult
from deal_document_intelligence.extraction.extractor import Extractor
from deal_document_intelligence.linking.linker import Linker
from deal_document_intelligence.parsing.parser import Parser
from deal_document_intelligence.segmentation.segmenter import Segmenter


class Pipeline:
    def __init__(
        self,
        parser: Parser,
        segmenter: Segmenter,
        classifier: Classifier,
        extractor: Extractor,
        linker: Linker,
        pipeline_version: str = "0.1.0",
    ) -> None:
        self.parser = parser
        self.segmenter = segmenter
        self.classifier = classifier
        self.extractor = extractor
        self.linker = linker
        self.pipeline_version = pipeline_version

    def run(self, source: Path) -> EvidenceBackedResult:
        document = self.parser.parse(source)
        clauses = self.segmenter.segment(document)
        clauses = self.classifier.classify(clauses, document)
        extractions = self.extractor.extract(document, clauses)
        relations = self.linker.link(document, clauses, extractions)
        return EvidenceBackedResult(
            doc_id=document.doc_id,
            document=document,
            clauses=clauses,
            entities=extractions.entities,
            obligations=extractions.obligations,
            events=extractions.events,
            relations=relations,
            pipeline_version=self.pipeline_version,
        )
