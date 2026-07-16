"""Bounding box for visual (click-to-highlight) evidence."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """A bounding box on a page."""

    page: int = Field(ge=1, description="1-based page number")
    x0: float
    y0: float
    x1: float
    y1: float
