import tomllib
from pathlib import Path

import polars as pl

from .models import AnalysisConfig, AnalysisResult
from .provenance import sha256_file


def analysis_config(
    config_path: str,
    category_override: str | None,
    minimum_value_override: int | None,
) -> AnalysisConfig:
    with Path(config_path).open("rb") as config_file:
        config = AnalysisConfig.model_validate(tomllib.load(config_file))
    updates: dict[str, object] = {}
    if category_override is not None:
        updates["category"] = category_override
    if minimum_value_override is not None:
        updates["minimum_value"] = minimum_value_override
    return config.model_copy(update=updates)


def observations(analysis_config: AnalysisConfig) -> pl.LazyFrame:
    return pl.scan_csv(analysis_config.input_path)


def selected_observations(
    observations: pl.LazyFrame,
    analysis_config: AnalysisConfig,
) -> pl.LazyFrame:
    selected = observations.filter(pl.col("value") >= analysis_config.minimum_value)
    if analysis_config.category != "all":
        selected = selected.filter(pl.col("category") == analysis_config.category)
    return selected


def summary(selected_observations: pl.LazyFrame) -> dict[str, int | float]:
    row = (
        selected_observations.select(
            pl.len().alias("count"),
            pl.col("value").sum().alias("total"),
            pl.col("value").mean().alias("average"),
        )
        .collect()
        .row(0, named=True)
    )
    return {
        "count": int(row["count"]),
        "total": int(row["total"] or 0),
        "average": round(float(row["average"] or 0.0), 6),
    }


def analysis_result(
    summary: dict[str, int | float],
    analysis_config: AnalysisConfig,
    config_path: str,
) -> AnalysisResult:
    return AnalysisResult(
        category=analysis_config.category,
        count=int(summary["count"]),
        total=int(summary["total"]),
        average=float(summary["average"]),
        input_sha256=sha256_file(analysis_config.input_path),
        config_sha256=sha256_file(Path(config_path)),
    )
