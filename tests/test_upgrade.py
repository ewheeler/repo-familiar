from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from repo_familiar.cli import main
from repo_familiar.generator import GenerationOptions, generate_project
from repo_familiar.upgrade import preview_upgrade


class UpgradePreviewTests(unittest.TestCase):
    def test_clean_snapshot_has_no_auto_apply_yet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            generate_project(
                GenerationOptions(
                    name="Generated Project",
                    description="Generated for upgrade tests.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )

            report = preview_upgrade(repo)

        self.assertEqual(report.safe_to_auto_apply, ())
        self.assertGreater(len(report.needs_user_review) + len(report.blocked) + len(report.unavailable), 0)
        self.assertTrue(any("Read-only preview" in note for note in report.notes))

    def test_modified_assets_block_future_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            generate_project(
                GenerationOptions(
                    name="Generated Project",
                    description="Generated for upgrade tests.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            (repo / "AGENTS.md").write_text("changed")

            report = preview_upgrade(repo)

        self.assertIn("AGENTS.md", {item.asset.path for item in report.blocked})

    def test_upgrade_json_output_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            generate_project(
                GenerationOptions(
                    name="Generated Project",
                    description="Generated for upgrade tests.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["upgrade", "--path", str(repo), "--format", "json"])

        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("safe_to_auto_apply", payload["summary"])
        self.assertIn("Read-only preview", payload["notes"][0])


if __name__ == "__main__":
    unittest.main()
