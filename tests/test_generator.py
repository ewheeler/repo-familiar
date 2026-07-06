from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

import repo_familiar.cli as cli_module
from repo_familiar.cli import main
from repo_familiar.generator import (
    ExistingBootstrapOptions,
    GenerationOptions,
    advise_existing_repository,
    audit_existing_repository,
    bootstrap_existing_repository,
    check_generated_repository,
    generate_project,
)


class GeneratorTests(unittest.TestCase):
    def test_generates_minimal_downstream_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            assets = generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    agent_harnesses=("opencode", "hermes"),
                    model_profiles=("default-coding", "budget-review"),
                    reference_type="git",
                    reference_url="https://example.invalid/repo-familiar.git",
                    reference_ref="test-ref",
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertTrue((output_dir / "AGENTS.md").exists())
            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "opencode.json").exists())
            self.assertTrue((output_dir / ".gitignore").exists())
            self.assertTrue((output_dir / ".agents/design.yml").exists())
            self.assertTrue((output_dir / ".agents/memory.yml").exists())
            self.assertTrue((output_dir / ".agents/models.yml").exists())
            self.assertTrue((output_dir / ".agents/privacy.yml").exists())
            self.assertTrue((output_dir / ".agents/public-interest.yml").exists())
            self.assertTrue((output_dir / ".agents/prompts.yml").exists())
            self.assertTrue((output_dir / ".agents/repomap.yml").exists())
            self.assertTrue((output_dir / ".agents/sandbox.yml").exists())
            self.assertTrue((output_dir / ".agents/secrets.yml").exists())
            self.assertTrue((output_dir / ".agents/safety.yml").exists())
            self.assertTrue((output_dir / ".agents/skill-sources.yml").exists())
            self.assertTrue((output_dir / ".agents/tools.yml").exists())
            self.assertTrue((output_dir / ".agents/worktrees.yml").exists())
            self.assertTrue((output_dir / ".env.example").exists())
            self.assertTrue((output_dir / ".agents/skills/grill-with-docs/SKILL.md").exists())
            self.assertTrue((output_dir / "docs/_quarto.yml").exists())
            self.assertTrue((output_dir / "docs/tutorials.qmd").exists())
            self.assertTrue((output_dir / "docs/how-to.qmd").exists())
            self.assertTrue((output_dir / "docs/reference.qmd").exists())
            self.assertTrue((output_dir / "docs/explanation.qmd").exists())
            self.assertTrue((output_dir / "plan.md").exists())
            self.assertTrue((output_dir / ".repo-familiar/bootstrap.yml").exists())

            bootstrap = (output_dir / ".repo-familiar/bootstrap.yml").read_text()
            self.assertIn('schema_version: 1', bootstrap)
            self.assertIn('bootstrap_mode: "new_repository"', bootstrap)
            self.assertIn('url: "https://example.invalid/repo-familiar.git"', bootstrap)
            self.assertIn('ref: "test-ref"', bootstrap)
            self.assertIn('generated_at: "2026-05-10T00:00:00Z"', bootstrap)
            self.assertIn('path: "AGENTS.md"', bootstrap)
            self.assertIn('kind: "agent_instructions"', bootstrap)
            self.assertIn('path: "README.md"', bootstrap)
            self.assertIn('path: "opencode.json"', bootstrap)
            self.assertIn('path: ".gitignore"', bootstrap)
            self.assertIn('path: ".agents/models.yml"', bootstrap)
            self.assertIn('path: ".agents/tools.yml"', bootstrap)
            self.assertIn('path: ".agents/memory.yml"', bootstrap)
            self.assertIn('path: ".agents/secrets.yml"', bootstrap)
            self.assertIn('path: ".agents/public-interest.yml"', bootstrap)
            self.assertIn('path: ".agents/skill-sources.yml"', bootstrap)
            self.assertIn('path: ".env.example"', bootstrap)
            self.assertIn('secrets_profiles:', bootstrap)
            self.assertIn('- "kvenv-azure-keyvault"', bootstrap)
            self.assertIn('memory_profiles:', bootstrap)
            self.assertIn('- "memory-local"', bootstrap)
            self.assertIn("content_sha256:", bootstrap)
            self.assertIn('kind: "skill"', bootstrap)
            self.assertIn('source: "generator:bootstrap"', bootstrap)

            models = (output_dir / ".agents/models.yml").read_text()
            self.assertIn("default-coding:", models)
            self.assertIn("budget-review:", models)
            self.assertEqual(len(assets), 31)

    def test_refuses_non_empty_output_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            (output_dir / "existing.txt").write_text("keep me")

            with self.assertRaises(FileExistsError):
                generate_project(
                    GenerationOptions(
                        name="Demo Project",
                        description="A generated demo.",
                        output_dir=output_dir,
                    )
                )

    def test_dry_run_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            assets = generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    dry_run=True,
                )
            )

            self.assertEqual(len(assets), 31)
            self.assertFalse(output_dir.exists())

    def test_skips_opencode_config_when_harness_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    agent_harnesses=("hermes",),
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertFalse((output_dir / "opencode.json").exists())

    def test_paseo_harness_records_selection_without_repo_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    agent_harnesses=("paseo",),
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertFalse((output_dir / "opencode.json").exists())
            self.assertIn('- `paseo`', (output_dir / "AGENTS.md").read_text())
            self.assertIn('- "paseo"', (output_dir / ".repo-familiar/bootstrap.yml").read_text())

    def test_opencode_mcp_profiles_render_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    tool_profiles=("cq", "opencode-playwright-mcp", "opencode-context7-mcp", "opencode-headroom-mcp"),
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            config = json.loads((output_dir / "opencode.json").read_text())

            self.assertEqual(config["skills"]["paths"], [".agents/skills"])
            self.assertEqual(config["mcp"]["playwright"]["command"], ["npx", "-y", "@playwright/mcp"])
            self.assertEqual(config["mcp"]["context7"]["headers"]["CONTEXT7_API_KEY"], "${CONTEXT7_API_KEY}")
            self.assertEqual(config["mcp"]["headroom"]["command"], ["headroom", "mcp", "serve"])

    def test_sops_age_without_recipient_is_guidance_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    secrets_profiles=("sops-age",),
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertTrue((output_dir / ".agents/secrets.yml").exists())
            self.assertIn("sops-age:", (output_dir / ".agents/secrets.yml").read_text())
            self.assertFalse((output_dir / ".sops.yaml").exists())
            self.assertFalse((output_dir / "secrets/README.md").exists())

    def test_sops_age_with_recipient_generates_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    secrets_profiles=("sops-age",),
                    sops_age_recipients=("age1example", "age1team"),
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertIn("age1example", (output_dir / ".sops.yaml").read_text())
            self.assertTrue((output_dir / "secrets/.gitignore").exists())
            self.assertIn("sops exec-env", (output_dir / "secrets/README.md").read_text())
            self.assertTrue((output_dir / "docs/secrets.qmd").exists())

    def test_existing_sops_config_is_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / ".sops.yaml").write_text("creation_rules: []\n")

            report = audit_existing_repository(
                ExistingBootstrapOptions(
                    path=repo,
                    secrets_profiles=("sops-age",),
                    sops_age_recipients=("age1example",),
                    asset_groups=("secrets",),
                )
            )

            self.assertIn(".sops.yaml", {asset.path for asset in report.conflicts})

    def test_cli_lists_templates_harnesses_and_model_profiles(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["list-templates"])
        self.assertEqual(result, 0)
        self.assertIn("basic", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["list-agent-harnesses"])
        self.assertEqual(result, 0)
        self.assertIn("opencode", stdout.getvalue())
        self.assertIn("paseo", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["list-model-profiles"])
        self.assertEqual(result, 0)
        self.assertIn("default-coding", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["list-tool-profiles"])
        self.assertEqual(result, 0)
        self.assertIn("cq", stdout.getvalue())
        self.assertIn("a11y-scanner", stdout.getvalue())
        self.assertIn("browser-automation", stdout.getvalue())
        self.assertIn("headroom-context-compression", stdout.getvalue())
        self.assertIn("headroom-mcp", stdout.getvalue())
        self.assertIn("headroom-proxy", stdout.getvalue())
        self.assertIn("opencode-headroom-mcp", stdout.getvalue())
        self.assertIn("opencode-homebrew-path", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["list-skills"])
        self.assertEqual(result, 0)
        self.assertIn("cq", stdout.getvalue())
        self.assertIn("grill-with-docs", stdout.getvalue())
        self.assertIn("get-api-docs", stdout.getvalue())
        self.assertIn("liteparse", stdout.getvalue())
        self.assertIn("playwright-cli", stdout.getvalue())
        self.assertIn("rodney-browser", stdout.getvalue())
        self.assertIn("upstream-improvement", stdout.getvalue())
        self.assertIn("a11y-web-scan", stdout.getvalue())
        self.assertIn("session-focus", stdout.getvalue())
        self.assertIn("qa-test-design", stdout.getvalue())
        self.assertIn("security-audit", stdout.getvalue())

        expected_profile_commands = [
            ("list-memory-profiles", "memory-local"),
            ("list-prompt-profiles", "prompt-migration-gpt55"),
            ("list-safety-profiles", "prompt-output-safety"),
            ("list-privacy-profiles", "data-privacy-review"),
            ("list-public-interest-profiles", "child-rights-digital"),
            ("list-repomap-profiles", "hamilton-dag"),
            ("list-sandbox-profiles", "sandbox-light"),
            ("list-secrets-profiles", "kvenv-azure-keyvault"),
            ("list-secrets-profiles", "sops-age"),
            ("list-design-profiles", "design-impeccable"),
            ("list-design-profiles", "design-a11y"),
            ("list-worktree-profiles", "parallel-worktrees"),
        ]
        for command, expected in expected_profile_commands:
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main([command])
            self.assertEqual(result, 0)
            self.assertIn(expected, stdout.getvalue())

    def test_cli_reports_invalid_model_profile(self) -> None:
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as tmpdir, redirect_stderr(stderr):
            result = main(
                [
                    "generate",
                    "--name",
                    "Demo Project",
                    "--output",
                    str(Path(tmpdir) / "demo-project"),
                    "--model-profile",
                    "missing-profile",
                ]
            )

        self.assertEqual(result, 1)
        self.assertIn("Unknown model profile", stderr.getvalue())

    def test_targeted_add_requires_selected_profile(self) -> None:
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as tmpdir, redirect_stderr(stderr):
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            result = main(["add-tool", "--path", str(repo)])

        self.assertEqual(result, 1)
        self.assertIn("add-tool requires at least one --tool or --tool-profile", stderr.getvalue())

    def test_cli_catalog_and_describe_profile_families(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["catalog", "model"])
        self.assertEqual(result, 0)
        self.assertIn("default-coding: general coding and repository maintenance", stdout.getvalue())
        self.assertIn("budget-review: cheaper review and planning passes", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["catalog", "tool", "--format", "json"])
        self.assertEqual(result, 0)
        catalog_payload = json.loads(stdout.getvalue())
        self.assertEqual(catalog_payload["family"], "tool")
        self.assertIn(
            {"name": "cq", "summary": "query shared agent knowledge before implementation and before fixing errors"},
            catalog_payload["profiles"],
        )

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["describe", "model", "default-coding"])
        self.assertEqual(result, 0)
        self.assertIn("provider: openai", stdout.getvalue())
        self.assertIn("model: gpt-5.5", stdout.getvalue())
        self.assertIn("use: general coding and repository maintenance", stdout.getvalue())

        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["describe", "secrets", "sops-age", "--format", "json"])
        self.assertEqual(result, 0)
        describe_payload = json.loads(stdout.getvalue())
        self.assertEqual(describe_payload["family"], "secrets")
        self.assertEqual(describe_payload["name"], "sops-age")
        self.assertEqual(
            describe_payload["profile"]["purpose"],
            "encrypt selected repository config or secret files while keeping plaintext out of git",
        )
        self.assertIn("setup", describe_payload["profile"])

    def test_cli_describe_reports_unknown_profile_name(self) -> None:
        stderr = StringIO()

        with redirect_stderr(stderr):
            result = main(["describe", "model", "missing-profile"])

        self.assertEqual(result, 1)
        self.assertIn("Unknown model profile: missing-profile", stderr.getvalue())

    def test_generate_requires_name_and_output_without_interactive(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            result = main(["generate"])

        self.assertEqual(result, 1)
        self.assertIn("requires --name and --output", stderr.getvalue())

    def test_generate_interactive_uses_prompted_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "interactive-project"
            original_prompt = cli_module.prompt_generation_options

            def fake_prompt(args):
                return GenerationOptions(
                    name="Interactive Project",
                    description="Prompted.",
                    output_dir=output_dir,
                    generated_at="2026-05-10T00:00:00Z",
                )

            cli_module.prompt_generation_options = fake_prompt
            try:
                stdout = StringIO()
                with redirect_stdout(stdout):
                    result = main(["generate", "--interactive"])
            finally:
                cli_module.prompt_generation_options = original_prompt

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / ".repo-familiar/bootstrap.yml").exists())
            self.assertIn("Generated Interactive Project", stdout.getvalue())

    def test_bootstrap_existing_interactive_uses_prompted_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            original_prompt = cli_module.prompt_existing_options

            def fake_prompt(args):
                return (
                    ExistingBootstrapOptions(
                        path=repo,
                        name="Existing Project",
                        generated_at="2026-05-10T00:00:00Z",
                        asset_groups=("memory", "metadata"),
                    ),
                    True,
                )

            cli_module.prompt_existing_options = fake_prompt
            try:
                stdout = StringIO()
                with redirect_stdout(stdout):
                    result = main(["bootstrap-existing", "--interactive"])
            finally:
                cli_module.prompt_existing_options = original_prompt

            self.assertEqual(result, 0)
            self.assertTrue((repo / ".agents/memory.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertIn("Wrote 2 assets", stdout.getvalue())

    def test_audits_existing_repository_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / "README.md").write_text("User-owned README")

            report = audit_existing_repository(
                ExistingBootstrapOptions(
                    path=repo,
                    name="Existing Project",
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertIn("README.md", {asset.path for asset in report.conflicts})
            self.assertIn("AGENTS.md", {asset.path for asset in report.missing})
            self.assertFalse((repo / "AGENTS.md").exists())

    def test_bootstraps_existing_repository_additively(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / "README.md").write_text("User-owned README")

            result = bootstrap_existing_repository(
                ExistingBootstrapOptions(
                    path=repo,
                    name="Existing Project",
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertTrue((repo / "AGENTS.md").exists())
            self.assertTrue((repo / ".agents/models.yml").exists())
            self.assertTrue((repo / ".agents/tools.yml").exists())
            self.assertTrue((repo / ".agents/skills/grill-with-docs/SKILL.md").exists())
            self.assertEqual((repo / "README.md").read_text(), "User-owned README")
            self.assertIn("README.md", {asset.path for asset in result.skipped_conflicts})

            bootstrap = (repo / ".repo-familiar/bootstrap.yml").read_text()
            self.assertIn('bootstrap_mode: "existing_repository"', bootstrap)
            self.assertNotIn('path: "README.md"', bootstrap)
            self.assertIn('path: ".agents/tools.yml"', bootstrap)

    def test_add_skill_only_writes_skill_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-skill",
                        "--path",
                        str(repo),
                        "--skill",
                        "grill-with-docs",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((repo / ".agents/skills/grill-with-docs/SKILL.md").exists())
            self.assertTrue((repo / ".agents/skill-sources.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertFalse((repo / "AGENTS.md").exists())
            self.assertFalse((repo / ".agents/models.yml").exists())
            bootstrap = (repo / ".repo-familiar/bootstrap.yml").read_text()
            self.assertIn('skills:', bootstrap)
            self.assertIn('path: ".agents/skills/grill-with-docs/SKILL.md"', bootstrap)
            self.assertIn('path: ".agents/skill-sources.yml"', bootstrap)
            self.assertNotIn('path: "AGENTS.md"', bootstrap)

    def test_add_skill_updates_existing_skill_sources_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            with redirect_stdout(StringIO()):
                first = main(
                    [
                        "add-skill",
                        "--path",
                        str(repo),
                        "--skill",
                        "grill-with-docs",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )
            self.assertEqual(first, 0)

            with redirect_stdout(StringIO()):
                second = main(
                    [
                        "add-skill",
                        "--path",
                        str(repo),
                        "--skill",
                        "caveman",
                        "--generated-at",
                        "2026-05-11T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(second, 0)
            self.assertTrue((repo / ".agents/skills/caveman/SKILL.md").exists())
            skill_sources = (repo / ".agents/skill-sources.yml").read_text()
            self.assertIn("grill-with-docs:", skill_sources)
            self.assertIn("caveman:", skill_sources)
            bootstrap = (repo / ".repo-familiar/bootstrap.yml").read_text()
            self.assertIn('- "grill-with-docs"', bootstrap)
            self.assertIn('- "caveman"', bootstrap)
            self.assertIn('path: ".agents/skills/caveman/SKILL.md"', bootstrap)
            self.assertIn('path: ".agents/skill-sources.yml"', bootstrap)

    def test_add_tool_only_writes_tool_profile_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-tool",
                        "--path",
                        str(repo),
                        "--tool",
                        "cq",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((repo / ".agents/tools.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertFalse((repo / "AGENTS.md").exists())
            self.assertFalse((repo / ".agents/models.yml").exists())
            bootstrap = (repo / ".repo-familiar/bootstrap.yml").read_text()
            self.assertIn('tool_profiles:', bootstrap)
            self.assertIn('path: ".agents/tools.yml"', bootstrap)
            self.assertNotIn('path: "AGENTS.md"', bootstrap)

    def test_add_tool_dry_run_reports_targeted_scope_and_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-tool",
                        "--path",
                        str(repo),
                        "--tool",
                        "cq",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                    ]
                )

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("Targeted add preview:", output)
            self.assertIn("Generated assets in scope:", output)
            self.assertIn("Follow-up verification:", output)
            self.assertIn(f"repo-familiar check --path {repo}", output)

    def test_add_opencode_mcp_tool_dry_run_warns_about_out_of_scope_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-tool",
                        "--path",
                        str(repo),
                        "--tool",
                        "opencode-playwright-mcp",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                    ]
                )

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("Warnings:", output)
            self.assertIn("`opencode-playwright-mcp` also affects `opencode.json`", output)
            self.assertIn("does not currently record the `opencode` harness", output)
            self.assertIn("--agent-harness opencode", output)
            self.assertFalse((repo / "opencode.json").exists())

    def test_add_opencode_mcp_tool_apply_reports_warning_and_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-tool",
                        "--path",
                        str(repo),
                        "--tool",
                        "opencode-playwright-mcp",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("Warnings:", output)
            self.assertIn(f"repo-familiar check --path {repo}", output)
            self.assertTrue((repo / ".agents/tools.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertFalse((repo / "opencode.json").exists())

    def test_add_opencode_homebrew_tool_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-tool",
                        "--path",
                        str(repo),
                        "--tool",
                        "opencode-homebrew-path",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            tools = (repo / ".agents/tools.yml").read_text()
            self.assertIn("opencode-homebrew-path:", tools)
            self.assertIn("~/.zshenv", tools)
            self.assertIn("/opt/homebrew/bin", tools)

    def test_audit_json_output_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["audit", "--path", str(repo), "--format", "json"])

            self.assertEqual(result, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["path"], str(repo))
            self.assertEqual(payload["comparison_basis"], "default full bootstrap audit")
            self.assertEqual(payload["asset_groups"], ["all"])
            self.assertEqual(payload["selected_options"]["skills"], ["grill-with-docs"])
            self.assertEqual(payload["summary"]["present"], 0)
            self.assertGreater(len(payload["missing"]), 0)
            self.assertEqual(payload["present"], [])
            self.assertEqual(payload["conflicts"], [])

    def test_asset_group_limits_audit_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "audit",
                        "--path",
                        str(repo),
                        "--asset-group",
                        "models",
                        "--asset-group",
                        "metadata",
                        "--format",
                        "json",
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads(stdout.getvalue())
            paths = {asset["path"] for asset in payload["missing"]}
            self.assertEqual(paths, {".agents/models.yml", ".repo-familiar/bootstrap.yml"})
            self.assertEqual(payload["comparison_basis"], "scoped asset-group audit")

    def test_advise_intent_json_output_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / ".github/workflows").mkdir(parents=True)
            (repo / "tests").mkdir()
            (repo / "CONTEXT.md").write_text("# Context\n")
            (repo / "plan.md").write_text("# Plan\n")
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["advise", "--path", str(repo), "--intent", "significant-refactor", "--format", "json"])

            self.assertEqual(result, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["recommended_stage"], "implementation-planning")
            self.assertEqual(payload["intended_work"], ["significant-refactor"])
            self.assertIn("improve-codebase-architecture", payload["recommended_profiles"]["skills"])

    def test_advise_recommends_sops_for_dotenv_without_sops(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / ".env.example").write_text("# EXAMPLE=value\n")
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["advise", "--path", str(repo), "--format", "json"])

            self.assertEqual(result, 0)
            payload = json.loads(stdout.getvalue())
            self.assertIn("sops-age", payload["recommended_profiles"]["secrets_profiles"])

    def test_resolve_conflicts_previews_safe_strategies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / "AGENTS.md").write_text("# Existing Agents\n")
            (repo / ".gitignore").write_text(".env\n")
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["resolve-conflicts", "--path", str(repo), "--asset-group", "agent", "--asset-group", "config", "--format", "json"])

            self.assertEqual(result, 0)
            payload = json.loads(stdout.getvalue())
            strategies = {item["path"]: item["strategy"] for item in payload["suggestions"]}
            self.assertEqual(strategies["AGENTS.md"], "markdown-heading-merge")
            self.assertEqual(strategies[".gitignore"], "line-union")

    def test_add_model_only_writes_model_profile_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-model",
                        "--path",
                        str(repo),
                        "--model-profile",
                        "budget-review",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((repo / ".agents/models.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertFalse((repo / "AGENTS.md").exists())
            self.assertFalse((repo / ".agents/tools.yml").exists())
            models = (repo / ".agents/models.yml").read_text()
            self.assertIn("budget-review:", models)
            self.assertNotIn("default-coding:", models)

    def test_add_docs_only_writes_docs_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-docs",
                        "--path",
                        str(repo),
                        "--name",
                        "Existing Project",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((repo / "README.md").exists())
            self.assertTrue((repo / "docs/_quarto.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertFalse((repo / "AGENTS.md").exists())
            self.assertFalse((repo / ".agents/models.yml").exists())

    def test_add_memory_only_writes_memory_profile_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "add-memory",
                        "--path",
                        str(repo),
                        "--memory-profile",
                        "memory-local",
                        "--generated-at",
                        "2026-05-10T00:00:00Z",
                        "--apply",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((repo / ".agents/memory.yml").exists())
            self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
            self.assertFalse((repo / ".agents/models.yml").exists())
            self.assertIn("memory-local:", (repo / ".agents/memory.yml").read_text())

    def test_add_sandbox_design_and_worktree_profiles(self) -> None:
        command_cases = [
            ("add-sandbox", "--sandbox-profile", "sandbox-light", ".agents/sandbox.yml", "sandbox-light:"),
            ("add-secrets", "--secrets-profile", "kvenv-azure-keyvault", ".agents/secrets.yml", "kvenv-azure-keyvault:"),
            ("add-prompts", "--prompt-profile", "prompt-migration-gpt55", ".agents/prompts.yml", "prompt-migration-gpt55:"),
            ("add-safety", "--safety-profile", "prompt-output-safety", ".agents/safety.yml", "prompt-output-safety:"),
            ("add-privacy", "--privacy-profile", "data-privacy-review", ".agents/privacy.yml", "data-privacy-review:"),
            ("add-public-interest", "--public-interest-profile", "child-rights-digital", ".agents/public-interest.yml", "child-rights-digital:"),
            ("add-repomap", "--repomap-profile", "hamilton-dag", ".agents/repomap.yml", "hamilton-dag:"),
            ("add-design", "--design-profile", "design-impeccable", ".agents/design.yml", "design-impeccable:"),
            ("add-worktree", "--worktree-profile", "parallel-worktrees", ".agents/worktrees.yml", "parallel-worktrees:"),
        ]
        for command, flag, profile, generated_path, expected_text in command_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                repo = Path(tmpdir) / "existing-project"
                repo.mkdir()
                stdout = StringIO()
                with redirect_stdout(stdout):
                    result = main(
                        [
                            command,
                            "--path",
                            str(repo),
                            flag,
                            profile,
                            "--generated-at",
                            "2026-05-10T00:00:00Z",
                            "--apply",
                        ]
                    )

                self.assertEqual(result, 0)
                self.assertTrue((repo / generated_path).exists())
                self.assertTrue((repo / ".repo-familiar/bootstrap.yml").exists())
                self.assertIn(expected_text, (repo / generated_path).read_text())
                self.assertFalse((repo / ".agents/models.yml").exists())
                if command == "add-secrets":
                    self.assertTrue((repo / ".env.example").exists())

    def test_existing_bootstrap_metadata_is_present_not_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / ".repo-familiar").mkdir()
            (repo / ".repo-familiar/bootstrap.yml").write_text("schema_version: 1\n")

            report = audit_existing_repository(
                ExistingBootstrapOptions(
                    path=repo,
                    name="Existing Project",
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            self.assertIn(".repo-familiar/bootstrap.yml", {asset.path for asset in report.present})
            self.assertNotIn(".repo-familiar/bootstrap.yml", {asset.path for asset in report.conflicts})

    def test_check_generated_repository_detects_modified_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            clean_report = check_generated_repository(output_dir)
            self.assertGreater(len(clean_report.ok), 0)
            self.assertEqual(clean_report.modified, ())
            self.assertEqual(clean_report.missing, ())

            (output_dir / "AGENTS.md").write_text("changed")
            dirty_report = check_generated_repository(output_dir)
            self.assertIn("AGENTS.md", {checked.asset.path for checked in dirty_report.modified})

    def test_check_command_returns_nonzero_for_modified_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "demo-project"
            generate_project(
                GenerationOptions(
                    name="Demo Project",
                    description="A generated demo.",
                    output_dir=output_dir,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            (output_dir / "plan.md").write_text("changed")

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["check", "--path", str(output_dir), "--format", "json"])

            self.assertEqual(result, 1)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["summary"]["modified"], 1)
            self.assertEqual(payload["modified"][0]["path"], "plan.md")

    def test_advise_recommends_research_stage_for_underdocumented_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

            report = advise_existing_repository(repo)

            self.assertEqual(report.recommended_stage, "research-heavy")
            self.assertIn("memory-local", report.recommended_memory_profiles)
            self.assertIn("grill-with-docs", report.recommended_skills)
            self.assertTrue(any("At session start" in item for item in report.memory_guidance))

    def test_advise_recommends_production_stage_for_ci_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            (repo / ".github/workflows").mkdir(parents=True)
            (repo / "tests").mkdir()
            (repo / "CONTEXT.md").write_text("# Context\n")
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

            report = advise_existing_repository(repo)

            self.assertEqual(report.recommended_stage, "production-maintenance")
            self.assertIn("sandbox-agent-runtime", report.recommended_sandbox_profiles)
            self.assertIn("parallel-worktrees", report.recommended_worktree_profiles)

    def test_advise_json_output_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "existing-project"
            repo.mkdir()
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["advise", "--path", str(repo), "--format", "json"])

            self.assertEqual(result, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["path"], str(repo))
            self.assertEqual(payload["recommended_stage"], "research-heavy")
            self.assertIn("memory-local", payload["recommended_profiles"]["memory_profiles"])
            self.assertGreater(len(payload["memory_guidance"]), 0)

    def test_advise_recommends_a11y_for_web_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "web-project"
            repo.mkdir()
            (repo / "package.json").write_text('{"scripts":{"test":"echo ok"}}')
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "CONTEXT.md").write_text("# Context\n")

            report = advise_existing_repository(repo)

            self.assertIn("browser-automation", report.recommended_tool_profiles)
            self.assertIn("a11y-scanner", report.recommended_tool_profiles)
            self.assertIn("design-a11y", report.recommended_design_profiles)
            self.assertIn("playwright-cli", report.recommended_skills)
            self.assertIn("a11y-web-scan", report.recommended_skills)

    def test_advise_recommends_prompt_safety_privacy_and_hamilton(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "ai-policy-kids-education"
            repo.mkdir()
            (repo / "prompts").mkdir()
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "CONTEXT.md").write_text("# Context\n")

            report = advise_existing_repository(repo)

            self.assertIn("prompt-migration-gpt55", report.recommended_prompt_profiles)
            self.assertIn("prompt-evals-dag", report.recommended_prompt_profiles)
            self.assertIn("prompt-output-safety", report.recommended_safety_profiles)
            self.assertIn("data-privacy-review", report.recommended_privacy_profiles)
            self.assertIn("hamilton-dag", report.recommended_repomap_profiles)
            self.assertIn("prompt-migration", report.recommended_skills)
            self.assertIn("prompt-eval-design", report.recommended_skills)


if __name__ == "__main__":
    unittest.main()
