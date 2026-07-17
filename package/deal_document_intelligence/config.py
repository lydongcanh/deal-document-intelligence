"""Project configuration.

Deliberately minimal for now: just the standard directory layout (all
gitignored) and the pipeline version. When we need environment-driven settings
(model paths, API keys, LLM endpoints) we'll graduate to pydantic-settings.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    data_dir: Path = Path("artifacts/data")        # raw + processed datasets
    models_dir: Path = Path("artifacts/models")    # local model checkpoints
    outputs_dir: Path = Path("artifacts/outputs")  # run logs, predictions, results
    cache_dir: Path = Path("artifacts/.cache")     # HuggingFace / library caches
    pipeline_version: str = "0.1.0"


settings = Settings()
