from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from repo_familiar import upgrade as upgrade_module
from repo_familiar.cli import main
from repo_familiar.generator import GenerationOptions, generate_project
from repo_familiar.managed_surfaces import attach_managed_surface, plan_surface_target
from repo_familiar.metadata import load_bootstrap_metadata, render_bootstrap_metadata
from repo_familiar.template_promotion import (
    SURFACE_PROMOTION_ORDER,
    preview_template_promotion,
    promote_template,
)


class TemplatePromotionTests(unittest.TestCase):
    def test_cli_broad_preview_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before = metadata_path.read_text()
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "promote-template",
                        "--path",
                        str(repo),
                        "--to",
                        "python-reproducible",
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            after = metadata_path.read_text()

        self.assertEqual(exit_code, 0)
        self.assertFalse(payload["can_apply"])
        self.assertFalse(payload["selected_template_changed"])
        self.assertEqual(payload["written_paths"], [])
        self.assertEqual(before, after)

    def test_cli_apply_and_blocked_error_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prepared = self._prepared_basic_repo(root / "prepared-root")
            stdout = StringIO()
            with redirect_stdout(stdout):
                apply_exit = main(
                    [
                        "promote-template",
                        "--path",
                        str(prepared),
                        "--to",
                        "python-reproducible",
                        "--reference-ref",
                        "template-cli-ref",
                        "--apply",
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            promoted = load_bootstrap_metadata(
                prepared / ".repo-familiar/bootstrap.yml"
            )

            blocked = self._basic_repo(root / "blocked-root")
            blocked_metadata = blocked / ".repo-familiar/bootstrap.yml"
            before_blocked = blocked_metadata.read_text()
            stderr = StringIO()
            with redirect_stderr(stderr):
                blocked_exit = main(
                    [
                        "promote-template",
                        "--path",
                        str(blocked),
                        "--to",
                        "python-reproducible",
                        "--reference-ref",
                        "template-cli-ref",
                        "--apply",
                    ]
                )
            after_blocked = blocked_metadata.read_text()

        self.assertEqual(apply_exit, 0)
        self.assertTrue(payload["selected_template_changed"])
        self.assertEqual(promoted.selected_template, "python-reproducible")
        self.assertEqual(promoted.reference_ref, "template-cli-ref")
        self.assertEqual(blocked_exit, 1)
        self.assertIn("requires manual review", stderr.getvalue())
        self.assertEqual(before_blocked, after_blocked)

    def test_broad_preview_is_blocked_until_manual_surfaces_are_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before = metadata_path.read_text()

            preview = preview_template_promotion(repo, "python-reproducible")

            with self.assertRaisesRegex(ValueError, "manual review"):
                promote_template(repo, "python-reproducible", apply=True)

            after = metadata_path.read_text()
            pyproject_exists = (repo / "pyproject.toml").exists()
        self.assertFalse(preview.can_apply)
        self.assertTrue(
            any("manual review" in blocker for blocker in preview.blockers)
        )
        self.assertEqual(before, after)
        self.assertFalse(pyproject_exists)

    def test_checksumless_v1_asset_blocks_broad_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata = load_bootstrap_metadata(metadata_path)
            checksumless_assets = tuple(
                replace(asset, content_sha256=None)
                if asset.path == ".agents/tools.yml"
                else asset
                for asset in metadata.generated_assets
            )
            metadata_path.write_text(
                render_bootstrap_metadata(
                    replace(
                        metadata,
                        schema_version=1,
                        generated_assets=checksumless_assets,
                        render_context=None,
                        managed_surfaces=(),
                        managed_surface_assets=(),
                        history=(),
                    )
                )
            )

            preview = preview_template_promotion(repo, "python-reproducible")

        agent_surface = next(
            surface
            for surface in preview.surfaces
            if surface.surface_id == "agent-runtime"
        )
        tools = next(
            asset for asset in agent_surface.assets if asset.path == ".agents/tools.yml"
        )
        self.assertEqual(tools.status, "unverifiable")
        self.assertEqual(tools.action, "blocked")
        self.assertFalse(preview.can_apply)

    def test_promotes_all_surfaces_atomically_and_finalizes_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._prepared_basic_repo(Path(tmpdir))

            preview = preview_template_promotion(repo, "python-reproducible")
            first = promote_template(
                repo,
                "python-reproducible",
                apply=True,
                reference_ref="broad-promotion-ref",
            )
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")
            before_second = (repo / ".repo-familiar/bootstrap.yml").read_text()
            second = promote_template(repo, "python-reproducible", apply=True)
            after_second = (repo / ".repo-familiar/bootstrap.yml").read_text()

        expected_order = tuple(
            surface_id
            for surface_id in SURFACE_PROMOTION_ORDER
            if surface_id
            in {
                "repository-foundation",
                "agent-runtime",
                "python-runtime",
                "quality-and-ci",
                "reproducible-analysis",
                "divio-documentation",
            }
        )
        self.assertTrue(preview.can_apply)
        self.assertEqual(
            tuple(surface.surface_id for surface in preview.surfaces), expected_order
        )
        self.assertIn("pyproject.toml", first.written_paths)
        self.assertIn(".repo-familiar/bootstrap.yml", first.written_paths)
        self.assertTrue(first.selected_template_changed)
        self.assertEqual(metadata.selected_template, "python-reproducible")
        self.assertEqual(metadata.reference_ref, "broad-promotion-ref")
        self.assertEqual(
            tuple(
                operation.surface_id
                for operation in metadata.history
                if operation.command == "promote-template"
            ),
            expected_order,
        )
        self.assertEqual(second.written_paths, ())
        self.assertFalse(second.selected_template_changed)
        self.assertEqual(before_second, after_second)

    def test_downgrade_blocks_when_target_omits_managed_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "static"
            generate_project(
                GenerationOptions(
                    name="Static Existing",
                    description="Static existing repository.",
                    output_dir=repo,
                    template="static-quarto-application",
                    generated_at="2026-08-10T00:00:00Z",
                )
            )

            preview = preview_template_promotion(repo, "python-reproducible")
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before = metadata_path.read_text()
            app_before = (repo / "app/index.qmd").read_text()
            with self.assertRaisesRegex(ValueError, "never deletes"):
                promote_template(repo, "python-reproducible", apply=True)
            after = metadata_path.read_text()
            app_after = (repo / "app/index.qmd").read_text()

        self.assertFalse(preview.can_apply)
        self.assertEqual(
            set(preview.removed_surface_ids),
            {"fastapi-api", "quarto-static-client"},
        )
        self.assertEqual(before, after)
        self.assertEqual(app_before, app_after)

    def test_broad_finalization_preserves_per_asset_manual_review_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._prepared_basic_repo(Path(tmpdir))
            agent_target = plan_surface_target(
                repo, "agent-runtime", "python-reproducible"
            )
            tools_target = next(
                asset for asset in agent_target.assets if asset.path == ".agents/tools.yml"
            )
            (repo / tools_target.path).write_text(tools_target.content)
            attach_managed_surface(
                repo,
                "agent-runtime",
                "python-reproducible",
                apply=True,
                accept_current=True,
                asset_paths=(tools_target.path,),
            )

            preview = preview_template_promotion(repo, "python-reproducible")
            promote_template(repo, "python-reproducible", apply=True)
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")

        self.assertTrue(preview.can_apply)
        managed_tools = next(
            asset
            for asset in metadata.managed_surface_assets
            if asset.path == ".agents/tools.yml"
        )
        self.assertEqual(managed_tools.strategy, "manual_review")
        self.assertEqual(managed_tools.state, "adopted")
        self.assertNotIn(
            ".agents/tools.yml", {asset.path for asset in metadata.generated_assets}
        )

    def test_atomic_failure_rolls_back_all_surfaces_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._prepared_basic_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before_metadata = metadata_path.read_text()
            real_replace = upgrade_module.os.replace
            calls = 0

            def fail_third_replace(source, target):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("simulated broad promotion failure")
                return real_replace(source, target)

            with patch.object(
                upgrade_module.os, "replace", side_effect=fail_third_replace
            ):
                with self.assertRaisesRegex(
                    OSError, "simulated broad promotion failure"
                ):
                    promote_template(repo, "python-reproducible", apply=True)

            after_metadata = metadata_path.read_text()
            promoted_paths_exist = tuple(
                (repo / path).exists()
                for path in ("pyproject.toml", "uv.lock", ".python-version")
            )
            promoted_directories_exist = tuple(
                (repo / path).exists()
                for path in (".github", "config", "data", "src", "tests")
            )

        self.assertEqual(before_metadata, after_metadata)
        self.assertEqual(promoted_paths_exist, (False, False, False))
        self.assertEqual(promoted_directories_exist, (False, False, False, False, False))

    def test_broad_apply_refuses_dirty_git_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._prepared_basic_repo(Path(tmpdir))
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-m",
                    "snapshot",
                ],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "local.txt").write_text("dirty\n")

            with self.assertRaisesRegex(ValueError, "dirty Git worktree"):
                promote_template(repo, "python-reproducible", apply=True)
            result = promote_template(
                repo,
                "python-reproducible",
                apply=True,
                allow_dirty=True,
            )

        self.assertIn("pyproject.toml", result.written_paths)

    def test_apply_repairs_stale_finalization_metadata_instead_of_false_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "python"
            generate_project(
                GenerationOptions(
                    name="Stale Finalization",
                    description="Stale finalization fixture.",
                    output_dir=repo,
                    template="python-reproducible",
                    generated_at="2026-08-10T00:00:00Z",
                )
            )
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata = load_bootstrap_metadata(metadata_path)
            stale_options = dict(metadata.selected_options)
            stale_options["skills"] = ()
            stale = replace(metadata, selected_options=stale_options)
            metadata_path.write_text(render_bootstrap_metadata(stale))

            result = promote_template(repo, "python-reproducible", apply=True)
            repaired = load_bootstrap_metadata(metadata_path)

        self.assertEqual(result.written_paths, (".repo-familiar/bootstrap.yml",))
        self.assertFalse(result.selected_template_changed)
        self.assertIn("reproducible-data-science", repaired.selected_options["skills"])
        self.assertEqual(repaired.history[-1].command, "promote-template")

    def test_same_template_apply_is_true_noop_without_history_churn(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "python"
            generate_project(
                GenerationOptions(
                    name="Already Conformant",
                    description="Already conformant fixture.",
                    output_dir=repo,
                    template="python-reproducible",
                    generated_at="2026-08-10T00:00:00Z",
                )
            )
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before = metadata_path.read_text()
            before_history = load_bootstrap_metadata(metadata_path).history

            result = promote_template(repo, "python-reproducible", apply=True)
            after = metadata_path.read_text()
            after_history = load_bootstrap_metadata(metadata_path).history

        self.assertEqual(result.written_paths, ())
        self.assertFalse(result.selected_template_changed)
        self.assertEqual(before, after)
        self.assertEqual(before_history, after_history)

    def _prepared_basic_repo(self, root: Path) -> Path:
        repo = self._basic_repo(root)
        for surface_id in ("repository-foundation", "divio-documentation"):
            target = plan_surface_target(
                repo, surface_id, "python-reproducible"
            )
            for asset in target.assets:
                target_path = repo / asset.path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(asset.content)
            attach_managed_surface(
                repo,
                surface_id,
                "python-reproducible",
                apply=True,
                accept_current=True,
            )
        return repo

    def _basic_repo(self, root: Path) -> Path:
        repo = root / "basic"
        generate_project(
            GenerationOptions(
                name="Broad Promotion",
                description="Broad promotion fixture.",
                output_dir=repo,
                template="basic",
                generated_at="2026-08-10T00:00:00Z",
            )
        )
        return repo


if __name__ == "__main__":
    unittest.main()
