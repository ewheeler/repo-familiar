import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from .analysis import analyze


def reproduce(config_path: str, output_path: Path) -> str:
    rendered = analyze(config_path).model_dump_json(indent=2) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce the exemplar analysis")
    parser.add_argument("--config", default="config/default.toml")
    parser.add_argument("--output", type=Path, default=Path("artifacts/analysis.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    first = reproduce(args.config, args.output)
    if args.check:
        with TemporaryDirectory() as first_dir, TemporaryDirectory() as second_dir:
            first_check = reproduce(args.config, Path(first_dir) / "analysis.json")
            second_check = reproduce(args.config, Path(second_dir) / "analysis.json")
        if first != first_check or first_check != second_check:
            raise SystemExit("Reproduction outputs differ")


if __name__ == "__main__":
    main()
