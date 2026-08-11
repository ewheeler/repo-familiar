from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import re
import shlex
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from repo_familiar.cli import (
    PROFILE_FAMILY_COMMANDS,
    build_parser,
    main,
)
from repo_familiar.generator import GenerationOptions, list_templates
from repo_familiar.metadata import SELECTED_OPTION_KEYS

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
REPO_ROOT = DOCS_DIR.parent
QUARTO_CONFIG = DOCS_DIR / "_quarto.yml"
README = REPO_ROOT / "README.md"
ROOT_PLAN = REPO_ROOT / "PLAN.md"
INDEX_DOC = DOCS_DIR / "index.qmd"
GETTING_STARTED_DOC = DOCS_DIR / "tutorials/generate-first-repository.qmd"
USAGE_DOC = DOCS_DIR / "how-to/generate-repository.qmd"
EXISTING_REPOS_DOC = DOCS_DIR / "how-to/bootstrap-existing-repository.qmd"
GENERATOR_DOC = DOCS_DIR / "reference/cli-and-metadata.qmd"
LIFECYCLE_DOC = DOCS_DIR / "reference/bootstrap-lifecycle.qmd"
PROFILES_DOC = DOCS_DIR / "reference/profiles-and-skills.qmd"
TEMPLATES_DOC = DOCS_DIR / "reference/templates.qmd"
DECISIONS_DOC = DOCS_DIR / "project-record/decisions.qmd"
RESEARCH_DOC = DOCS_DIR / "project-record/research.qmd"
PYTHON_FIRST_PLAN = DOCS_DIR / "project-record/python-first-project-plan.qmd"
METADATA_V2_ADR = DOCS_DIR / "project-record/adr/0010-metadata-v2-preview-first-refresh.md"
PYTHON_FIRST_ADR = DOCS_DIR / "project-record/adr/0012-python-first-greenfield-existing-repository-boundary.md"
REPOSITORY_MAP_DOC = DOCS_DIR / "project-record/repository-map.md"

VALID_DOC_TYPES = {"tutorial", "how-to", "reference", "explanation"}
PRODUCT_SECTIONS = {
    "Tutorials": "tutorial",
    "How-to": "how-to",
    "Reference": "reference",
    "Explanation": "explanation",
}
DIRECTORY_FOR_TYPE = {
    "tutorial": "tutorials",
    "how-to": "how-to",
    "reference": "reference",
    "explanation": "explanation",
}
EXPECTED_SECTIONS = (*PRODUCT_SECTIONS, "Project Record")
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]*]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$")


def _subcommand_parser(command_name: str) -> argparse.ArgumentParser:
    parser = build_parser()
    subparsers_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return subparsers_action.choices[command_name]


