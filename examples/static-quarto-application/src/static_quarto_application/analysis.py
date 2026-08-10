from hamilton import driver

from . import dataflow
from .models import AnalysisResult


def analyze(
    config_path: str = "config/default.toml",
    *,
    category: str | None = None,
    minimum_value: int | None = None,
) -> AnalysisResult:
    graph = driver.Builder().with_modules(dataflow).build()
    result = graph.execute(
        ["analysis_result"],
        inputs={
            "config_path": config_path,
            "category_override": category,
            "minimum_value_override": minimum_value,
        },
    )
    analysis_result = result["analysis_result"]
    if not isinstance(analysis_result, AnalysisResult):
        raise TypeError("Hamilton returned an unexpected analysis result")
    return analysis_result
