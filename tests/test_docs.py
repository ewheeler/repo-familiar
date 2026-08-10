from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from repo_familiar.cli import (
    PROFILE_FAMILY_COMMANDS,
    TARGETED_ADD_COMMANDS,
    build_parser,
)
from repo_familiar.generator import GenerationOptions, list_templates
from repo_familiar.metadata import SELECTED_OPTION_KEYS, load_bootstrap_metadata

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
REPO_ROOT = DOCS_DIR.parent
BOOTSTRAP_LIFECYCLE_DOC = DOCS_DIR / "bootstrap-lifecycle.qmd"
QUARTO_CONFIG = DOCS_DIR / "_quarto.yml"
USAGE_DOC = DOCS_DIR / "usage.qmd"
GENERATOR_DOC = DOCS_DIR / "generator.qmd"
EXISTING_REPOS_DOC = DOCS_DIR / "existing-repos.qmd"
PRE_BOOTSTRAP_DOC = DOCS_DIR / "pre-bootstrap.qmd"
DECISIONS_DOC = DOCS_DIR / "decisions.qmd"
METADATA_V2_ADR = DOCS_DIR / "adr/0010-metadata-v2-preview-first-refresh.md"
AGENT_PLUGIN_ADR = DOCS_DIR / "adr/0011-agent-plugins-export-pilot.md"
PYTHON_FIRST_ADR = DOCS_DIR / "adr/0012-python-first-greenfield-existing-repository-boundary.md"
PYTHON_FIRST_PLAN = DOCS_DIR / "python-first-project-plan.qmd"
ROOT_PLAN = REPO_ROOT / "PLAN.md"
REPOSITORY_MAP_DOC = DOCS_DIR / "agents/repository-map.md"
EXAMPLE_BOOTSTRAP_METADATA = (
    Path(__file__).resolve().parents[1]
    / "examples/basic-agentic-project/.repo-familiar/bootstrap.yml"
)


def _subcommand_parser(command_name: str) -> argparse.ArgumentParser:
    parser = build_parser()
    subparsers_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return subparsers_action.choices[command_name]


def _option_strings_for_dest(parser: argparse.ArgumentParser, dest: str) -> tuple[str, ...]:
    options = []
    for action in parser._actions:
        if action.dest != dest:
            continue
        options.extend(option for option in action.option_strings if option.startswith("--"))
    return tuple(dict.fromkeys(options))


def _positional_action(parser: argparse.ArgumentParser, dest: str) -> argparse.Action:
    return next(action for action in parser._actions if action.dest == dest)


def _bash_code_blocks(path: Path) -> tuple[str, ...]:
    content = path.read_text()
    return tuple(block.partition("```")[0].strip() for block in content.split("```bash\n")[1:])


