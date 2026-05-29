from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from repo_familiar.advice import advise_existing_repository, detect_repository_signals, recommended_commands


class AdviceTests(unittest.TestCase):
    def test_detects_repository_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "CONTEXT.md").write_text("# Context\n")
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "package.json").write_text("{}")

            signals = detect_repository_signals(repo)

        self.assertTrue(signals.has_context)
        self.assertTrue(signals.has_plan)
        self.assertTrue(signals.has_frontend)

    def test_recommends_browser_automation_for_web_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "CONTEXT.md").write_text("# Context\n")
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "package.json").write_text("{}")

            report = advise_existing_repository(repo)

        self.assertIn("browser-automation", report.recommended_tool_profiles)
        self.assertIn("playwright-cli", report.recommended_skills)

    def test_intended_refactor_adjusts_stage_and_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / ".github/workflows").mkdir(parents=True)
            (repo / "tests").mkdir()
            (repo / "CONTEXT.md").write_text("# Context\n")
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

            report = advise_existing_repository(repo, ("significant-refactor",))

        self.assertEqual(report.recommended_stage, "implementation-planning")
        self.assertIn("improve-codebase-architecture", report.recommended_skills)
        self.assertIn("qa-test-design", report.recommended_skills)
        self.assertIn("significant-refactor", report.intended_work)

    def test_asset_groups_include_recommended_profile_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "ai-policy-kids-education"
            repo.mkdir()
            (repo / "prompts").mkdir()
            (repo / "CONTEXT.md").write_text("# Context\n")
            (repo / "plan.md").write_text("# Plan\n")
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

            report = advise_existing_repository(repo, ("significant-refactor",))

        self.assertIn("prompts", report.recommended_asset_groups)
        self.assertIn("safety", report.recommended_asset_groups)
        self.assertIn("privacy", report.recommended_asset_groups)
        self.assertIn("public-interest", report.recommended_asset_groups)
        self.assertIn("repomap", report.recommended_asset_groups)

    def test_research_advice_includes_model_and_tool_asset_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            repo.mkdir(exist_ok=True)

            report = advise_existing_repository(repo)

        self.assertIn("default-coding", report.recommended_model_profiles)
        self.assertIn("cq", report.recommended_tool_profiles)
        self.assertIn("models", report.recommended_asset_groups)
        self.assertIn("tools", report.recommended_asset_groups)

    def test_recommended_commands_use_repo_familiar_module(self) -> None:
        commands = recommended_commands(
            Path("/tmp/example"),
            asset_groups=("memory", "metadata"),
            skills=("cq",),
            prompt_profiles=("prompt-migration-gpt55",),
            safety_profiles=(),
            privacy_profiles=(),
            repomap_profiles=(),
            sandbox_profiles=(),
            secrets_profiles=(),
            design_profiles=(),
            worktree_profiles=(),
            public_interest_profiles=(),
        )

        self.assertIn("uv run python -m repo_familiar audit", commands[0])
        self.assertTrue(any("add-skill" in command and "cq" in command for command in commands))
        self.assertTrue(any("add-prompts" in command for command in commands))


if __name__ == "__main__":
    unittest.main()
