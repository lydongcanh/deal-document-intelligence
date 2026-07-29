"""Single-document pipeline — composes the stage implementations via their
interfaces and produces one document's `EvidenceBackedResult` (stage 9a).

Stages are injected as objects satisfying the per-stage Protocols. A
walking-skeleton pipeline (library baselines) and a production pipeline (custom
models) are the same class with different constructor arguments; consumers bring
their own parser/language-detector without the package depending on any vendor.

    1-2  Parser           source file → ParsedDocument
    3    LanguageDetector document → DetectedLanguage
    4    Segmenter        document → clauses
    5    Classifier       clauses → typed clauses
    6    EntityExtractor  document + clauses → entities
    7    RelationExtractor entities → obligations/events/relations
    8    Resolver         normalise values + resolve aliases
    9a   assembled here into an EvidenceBackedResult
"""

from __future__ import annotations

from pathlib import Path

from deal_document_intelligence.contracts import EvidenceBackedResult
from deal_document_intelligence.integrity_error import IntegrityError
from deal_document_intelligence.interfaces import (
    Classifier,
    EntityExtractor,
    LanguageDetector,
    Parser,
    RelationExtractor,
    Resolver,
    Segmenter,
)


class Pipeline:
    def __init__(
        self,
        parser: Parser,
        language_detector: LanguageDetector,
        segmenter: Segmenter,
        classifier: Classifier,
        entity_extractor: EntityExtractor,
        relation_extractor: RelationExtractor,
        resolver: Resolver,
        pipeline_version: str = "0.1.0",
        validation: str = "warn",
    ) -> None:
        if validation not in ("off", "warn", "strict"):
            raise ValueError("validation must be 'off', 'warn', or 'strict'")
        self.parser = parser
        self.language_detector = language_detector
        self.segmenter = segmenter
        self.classifier = classifier
        self.entity_extractor = entity_extractor
        self.relation_extractor = relation_extractor
        self.resolver = resolver
        self.pipeline_version = pipeline_version
        self.validation = validation  # "off" | "warn" (record issues) | "strict" (raise)

    def run(self, source: Path) -> EvidenceBackedResult:
        document = self.parser.parse(source)
        # Detection is a separate object now; thread it into stages that need
        # the language as we build them.
        language = self.language_detector.detect(document)
        clauses = self.segmenter.segment(document)
        clauses = self.classifier.classify(clauses, document)
        entities = self.entity_extractor.extract(document, clauses)
        rel = self.relation_extractor.extract(document, clauses, entities)
        entities = self.resolver.resolve(document, entities)
        result = EvidenceBackedResult(
            doc_id=document.doc_id,
            document=document,
            language=language,
            clauses=clauses,
            entities=entities,
            obligations=rel.obligations,
            events=rel.events,
            relations=rel.relations,
            pipeline_version=self.pipeline_version,
        )
        if self.validation != "off":
            issues = result.validate_integrity()
            result.meta["validation_issues"] = [i.model_dump() for i in issues]
            if self.validation == "strict" and issues:
                raise IntegrityError(issues)
        return result