def _subcommand_names() -> tuple[str, ...]:
    subparser = next(
        action
        for action in build_parser()._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return tuple(subparser.choices)


def _option_strings_for_dest(parser: argparse.ArgumentParser, dest: str) -> tuple[str, ...]:
    options = []
    for action in parser._actions:
        if action.dest == dest:
            options.extend(option for option in action.option_strings if option.startswith("--"))
    return tuple(dict.fromkeys(options))


def _front_matter(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "---":
        return {}
    end = lines[1:].index("---") + 1
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if separator and not line.startswith(" "):
            metadata[key] = value.strip().strip('"\'')
    return metadata


def _source_paths() -> set[str]:
    return {
        path.relative_to(DOCS_DIR).as_posix()
        for pattern in ("**/*.qmd", "**/*.md")
        for path in DOCS_DIR.glob(pattern)
        if "_site" not in path.parts and ".quarto" not in path.parts
    }


def _render_paths() -> list[str]:
    paths: list[str] = []
    in_render = False
    for line in QUARTO_CONFIG.read_text().splitlines():
        if line == "  render:":
            in_render = True
            continue
        if in_render and line and not line.startswith("    "):
            break
        if in_render and line.startswith("    - "):
            paths.append(line.removeprefix("    - "))
    return paths


def _sidebar_membership() -> tuple[list[str], dict[str, list[str]]]:
    paths: list[str] = []
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    in_contents = False
    for line in QUARTO_CONFIG.read_text().splitlines():
        if line == "    contents:":
            in_contents = True
            continue
        if in_contents and line.startswith("  page-footer:"):
            break
        if not in_contents:
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 6 and stripped.startswith("- section: "):
            current_section = stripped.removeprefix("- section: ")
            sections[current_section] = []
            continue
        if stripped.startswith("- ") and not stripped.startswith("- section: "):
            candidate = stripped.removeprefix("- ")
            if candidate.endswith((".qmd", ".md")):
                paths.append(candidate)
                if current_section is not None:
                    sections[current_section].append(candidate)
    return paths, sections


def _markdown_slug(heading: str) -> str:
    explicit = re.search(r"\{#([^}]+)}\s*$", heading)
    if explicit:
        return explicit.group(1)
    heading = re.sub(r"`([^`]+)`", r"\1", heading)
    heading = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", heading)
    heading = re.sub(r"[^\w\s-]", "", heading.lower())
    return re.sub(r"[-\s]+", "-", heading).strip("-")


def _anchors(path: Path) -> set[str]:
    anchors = set()
    for line in path.read_text().splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            anchors.add(_markdown_slug(match.group(1)))
    return anchors


def _bash_code_blocks(path: Path) -> tuple[str, ...]:
    return tuple(
        block.partition("```")[0].strip()
        for block in path.read_text().split("```bash\n")[1:]
    )


class DocsTests(unittest.TestCase):
    def test_quarto_inventory_sidebar_and_sources_match(self) -> None:
        source_paths = _source_paths()
        render_paths = _render_paths()
        sidebar_paths, sections = _sidebar_membership()

        self.assertEqual(set(render_paths), source_paths)
        self.assertEqual(len(render_paths), len(set(render_paths)))
        self.assertEqual(set(sidebar_paths), source_paths)
        self.assertEqual(len(sidebar_paths), len(set(sidebar_paths)))
        self.assertEqual(tuple(sections), EXPECTED_SECTIONS)
        self.assertIn("include-after-body: accessibility.html", QUARTO_CONFIG.read_text())
        accessibility_include = (DOCS_DIR / "accessibility.html").read_text()
        self.assertIn("[role='combobox']", accessibility_include)
        self.assertIn("#quarto-search button", accessibility_include)
        self.assertGreaterEqual(accessibility_include.count('"aria-label"'), 2)

    def test_rendered_pages_have_one_divio_type_matching_navigation(self) -> None:
        _, sections = _sidebar_membership()

        self.assertEqual(_front_matter(INDEX_DOC).get("page-role"), "landing")
        for section, paths in sections.items():
            for relative_path in paths:
                doc_type = _front_matter(DOCS_DIR / relative_path).get("doc-type")
                self.assertIn(doc_type, VALID_DOC_TYPES, relative_path)
                assert doc_type is not None
                if section in PRODUCT_SECTIONS:
                    self.assertEqual(doc_type, PRODUCT_SECTIONS[section], relative_path)
                    self.assertEqual(Path(relative_path).parts[0], DIRECTORY_FOR_TYPE[doc_type])
                else:
                    self.assertEqual(Path(relative_path).parts[0], "project-record")

    def test_local_document_links_and_fragments_resolve(self) -> None:
        for relative_path in _source_paths():
            source = DOCS_DIR / relative_path
            for raw_target in LINK_PATTERN.findall(source.read_text()):
                target = raw_target.split(maxsplit=1)[0].strip("<>")
                if "://" in target or target.startswith("mailto:"):
                    continue
                path_part, _, fragment = target.partition("#")
                destination = source if not path_part else (source.parent / unquote(path_part)).resolve()
                self.assertTrue(destination.exists(), f"{relative_path}: {target}")
                if fragment and destination.suffix in {".md", ".qmd"}:
                    self.assertIn(unquote(fragment), _anchors(destination), f"{relative_path}: {target}")

    def test_repository_map_routes_authoritative_surfaces(self) -> None:
        content = REPOSITORY_MAP_DOC.read_text()
        required_paths = {
            "AGENTS.md",
            "CONTEXT.md",
            "PLAN.md",
            "src/repo_familiar/cli.py",
            "src/repo_familiar/generator.py",
            "src/repo_familiar/asset_plan.py",
            "src/repo_familiar/profiles.py",
            "src/repo_familiar/metadata.py",
            "src/repo_familiar/advice.py",
            "src/repo_familiar/advice_dag.py",
            "tests/test_docs.py",
        }
        for path in required_paths:
            self.assertTrue((REPO_ROOT / path).exists(), path)
            self.assertIn(f"`{path}`", content, path)
        self.assertIn("docs/project-record/repository-map.md", (REPO_ROOT / "AGENTS.md").read_text())

    def test_cli_reference_covers_every_subcommand(self) -> None:
        content = GENERATOR_DOC.read_text()
        command_index = content.split("## Command Index", 1)[1].split("## Generation Defaults", 1)[0]
        documented_commands = set(re.findall(r"`([a-z][a-z0-9-]+)`", command_index))
        self.assertEqual(documented_commands, set(_subcommand_names()))

    def test_profile_reference_covers_registry_lookup_contract(self) -> None:
        content = PROFILES_DOC.read_text()
        generate_parser = _subcommand_parser("generate")
        for spec in PROFILE_FAMILY_COMMANDS:
            self.assertIn(f"`{spec.list_command}`", content)
            self.assertIn(f"`{spec.add_command}`", content)
            for option in _option_strings_for_dest(generate_parser, spec.selection_attr):
                self.assertIn(f"`{option}`", content)
        self.assertIn("src/repo_familiar/profiles.py", content)
        self.assertIn("repo_familiar catalog", content)
        self.assertIn("repo_familiar describe", content)

    def test_template_reference_matches_registered_templates_and_defaults(self) -> None:
        content = TEMPLATES_DOC.read_text()
        for template in list_templates():
            self.assertIn(f"`{template}`", content)
        self.assertEqual(
            GenerationOptions(
                name="Default",
                description="Default.",
                output_dir=Path("unused"),
            ).template,
            "python-reproducible",
        )
        self.assertIn("Existing-repository commands use `basic`", content)

    def test_existing_repository_how_to_previews_before_apply(self) -> None:
        content = EXISTING_REPOS_DOC.read_text()
        preview = "uv run python -m repo_familiar bootstrap-existing --path /path/to/repo"
        apply = f"{preview} --apply"
        self.assertLess(content.index(preview), content.index(apply))
        self.assertIn("then use `promote-surface` or all-or-nothing `promote-template`", content)

    def test_getting_started_commands_follow_the_generate_parser(self) -> None:
        generate_blocks = [
            block
            for block in _bash_code_blocks(GETTING_STARTED_DOC)
            if block.startswith("uv run python -m repo_familiar generate ")
        ]
        self.assertEqual(len(generate_blocks), 2)
        parsed = []
        for block in generate_blocks:
            command = block.replace("\\\n", "")
            arguments = shlex.split(command)[5:]
            parsed.append(build_parser().parse_args(arguments))
        self.assertTrue(parsed[0].dry_run)
        self.assertFalse(parsed[1].dry_run)
        self.assertEqual(parsed[0].template, parsed[1].template)
        self.assertEqual(parsed[0].output, parsed[1].output)
        self.assertIn("uv run python -m repo_familiar check --path /tmp/repo-familiar-demo", GETTING_STARTED_DOC.read_text())

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "demo"
            command_arguments = []
            for block in generate_blocks:
                arguments = shlex.split(block.replace("\\\n", ""))[5:]
                arguments[arguments.index("--output") + 1] = str(output_path)
                command_arguments.append(arguments)

            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(command_arguments[0]), 0)
            self.assertFalse(output_path.exists())

            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(command_arguments[1]), 0)
            self.assertTrue((output_path / ".repo-familiar/bootstrap.yml").exists())

            check_output = io.StringIO()
            with redirect_stdout(check_output):
                self.assertEqual(main(["check", "--path", str(output_path)]), 0)
            self.assertIn("0 modified", check_output.getvalue())
            self.assertIn("0 missing", check_output.getvalue())

    def test_metadata_schema_has_one_human_reference(self) -> None:
        generator = GENERATOR_DOC.read_text()
        snippet = next(
            block.partition("```")[0]
            for block in generator.split("```yaml\n")[1:]
            if block.startswith("schema_version: 2\n")
        )
        last_index = snippet.index("  template: <template-name>")
        for key in SELECTED_OPTION_KEYS:
            line = f"  {key}: []"
            self.assertIn(line, snippet)
            current_index = snippet.index(line)
            self.assertGreater(current_index, last_index)
            last_index = current_index
        self.assertIn("render_context:", snippet)
        self.assertIn("managed_surfaces:", snippet)
        self.assertIn("managed_surface_assets:", snippet)
        self.assertIn("history:", snippet)
        for path in (README, USAGE_DOC, DOCS_DIR / "explanation/architecture.qmd", EXISTING_REPOS_DOC):
            self.assertNotIn("schema_version: 2", path.read_text(), str(path))

    def test_managed_surface_contract_is_current_without_parallel_status(self) -> None:
        generator = GENERATOR_DOC.read_text()
        lifecycle = LIFECYCLE_DOC.read_text()
        existing = EXISTING_REPOS_DOC.read_text()
        for command in (
            "migrate-metadata",
            "attach",
            "migrate-template",
            "promote-surface",
            "promote-template",
        ):
            self.assertIn(command, _subcommand_parser(command).prog)
            self.assertIn(f"`{command}`", generator)
            self.assertIn(f"`{command}`", lifecycle)
        self.assertIn("adopted Managed Surface assets", existing)
        self.assertIn("Dogfood Metadata v2 migration, attach, surface promotion", ROOT_PLAN.read_text())

    def test_project_record_indexes_cover_retained_records(self) -> None:
        decisions = DECISIONS_DOC.read_text()
        research = RESEARCH_DOC.read_text()
        for adr in sorted((DOCS_DIR / "project-record/adr").glob("*.md")):
            self.assertIn(f"./adr/{adr.name}", decisions)
        for assessment in sorted((DOCS_DIR / "project-record/assessments").glob("*.qmd")):
            self.assertIn(f"./assessments/{assessment.name}", research)
        self.assertNotIn("## Open Decisions", decisions)
        self.assertNotIn("## Research Questions", research)

    def test_retired_pages_and_internal_references_are_removed(self) -> None:
        retired = {
            "naming.qmd",
            "pre-bootstrap.qmd",
            "examples.qmd",
            "model-profiles.qmd",
            "tool-profiles.qmd",
            "advisory-profiles.qmd",
        }
        for path in retired:
            self.assertFalse((DOCS_DIR / path).exists(), path)
        combined = "\n".join((DOCS_DIR / path).read_text() for path in _source_paths())
        for path in retired:
            self.assertNotIn(path, combined)

    def test_point_in_time_plan_defers_live_status_to_root_plan(self) -> None:
        plan = PYTHON_FIRST_PLAN.read_text()
        self.assertIn("PLAN.md", plan)
        status = plan.split("## Status", 1)[1].split("##", 1)[0]
        for live_status_word in ("implemented", "pending", "complete"):
            self.assertNotIn(live_status_word, status.lower())
        self.assertNotIn("Status: implemented", plan)
        self.assertNotIn("now gate", plan)

        for adr in sorted((DOCS_DIR / "project-record/adr").glob("*.md")):
            content = adr.read_text()
            if "## Status" not in content:
                continue
            adr_status = content.split("## Status", 1)[1].split("##", 1)[0]
            for live_status_word in ("implemented", "pending", "complete"):
                self.assertNotIn(live_status_word, adr_status.lower(), adr.name)

        python_first_adr = PYTHON_FIRST_ADR.read_text()
        self.assertIn("skills as the only write-capable upgrade slice", python_first_adr)
        metadata_v2_adr = METADATA_V2_ADR.read_text()
        self.assertNotIn("The implemented skills slice", metadata_v2_adr)
        self.assertNotIn("implemented preview/attach behavior", metadata_v2_adr)


if __name__ == "__main__":
    unittest.main()
