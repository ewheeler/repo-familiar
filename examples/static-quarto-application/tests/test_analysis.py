from pathlib import Path

from static_quarto_application.analysis import analyze
from static_quarto_application.reproduce import reproduce


def test_analysis_has_known_result() -> None:
    result = analyze()

    assert result.category == "all"
    assert result.count == 4
    assert result.total == 82
    assert result.average == 20.5


def test_reproduction_is_deterministic(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = reproduce("config/default.toml", first_dir / "analysis.json")
    second = reproduce("config/default.toml", second_dir / "analysis.json")

    assert first == second
    assert first_dir != second_dir
