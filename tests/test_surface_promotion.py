from __future__ import annotations

import hashlib
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
from repo_familiar.generator import (
    GenerationOptions,
    check_generated_repository,
    generate_project,
)
from repo_familiar.managed_surfaces import attach_managed_surface
from repo_familiar.metadata import (
    GeneratedAsset,
    load_bootstrap_metadata,
    render_bootstrap_metadata,
)
from repo_familiar.surface_promotion import preview_surface_promotion, promote_surface


class SurfacePromotionTests(unittest.TestCase):
    def test_cli_preview_is_read_only_and_reports_selected_template_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before = metadata_path.read_text()
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "promote-surface",
                        "--path",
                        str(repo),
                        "--surface",
                        "python-runtime",
                        "--to",
                        "python-reproducible",
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            after = metadata_path.read_text()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["can_apply"])
        self.assertFalse(payload["selected_template_changed"])
        self.assertEqual(payload["written_paths"], [])
        self.assertEqual(before, after)

    def test_cli_apply_and_blocked_error_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            stdout = StringIO()
            with redirect_stdout(stdout):
                apply_exit = main(
                    [
                        "promote-surface",
                        "--path",
                        str(repo),
                        "--surface",
                        "python-runtime",
                        "--to",
                        "python-reproducible",
                        "--reference-ref",
                        "surface-cli-ref",
                        "--apply",
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")
            before_blocked = (repo / ".repo-familiar/bootstrap.yml").read_text()
            stderr = StringIO()
            with redirect_stderr(stderr):
                blocked_exit = main(
                    [
                        "promote-surface",
                        "--path",
                        str(repo),
                        "--surface",
                        "repository-foundation",
                        "--to",
                        "python-reproducible",
                        "--reference-ref",
                        "surface-cli-ref",
                        "--apply",
                    ]
                )
            after_blocked = (repo / ".repo-familiar/bootstrap.yml").read_text()

        self.assertEqual(apply_exit, 0)
        self.assertIn("pyproject.toml", payload["written_paths"])
        self.assertFalse(payload["selected_template_changed"])
        self.assertEqual(metadata.reference_ref, "surface-cli-ref")
        self.assertEqual(blocked_exit, 1)
        self.assertIn("requires manual review", stderr.getvalue())
        self.assertEqual(before_blocked, after_blocked)

    def test_promotes_missing_surface_atomically_without_changing_selected_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))

            preview = preview_surface_promotion(
                repo, "python-runtime", "python-reproducible"
            )
            first = promote_surface(
                repo,
                "python-runtime",
                "python-reproducible",
                apply=True,
                reference_ref="promotion-ref",
            )
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")
            before_second = (repo / ".repo-familiar/bootstrap.yml").read_text()
            second = promote_surface(
                repo,
                "python-runtime",
                "python-reproducible",
                apply=True,
            )
            after_second = (repo / ".repo-familiar/bootstrap.yml").read_text()
            upgrade_stdout = StringIO()
            with redirect_stdout(upgrade_stdout):
                upgrade_exit = main(
                    [
                        "upgrade",
                        "--path",
                        str(repo),
                        "--asset-group",
                        "python",
                        "--format",
                        "json",
                    ]
                )
            upgrade_payload = json.loads(upgrade_stdout.getvalue())

        self.assertTrue(preview.can_apply)
        self.assertEqual({asset.action for asset in preview.assets}, {"create"})
        self.assertIn("pyproject.toml", first.written_paths)
        self.assertIn("uv.lock", first.written_paths)
        self.assertIn(".repo-familiar/bootstrap.yml", first.written_paths)
        self.assertEqual(metadata.selected_template, "basic")
        self.assertEqual(metadata.reference_ref, "promotion-ref")
        self.assertEqual(metadata.history[-1].command, "promote-surface")
        self.assertIn("pyproject.toml", {asset.path for asset in metadata.generated_assets})
        self.assertEqual(
            next(
                surface
                for surface in metadata.managed_surfaces
                if surface.id == "python-runtime"
            ).template,
            "python-reproducible",
        )
        self.assertEqual(second.written_paths, ())
        self.assertEqual(before_second, after_second)
        self.assertEqual(upgrade_exit, 0)
        python_candidates = [
            candidate
            for group in (
                "safe_to_auto_apply",
                "needs_user_review",
                "blocked",
                "unavailable",
            )
            for candidate in upgrade_payload[group]
            if candidate["path"] == "pyproject.toml"
        ]
        self.assertEqual(len(python_candidates), 1)
        self.assertEqual(python_candidates[0]["current_reference_status"], "reference-unchanged")

    def test_manual_review_target_difference_blocks_whole_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))

            preview = preview_surface_promotion(
                repo, "repository-foundation", "python-reproducible"
            )

            self.assertFalse(preview.can_apply)
            self.assertIn("blocked", {asset.action for asset in preview.assets})
            with self.assertRaisesRegex(ValueError, "requires manual review"):
                promote_surface(
                    repo,
                    "repository-foundation",
                    "python-reproducible",
                    apply=True,
                )

    def test_checksum_clean_replaceable_surface_can_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            before_tools = (repo / ".agents/tools.yml").read_text()

            preview = preview_surface_promotion(
                repo, "agent-runtime", "python-reproducible"
            )
            result = promote_surface(
                repo,
                "agent-runtime",
                "python-reproducible",
                apply=True,
            )

            after_tools = (repo / ".agents/tools.yml").read_text()
        self.assertTrue(preview.can_apply)
        self.assertIn("replace", {asset.action for asset in preview.assets})
        self.assertIn("create", {asset.action for asset in preview.assets})
        self.assertNotEqual(before_tools, after_tools)
        self.assertIn(".agents/tools.yml", result.written_paths)

    def test_edited_path_blocks_replaceable_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            tools = repo / ".agents/tools.yml"
            tools.write_text(tools.read_text() + "# local edit\n")

            preview = preview_surface_promotion(
                repo, "agent-runtime", "python-reproducible"
            )

        self.assertFalse(preview.can_apply)
        self.assertIn("edited", {asset.status for asset in preview.assets})

    def test_extra_adopted_paths_block_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "static"
            generate_project(
                GenerationOptions(
                    name="Static Promotion",
                    description="Static promotion fixture.",
                    output_dir=repo,
                    template="static-quarto-application",
                    generated_at="2026-08-10T00:00:00Z",
                )
            )
            (repo / "service").mkdir()
            (repo / "service/legacy_api.py").write_text("legacy = True\n")
            attach_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                apply=True,
                accept_current=True,
                asset_paths=("service/legacy_api.py",),
            )

            preview = preview_surface_promotion(
                repo, "fastapi-api", "static-quarto-application"
            )

        self.assertFalse(preview.can_apply)
        self.assertEqual(preview.extra_managed_paths, ("service/legacy_api.py",))

    def test_v1_generated_extra_path_blocks_promotion_after_in_memory_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            legacy_path = repo / ".agents/legacy.yml"
            legacy_path.write_text("legacy: true\n")
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata = load_bootstrap_metadata(metadata_path)
            legacy_metadata = replace(
                metadata,
                schema_version=1,
                generated_assets=(
                    *metadata.generated_assets,
                    GeneratedAsset(
                        path=".agents/legacy.yml",
                        kind="agent_instructions",
                        source="legacy-template",
                        content_sha256=hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
                    ),
                ),
                render_context=None,
                managed_surfaces=(),
                managed_surface_assets=(),
                history=(),
            )
            metadata_path.write_text(render_bootstrap_metadata(legacy_metadata))

            preview = preview_surface_promotion(
                repo, "agent-runtime", "python-reproducible"
            )

        self.assertFalse(preview.can_apply)
        self.assertIn(".agents/legacy.yml", preview.extra_managed_paths)

    def test_checksumless_v1_asset_cannot_be_replaced(self) -> None:
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
            legacy_metadata = replace(
                metadata,
                schema_version=1,
                generated_assets=checksumless_assets,
                render_context=None,
                managed_surfaces=(),
                managed_surface_assets=(),
                history=(),
            )
            metadata_path.write_text(render_bootstrap_metadata(legacy_metadata))

            preview = preview_surface_promotion(
                repo, "agent-runtime", "python-reproducible"
            )

        tools = next(asset for asset in preview.assets if asset.path == ".agents/tools.yml")
        self.assertEqual(tools.status, "unverifiable")
        self.assertEqual(tools.action, "blocked")
        self.assertFalse(preview.can_apply)

    def test_attached_manual_review_asset_cannot_use_surface_replace_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            attach_managed_surface(
                repo,
                "agent-runtime",
                "python-reproducible",
                apply=True,
                accept_current=True,
                asset_paths=(".agents/tools.yml",),
            )

            preview = preview_surface_promotion(
                repo, "agent-runtime", "python-reproducible"
            )

        tools = next(asset for asset in preview.assets if asset.path == ".agents/tools.yml")
        self.assertEqual(tools.strategy, "manual_review")
        self.assertEqual(tools.status, "target-differs")
        self.assertEqual(tools.action, "blocked")
        self.assertFalse(preview.can_apply)

    def test_apply_refuses_dirty_git_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "snapshot"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "local.txt").write_text("dirty\n")

            with self.assertRaisesRegex(ValueError, "dirty Git worktree"):
                promote_surface(
                    repo,
                    "python-runtime",
                    "python-reproducible",
                    apply=True,
                )
            result = promote_surface(
                repo,
                "python-runtime",
                "python-reproducible",
                apply=True,
                allow_dirty=True,
            )

        self.assertIn("pyproject.toml", result.written_paths)

    def test_atomic_failure_rolls_back_surface_files_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._basic_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            before_metadata = metadata_path.read_text()
            real_replace = upgrade_module.os.replace
            calls = 0

            def fail_second_replace(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated promotion failure")
                return real_replace(source, target)

            with patch.object(
                upgrade_module.os, "replace", side_effect=fail_second_replace
            ):
                with self.assertRaisesRegex(OSError, "simulated promotion failure"):
                    promote_surface(
                        repo,
                        "python-runtime",
                        "python-reproducible",
                        apply=True,
                    )

            after_metadata = metadata_path.read_text()
            promoted_paths_exist = tuple(
                (repo / path).exists()
                for path in ("pyproject.toml", "uv.lock", ".python-version")
            )

        self.assertEqual(before_metadata, after_metadata)
        self.assertEqual(promoted_paths_exist, (False, False, False))

    def test_promotion_refuses_symlinked_parent_and_check_flags_symlinked_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = self._basic_repo(root)
            external = root / "external"
            external.mkdir()
            (repo / "config").symlink_to(external, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symlinked asset path"):
                promote_surface(
                    repo,
                    "reproducible-analysis",
                    "python-reproducible",
                    apply=True,
                )

            readme = repo / "README.md"
            original_readme = readme.read_text()
            readme.unlink()
            external_readme = external / "README.md"
            external_readme.write_text(original_readme)
            readme.symlink_to(external_readme)
            check = check_generated_repository(repo)
            external_paths = tuple(external.iterdir())

        self.assertEqual(external_paths, (external_readme,))
        self.assertIn("README.md", {item.asset.path for item in check.modified})

    def _basic_repo(self, root: Path) -> Path:
        repo = root / "basic"
        generate_project(
            GenerationOptions(
                name="Basic Promotion",
                description="Basic promotion fixture.",
                output_dir=repo,
                template="basic",
                generated_at="2026-08-10T00:00:00Z",
            )
        )
        return repo


if __name__ == "__main__":
    unittest.main()
