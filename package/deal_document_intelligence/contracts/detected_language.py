"""DetectedLanguage — output of the language stage.

The detected language of a document, with a confidence (it is a prediction, so
it can be wrong). Kept separate from `ParsedDocument` so `parse()` never returns
a document with this field silently empty. Document-type detection is a separate
stage with its own result, so it is deliberately not here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DetectedLanguage(BaseModel):
    language: str | None = Field(default=None, description="ISO 639-1, e.g. 'en'")
    confidence: float | None = Field(default=None, ge=0, le=1)
