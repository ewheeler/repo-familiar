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

    def test_recommended_commands_use_repo_familiar_module(self) -> None:
        commands = recommended_commands(
            Path("/tmp/example"),
            asset_groups=("memory", "metadata"),
            prompt_profiles=("prompt-migration-gpt55",),
            safety_profiles=(),
            privacy_profiles=(),
            repomap_profiles=(),
            sandbox_profiles=(),
            secrets_profiles=(),
            design_profiles=(),
            worktree_profiles=(),
        )

        self.assertIn("uv run python -m repo_familiar audit", commands[0])
        self.assertTrue(any("add-prompts" in command for command in commands))


if __name__ == "__main__":
    unittest.main()