def _subcommand_names() -> tuple[str, ...]:
    subparser = next(
        action
        for action in build_parser()._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return tuple(subparser.choices)


class DocsTests(unittest.TestCase):
    def test_repository_map_routes_key_implementation_seams(self) -> None:
        content = REPOSITORY_MAP_DOC.read_text()
        required_paths = {
            "AGENTS.md",
            "CONTEXT.md",
            "PLAN.md",
            "src/repo_familiar/generator.py",
            "src/repo_familiar/agent_plugins.py",
            "src/repo_familiar/asset_plan.py",
            "src/repo_familiar/profiles.py",
            "src/repo_familiar/metadata.py",
            "src/repo_familiar/advice.py",
            "src/repo_familiar/advice_dag.py",
            "src/repo_familiar/upgrade.py",
            "tests/test_generator.py",
            "tests/test_agent_plugins.py",
            "tests/test_profiles.py",
            "tests/test_docs.py",
        }

        for path in required_paths:
            self.assertTrue((REPO_ROOT / path).exists(), path)
            self.assertIn(f"`{path}`", content, path)
        self.assertIn("docs/agents/repository-map.md", (REPO_ROOT / "AGENTS.md").read_text())
        self.assertIn("agents/repository-map.md", QUARTO_CONFIG.read_text())

    def test_generator_doc_lists_all_list_commands(self) -> None:
        content = GENERATOR_DOC.read_text()

        for command_name in sorted(name for name in _subcommand_names() if name.startswith("list-")):
            self.assertIn(f"uv run python -m repo_familiar {command_name}", content)

    def test_template_docs_cover_registered_templates_and_split_defaults(self) -> None:
        templates_doc = (DOCS_DIR / "templates.qmd").read_text()
        generator_doc = GENERATOR_DOC.read_text()

        for template in list_templates():
            self.assertIn(f"`{template}`", templates_doc)
        self.assertEqual(
            GenerationOptions(
                name="Default",
                description="Default.",
                output_dir=Path("unused"),
            ).template,
            "python-reproducible",
        )
        self.assertIn("Existing-repository commands use `basic`", generator_doc)

    def test_existing_repo_doc_lists_all_targeted_add_commands(self) -> None:
        content = EXISTING_REPOS_DOC.read_text()

        for command_name in sorted(TARGETED_ADD_COMMANDS):
            self.assertIn(f"uv run python -m repo_familiar {command_name}", content)

    def test_bootstrap_lifecycle_doc_is_in_quarto_navigation(self) -> None:
        quarto_config = QUARTO_CONFIG.read_text()

        self.assertIn("- bootstrap-lifecycle.qmd", quarto_config)

    def test_metadata_v2_adr_is_in_quarto_render_set(self) -> None:
        quarto_config = QUARTO_CONFIG.read_text()

        self.assertIn("- adr/0010-metadata-v2-preview-first-refresh.md", quarto_config)

    def test_agent_plugin_pilot_is_documented_and_rendered(self) -> None:
        self.assertIn(
            "- adr/0011-agent-plugins-export-pilot.md",
            QUARTO_CONFIG.read_text(),
        )
        self.assertIn(
            "uv run python -m repo_familiar export-plugin",
            GENERATOR_DOC.read_text(),
        )
        adr = AGENT_PLUGIN_ADR.read_text()
        self.assertIn("optional derived export format", adr)
        self.assertIn("does not mutate a Downstream Repository", adr)

    def test_python_first_plan_and_adr_are_documented_and_rendered(self) -> None:
        quarto_config = QUARTO_CONFIG.read_text()
        decisions = DECISIONS_DOC.read_text()

        self.assertTrue(PYTHON_FIRST_PLAN.exists())
        self.assertTrue(PYTHON_FIRST_ADR.exists())
        self.assertGreaterEqual(quarto_config.count("- python-first-project-plan.qmd"), 2)
        self.assertGreaterEqual(
            quarto_config.count(
                "- adr/0012-python-first-greenfield-existing-repository-boundary.md"
            ),
            2,
        )
        self.assertIn(
            "[Separate Python-first greenfield defaults from existing-repository adoption]",
            decisions,
        )

    def test_python_first_plan_preserves_existing_repository_boundary(self) -> None:
        content = PYTHON_FIRST_PLAN.read_text()
        adr = PYTHON_FIRST_ADR.read_text()

        self.assertIn("NEW_REPOSITORY_DEFAULT_TEMPLATE", content)
        self.assertIn("EXISTING_REPOSITORY_FALLBACK_TEMPLATE", content)
        self.assertIn("Plain Quarto documentation must not trigger", content)
        self.assertIn("No non-skill upgrade apply is enabled under Metadata v1", content)
        self.assertIn("Unknown or retired recorded template", content)
        self.assertIn("skills as the only write-capable upgrade slice", adr)
        self.assertIn("python-first-project-plan.qmd", BOOTSTRAP_LIFECYCLE_DOC.read_text())

    def test_metadata_v2_adr_includes_preview_first_sections(self) -> None:
        content = METADATA_V2_ADR.read_text()

        self.assertIn("## Why Metadata V1 Is Enough For Read-Only Checks", content)
        self.assertIn("## Why Metadata V1 Is Not Enough For Safe Refresh Writes", content)
        self.assertIn("## Metadata V2 Concepts", content)
        self.assertIn("## Preview First, Apply Later", content)
        self.assertIn("## Safety Boundaries", content)

    def test_refresh_docs_cross_link_to_metadata_v2_adr(self) -> None:
        adr_link = "./adr/0010-metadata-v2-preview-first-refresh.md"

        self.assertIn(adr_link, BOOTSTRAP_LIFECYCLE_DOC.read_text())
        self.assertIn(adr_link, EXISTING_REPOS_DOC.read_text())
        self.assertIn(adr_link, Path(DOCS_DIR / "generator.qmd").read_text())

    def test_decisions_page_lists_metadata_v2_adr(self) -> None:
        content = DECISIONS_DOC.read_text()

        self.assertIn("[Plan Metadata v2 and preview-first refresh](./adr/0010-metadata-v2-preview-first-refresh.md)", content)

    def test_bootstrap_lifecycle_doc_includes_required_sections(self) -> None:
        content = BOOTSTRAP_LIFECYCLE_DOC.read_text()

        self.assertIn("## New Repository Path", content)
        self.assertIn("## Existing Repository Path", content)
        self.assertIn("## Reference Source Maintenance Path", content)
        self.assertIn("## Contract Ownership", content)
        self.assertIn("## Profile Family Selection Matrix", content)
        self.assertIn("## Command Safety", content)

    def test_bootstrap_lifecycle_doc_covers_targeted_add_commands(self) -> None:
        content = BOOTSTRAP_LIFECYCLE_DOC.read_text()

        for command_name in sorted(TARGETED_ADD_COMMANDS):
            self.assertIn(f"`{command_name}`", content)

    def test_bootstrap_lifecycle_profile_matrix_matches_cli_families(self) -> None:
        content = BOOTSTRAP_LIFECYCLE_DOC.read_text()
        generate_parser = _subcommand_parser("generate")

        for spec in PROFILE_FAMILY_COMMANDS:
            add_parser = _subcommand_parser(spec.add_command)
            self.assertIn(f"`{spec.selection_attr}`", content)
            self.assertIn(f"`{spec.list_command}`", content)
            for option in _option_strings_for_dest(generate_parser, spec.selection_attr):
                self.assertIn(f"`{option}`", content)
            for option in _option_strings_for_dest(add_parser, spec.selection_attr):
                self.assertIn(f"`{option}`", content)
            self.assertIn(f"`{spec.add_command}`", content)

    def test_profile_family_command_specs_match_targeted_add_contracts(self) -> None:
        for spec in PROFILE_FAMILY_COMMANDS:
            targeted_add = TARGETED_ADD_COMMANDS[spec.add_command]
            self.assertEqual(targeted_add.required_attr, spec.selection_attr)
            self.assertEqual(targeted_add.keep_attrs, (spec.selection_attr,))
            self.assertEqual(targeted_add.asset_groups, (spec.asset_group, "metadata"))

    def test_bootstrap_lifecycle_profile_matrix_mentions_secrets_apply_detail(self) -> None:
        content = BOOTSTRAP_LIFECYCLE_DOC.read_text()

        self.assertIn("`--sops-age-recipient`", content)

    def test_usage_doc_shows_preview_before_apply_for_targeted_adds(self) -> None:
        content = USAGE_DOC.read_text()

        self.assertLess(
            content.index("uv run python -m repo_familiar add-memory --path /path/to/repo --memory-profile memory-local"),
            content.index("uv run python -m repo_familiar add-memory --path /path/to/repo --memory-profile memory-local --apply"),
        )

    def test_existing_repo_doc_shows_preview_before_apply_examples(self) -> None:
        content = EXISTING_REPOS_DOC.read_text()

        self.assertLess(
            content.index("uv run python -m repo_familiar bootstrap-existing --path /path/to/repo"),
            content.index("uv run python -m repo_familiar bootstrap-existing --path /path/to/repo --apply"),
        )
        self.assertLess(
            content.index("uv run python -m repo_familiar add-model --path /path/to/repo --model-profile default-coding"),
            content.index("uv run python -m repo_familiar add-model --path /path/to/repo --model-profile default-coding --apply"),
        )

    def test_generator_doc_shows_preview_before_apply_examples(self) -> None:
        content = GENERATOR_DOC.read_text()
        preview_command = "\n".join(
            (
                "uv run python -m repo_familiar add-tool \\",
                "  --path /path/to/repo \\",
                "  --tool cq",
            )
        )
        apply_command = "\n".join(
            (
                "uv run python -m repo_familiar add-tool \\",
                "  --path /path/to/repo \\",
                "  --tool cq \\",
                "  --apply",
            )
        )

        self.assertLess(
            content.index("uv run python -m repo_familiar bootstrap-existing --path /path/to/repo"),
            content.index("uv run python -m repo_familiar bootstrap-existing --path /path/to/repo --apply"),
        )
        self.assertLess(content.index(preview_command), content.index(apply_command))

    def test_pre_bootstrap_doc_shows_preview_before_apply_examples(self) -> None:
        content = PRE_BOOTSTRAP_DOC.read_text()

        self.assertLess(
            content.index("uv run python -m repo_familiar add-memory --path /path/to/repo --memory-profile memory-local"),
            content.index("uv run python -m repo_familiar add-memory --path /path/to/repo --memory-profile memory-local --apply"),
        )
        self.assertLess(
            content.index("uv run python -m repo_familiar add-docs --path /path/to/repo"),
            content.index("uv run python -m repo_familiar add-docs --path /path/to/repo --apply"),
        )

    def test_generator_preview_example_matches_committed_example_metadata(self) -> None:
        preview_block = next(
            block
            for block in _bash_code_blocks(GENERATOR_DOC)
            if block.startswith("uv run python -m repo_familiar generate ") and "--dry-run" in block
        )
        metadata = load_bootstrap_metadata(EXAMPLE_BOOTSTRAP_METADATA)
        generate_parser = _subcommand_parser("generate")

        self.assertIn('--name "Basic Agentic Project"', preview_block)
        self.assertIn(
            '--description "Example downstream repository generated by repo-familiar."',
            preview_block,
        )
        self.assertIn("--output /tmp/basic-agentic-project", preview_block)
        self.assertIn("--template basic", preview_block)

        for value in metadata.selected_options["agent_harnesses"]:
            self.assertIn(f"--agent-harness {value}", preview_block)
        for spec in PROFILE_FAMILY_COMMANDS:
            option = _option_strings_for_dest(generate_parser, spec.selection_attr)[0]
            for value in metadata.selected_options[spec.selection_attr]:
                self.assertIn(f"{option} {value}", preview_block)
        for value in metadata.selected_options["skills"]:
            self.assertIn(f"--skill {value}", preview_block)
        for value in metadata.selected_options["sops_age_recipients"]:
            self.assertIn(f"--sops-age-recipient {value}", preview_block)

    def test_usage_metadata_snippet_matches_selected_option_schema(self) -> None:
        snippet = next(
            block
            for block in USAGE_DOC.read_text().split("```yaml\n")[1:]
            if block.startswith("schema_version: 2\n")
        ).partition("```")[0]

        self.assertLess(snippet.index("  template: <template-name>"), snippet.index("  docs: quarto"))
        last_index = snippet.index("  template: <template-name>")
        for key in SELECTED_OPTION_KEYS:
            line = f"  {key}: []"
            self.assertIn(line, snippet)
            current_index = snippet.index(line)
            self.assertGreater(current_index, last_index)
            last_index = current_index
        self.assertGreater(snippet.index("  docs: quarto"), last_index)
        self.assertIn("render_context:", snippet)
        self.assertIn("managed_surfaces:", snippet)
        self.assertIn("managed_surface_assets:", snippet)
        self.assertIn("history:", snippet)

    def test_managed_surface_commands_are_documented(self) -> None:
        generator_doc = GENERATOR_DOC.read_text()
        lifecycle_doc = BOOTSTRAP_LIFECYCLE_DOC.read_text()
        existing_doc = (DOCS_DIR / "existing-repos.qmd").read_text()

        for command in (
            "migrate-metadata",
            "attach",
            "promote-surface",
            "promote-template",
            "migrate-template",
        ):
            self.assertIn(command, _subcommand_parser(command).prog)
            self.assertIn(f"repo_familiar {command}", generator_doc)
            self.assertIn(f"`{command}`", lifecycle_doc)
            self.assertIn(f"repo_familiar {command}", existing_doc)
        self.assertIn(
            "`promote-surface` writes one eligible surface atomically",
            lifecycle_doc,
        )
        self.assertIn(
            "`promote-template` changes `selected_template` only after every target surface",
            lifecycle_doc,
        )
        self.assertIn(
            "then use `promote-surface` or all-or-nothing `promote-template`",
            existing_doc,
        )
        self.assertIn(
            "Managed Surface and template writes use the separate preview-first "
            "`promote-surface` and `promote-template` commands",
            generator_doc,
        )
        self.assertNotIn("skills are the only write-capable path", generator_doc)

        roadmap = ROOT_PLAN.read_text()
        self.assertIn("Dogfood Metadata v2 migration, attach, surface promotion", roadmap)
        self.assertIn("additional write strategies", roadmap)
        self.assertNotIn(
            "Add narrow write strategies only after preview evidence",
            roadmap,
        )

        context = (REPO_ROOT / "CONTEXT.md").read_text()
        architecture = (DOCS_DIR / "architecture.qmd").read_text()
        adr = PYTHON_FIRST_ADR.read_text()
        python_plan = PYTHON_FIRST_PLAN.read_text()
        self.assertNotIn("A future explicit workflow", context)
        self.assertNotIn("The first implementation is a Python CLI", architecture)
        self.assertNotIn("The planned refresh model", architecture)
        self.assertNotIn("promotion and application-source adoption preview-only", adr)
        self.assertIn("Those records now gate", python_plan)
        self.assertIn("adopted Managed Surface assets", existing_doc)

    def test_catalog_and_describe_parser_cover_profile_families_and_formats(self) -> None:
        catalog_parser = _subcommand_parser("catalog")
        describe_parser = _subcommand_parser("describe")
        expected_families = {
            "model",
            "tool",
            "memory",
            "prompt",
            "safety",
            "privacy",
            "public-interest",
            "repomap",
            "sandbox",
            "secrets",
            "design",
            "worktree",
        }
        catalog_family_choices = _positional_action(catalog_parser, "family").choices or ()
        describe_family_choices = _positional_action(describe_parser, "family").choices or ()

        self.assertEqual(set(catalog_family_choices), expected_families)
        self.assertEqual(set(describe_family_choices), expected_families)
        self.assertEqual(_option_strings_for_dest(catalog_parser, "format"), ("--format",))
        self.assertEqual(_option_strings_for_dest(describe_parser, "format"), ("--format",))

    def test_usage_doc_mentions_catalog_and_describe_commands(self) -> None:
        content = USAGE_DOC.read_text()

        self.assertIn("uv run python -m repo_familiar catalog model", content)
        self.assertIn("uv run python -m repo_familiar describe tool cq", content)


if __name__ == "__main__":
    unittest.main()
