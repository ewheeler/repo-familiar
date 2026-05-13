from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from repo_familiar.cli import main
from repo_familiar.generator import GenerationOptions, generate_project
from repo_familiar.upstream import diff_upstream_candidate


class UpstreamDiffTests(unittest.TestCase):
    def test_classifies_modified_missing_and_unchecked_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            generate_project(
                GenerationOptions(
                    name="Generated Project",
                    description="Generated for upstream diff tests.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            (repo / "AGENTS.md").write_text("changed")
            (repo / "README.md").unlink()

            report = diff_upstream_candidate(repo)

        self.assertIn("AGENTS.md", {item.asset.path for item in report.modified})
        self.assertIn("README.md", {item.asset.path for item in report.missing})
        self.assertIn(".repo-familiar/bootstrap.yml", {item.asset.path for item in report.unchecked})
        modified = {item.asset.path: item for item in report.modified}
        self.assertEqual(modified["AGENTS.md"].recommendation, "review-for-upstream-improvement")

    def test_secret_guidance_changes_are_private_review_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            generate_project(
                GenerationOptions(
                    name="Generated Project",
                    description="Generated for upstream diff tests.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            (repo / ".env.example").write_text("OPENAI_API_KEY=secret\n")

            report = diff_upstream_candidate(repo)

        env_item = next(item for item in report.modified if item.asset.path == ".env.example")
        self.assertEqual(env_item.recommendation, "review-private-or-local-only")

    def test_cli_json_output_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            generate_project(
                GenerationOptions(
                    name="Generated Project",
                    description="Generated for upstream diff tests.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            (repo / "plan.md").write_text("changed")
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["diff-upstream-candidate", "--path", str(repo), "--format", "json"])

        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["summary"]["modified"], 1)
        self.assertEqual(payload["modified"][0]["path"], "plan.md")
        self.assertEqual(payload["modified"][0]["recommendation"], "review-for-upstream-improvement")


if __name__ == "__main__":
    unittest.main()
