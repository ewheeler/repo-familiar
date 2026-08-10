from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from repo_familiar.cli import main
from repo_familiar.generator import GenerationOptions, generate_project
from repo_familiar.managed_surfaces import (
    attach_managed_surface,
    migrate_metadata_v2,
    preview_managed_surface,
    preview_template_migration,
)
from repo_familiar.metadata import (
    BootstrapMetadata,
    GeneratedAsset,
    load_bootstrap_metadata,
    render_bootstrap_metadata,
)
from repo_familiar.upgrade import preview_upgrade


class ManagedSurfaceTests(unittest.TestCase):
    def test_v1_migration_preserves_only_recorded_generated_assets(self) -> None:
        metadata = BootstrapMetadata(
            schema_version=1,
            bootstrap_mode="existing_repository",
            reference_type="local",
            reference_url="local",
            reference_ref="v1",
            generated_at="2026-08-10T00:00:00Z",
            generator_name="repo-familiar",
            generator_version="0.1.0",
            selected_template="basic",
            selected_options={"skills": ()},
            docs="quarto",
            generated_assets=(
                GeneratedAsset("AGENTS.md", "agent_instructions", "template", "abc123"),
            ),
        )

        migrated = migrate_metadata_v2(
            metadata,
            project_name="Existing",
            project_description="Existing repository.",
        )

        self.assertEqual(migrated.schema_version, 2)
        self.assertIsNotNone(migrated.render_context)
        if migrated.render_context is None:
            self.fail("Metadata v2 migration did not record render context")
        self.assertEqual(migrated.render_context.source, "inferred_from_repository")
        self.assertEqual(
            [(asset.path, asset.state) for asset in migrated.managed_surface_assets],
            [("AGENTS.md", "written")],
        )
        self.assertEqual(migrated.history[0].command, "migrate-metadata")

    def test_exact_surface_attach_writes_only_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._generated_static_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata_path.unlink()
            api_path = repo / "src/static_attach/api.py"
            original_api = api_path.read_text()

            preview = preview_managed_surface(
                repo, "fastapi-api", "static-quarto-application"
            )
            result = attach_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                apply=True,
            )

            metadata = load_bootstrap_metadata(metadata_path)
            attached_api = api_path.read_text()
        self.assertTrue(preview.can_attach_exact)
        self.assertTrue(result.metadata_written)
        self.assertEqual(attached_api, original_api)
        self.assertEqual(metadata.selected_template, "basic")
        self.assertEqual(metadata.managed_surfaces[0].state, "adopted")
        self.assertEqual(metadata.history[-1].command, "attach")

    def test_conflicting_surface_requires_explicit_current_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._generated_static_repo(Path(tmpdir))
            (repo / ".repo-familiar/bootstrap.yml").unlink()
            api_path = repo / "src/static_attach/api.py"
            api_path.write_text(api_path.read_text() + "\n# local behavior\n")

            preview = preview_managed_surface(
                repo, "fastapi-api", "static-quarto-application"
            )
            with self.assertRaisesRegex(ValueError, "--accept-current"):
                attach_managed_surface(
                    repo,
                    "fastapi-api",
                    "static-quarto-application",
                    apply=True,
                )
            attach_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                apply=True,
                accept_current=True,
            )

            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")
        self.assertIn("conflict", {asset.status for asset in preview.assets})
        self.assertEqual(
            {asset.state for asset in metadata.managed_surface_assets}, {"adopted"}
        )

    def test_partial_surface_cannot_be_attached(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._generated_static_repo(Path(tmpdir))
            (repo / ".repo-familiar/bootstrap.yml").unlink()
            (repo / "tests/test_api.py").unlink()

            preview = preview_managed_surface(
                repo, "fastapi-api", "static-quarto-application"
            )

            self.assertFalse(preview.can_attach_current)
            with self.assertRaisesRegex(ValueError, "required files are missing"):
                attach_managed_surface(
                    repo,
                    "fastapi-api",
                    "static-quarto-application",
                    apply=True,
                    accept_current=True,
                )

    def test_template_migration_is_read_only_and_surface_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "basic"
            generate_project(
                GenerationOptions(
                    name="Basic Existing",
                    description="Existing basic repository.",
                    output_dir=repo,
                    template="basic",
                    generated_at="2026-08-10T00:00:00Z",
                )
            )
            before = (repo / ".repo-familiar/bootstrap.yml").read_text()

            preview = preview_template_migration(repo, "python-reproducible")

            after = (repo / ".repo-familiar/bootstrap.yml").read_text()
        self.assertEqual(preview.current_template, "basic")
        self.assertEqual(preview.target_template, "python-reproducible")
        self.assertIn("python-runtime", {surface.surface_id for surface in preview.surfaces})
        foundation = next(
            surface
            for surface in preview.surfaces
            if surface.surface_id == "repository-foundation"
        )
        self.assertIn("target-differs", {asset.status for asset in foundation.assets})
        self.assertEqual(before, after)

    def test_attach_cli_defaults_to_json_preview_without_metadata_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = self._generated_static_repo(Path(tmpdir))
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata_path.unlink()
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "attach",
                        "--path",
                        str(repo),
                        "--surface",
                        "fastapi-api",
                        "--template",
                        "static-quarto-application",
                        "--format",
                        "json",
                    ]
                )

            payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["can_attach_exact"])
        self.assertFalse(payload["metadata_written"])
        self.assertFalse(metadata_path.exists())

    def test_metadata_migration_cli_is_preview_first_and_lossless(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / ".repo-familiar").mkdir()
            (repo / "README.md").write_text("# Legacy\n\nLegacy repository.\n")
            (repo / "AGENTS.md").write_text("# Legacy agents\n")
            metadata = BootstrapMetadata(
                schema_version=1,
                bootstrap_mode="existing_repository",
                reference_type="local",
                reference_url="local",
                reference_ref="v1",
                generated_at="2026-08-10T00:00:00Z",
                generator_name="repo-familiar",
                generator_version="0.1.0",
                selected_template="basic",
                selected_options={"skills": ()},
                docs="quarto",
                generated_assets=(
                    GeneratedAsset("AGENTS.md", "agent_instructions", "template", "abc123"),
                ),
            )
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata_path.write_text(render_bootstrap_metadata(metadata))
            before = metadata_path.read_text()

            preview_exit = main(["migrate-metadata", "--path", str(repo)])
            self.assertEqual(metadata_path.read_text(), before)
            apply_exit = main(["migrate-metadata", "--path", str(repo), "--apply"])
            migrated = load_bootstrap_metadata(metadata_path)

        self.assertEqual(preview_exit, 0)
        self.assertEqual(apply_exit, 0)
        self.assertEqual(migrated.schema_version, 2)
        self.assertEqual(migrated.generated_assets, metadata.generated_assets)
        self.assertEqual(
            [(asset.path, asset.state) for asset in migrated.managed_surface_assets],
            [("AGENTS.md", "written")],
        )

    def test_explicit_assets_attach_independent_surface_without_template_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "service").mkdir()
            (repo / "service/api.py").write_text("app = object()\n")
            (repo / "service/test_api.py").write_text("def test_api(): pass\n")

            preview = preview_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                asset_paths=("service/api.py", "service/test_api.py"),
            )
            with self.assertRaisesRegex(ValueError, "--accept-current"):
                attach_managed_surface(
                    repo,
                    "fastapi-api",
                    "static-quarto-application",
                    apply=True,
                    asset_paths=("service/api.py", "service/test_api.py"),
                )
            attach_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                apply=True,
                accept_current=True,
                asset_paths=("service/api.py", "service/test_api.py"),
            )
            metadata_path = repo / ".repo-familiar/bootstrap.yml"
            metadata = load_bootstrap_metadata(metadata_path)
            before_reattach = metadata_path.read_text()
            repeated = attach_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                apply=True,
                accept_current=True,
                asset_paths=("service/api.py",),
            )
            repeated_metadata = load_bootstrap_metadata(metadata_path)
            after_reattach = metadata_path.read_text()

        self.assertEqual({asset.status for asset in preview.assets}, {"current"})
        self.assertEqual(
            {asset.path for asset in metadata.managed_surface_assets},
            {"service/api.py", "service/test_api.py"},
        )
        self.assertFalse(repeated.metadata_written)
        self.assertEqual(before_reattach, after_reattach)
        self.assertEqual(
            {asset.path for asset in repeated_metadata.managed_surface_assets},
            {"service/api.py", "service/test_api.py"},
        )
        self.assertEqual(len(repeated_metadata.history), len(metadata.history))

    def test_explicit_assets_cannot_invent_surface_for_unrelated_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "service").mkdir()
            (repo / "service/api.py").write_text("app = object()\n")

            with self.assertRaisesRegex(
                ValueError, "does not define Managed Surface fastapi-api"
            ):
                preview_managed_surface(
                    repo,
                    "fastapi-api",
                    "basic",
                    asset_paths=("service/api.py",),
                )

    def test_upgrade_preview_includes_adopted_surface_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "service").mkdir()
            api_path = repo / "service/api.py"
            api_path.write_text("app = object()\n")
            attach_managed_surface(
                repo,
                "fastapi-api",
                "static-quarto-application",
                apply=True,
                accept_current=True,
                asset_paths=("service/api.py",),
            )

            clean = preview_upgrade(repo)
            api_path.write_text("app = object()\nchanged = True\n")
            edited = preview_upgrade(repo)

        self.assertIn(
            "service/api.py",
            {candidate.asset.path for candidate in clean.needs_user_review},
        )
        self.assertIn(
            "service/api.py", {candidate.asset.path for candidate in edited.blocked}
        )

    def _generated_static_repo(self, root: Path) -> Path:
        repo = root / "static-attach"
        generate_project(
            GenerationOptions(
                name="Static Attach",
                description="Static attach fixture.",
                output_dir=repo,
                template="static-quarto-application",
                generated_at="2026-08-10T00:00:00Z",
            )
        )
        return repo


if __name__ == "__main__":
    unittest.main()
