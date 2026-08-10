from pathlib import Path

from pydantic import BaseModel, Field


class AnalysisConfig(BaseModel):
    input_path: Path
    minimum_value: int = Field(ge=0)
    category: str = Field(min_length=1)


class AnalysisResult(BaseModel):
    category: str
    count: int = Field(ge=0)
    total: int
    average: float
    input_sha256: str
    config_sha256: str
