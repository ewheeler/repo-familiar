from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import hashlib
from io import StringIO
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from repo_familiar.cli import main
from repo_familiar import cli as cli_module
from repo_familiar.asset_plan import PlannedAsset
from repo_familiar.generator import GenerationOptions, check_generated_repository, generate_project, plan_project
from repo_familiar.metadata import GeneratedAsset, load_bootstrap_metadata, render_bootstrap_metadata
from repo_familiar import upgrade as upgrade_module
from repo_familiar.upgrade import apply_upgrade, preview_upgrade


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

    def test_skills_preview_marks_unchanged_vendored_skill_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated skill\n")

            report = preview_upgrade(
                repo,
                _generated_assets(current),
                asset_groups=("skills",),
            )

        self.assertEqual(
            {item.asset.path for item in report.safe_to_auto_apply},
            {".agents/skills/ponytail/SKILL.md"},
        )
        self.assertEqual(report.safe_to_auto_apply[0].strategy, "replace_if_unchanged")

    def test_skills_preview_preserves_modified_vendored_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            (repo / ".agents/skills/ponytail/SKILL.md").write_text("local edit\n")
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated skill\n")

            report = preview_upgrade(repo, _generated_assets(current), asset_groups=("skills",))

        self.assertIn(
            ".agents/skills/ponytail/SKILL.md",
            {item.asset.path for item in report.needs_user_review},
        )

    def test_skills_preview_adds_new_missing_support_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = plan_project(options)
            current.append(
                PlannedAsset(
                    path=".agents/skills/ponytail/REFERENCE.md",
                    kind="skill",
                    source="templates/skills/ponytail/REFERENCE.md.tmpl",
                    content="new support\n",
                )
            )

            report = preview_upgrade(repo, _generated_assets(current), asset_groups=("skills",))

        candidate = next(item for item in report.safe_to_auto_apply if item.asset.path.endswith("REFERENCE.md"))
        self.assertEqual(candidate.strategy, "add_missing_support_file")

    def test_skills_apply_updates_safe_assets_sources_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail", "prototype"),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            local_prototype = repo / ".agents/skills/prototype/SKILL.md"
            local_prototype.write_text("local prototype edit\n")
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated ponytail\n")
            current = _replace_plan_content(current, ".agents/skills/prototype/SKILL.md", "updated prototype\n")
            current = _replace_plan_content(
                current,
                ".agents/skill-sources.yml",
                "skills:\n  ponytail:\n    source_type: \"external\"\n    source_url: \"https://example.invalid/ponytail\"\n",
            )
            current.append(
                PlannedAsset(
                    path=".agents/skills/ponytail/REFERENCE.md",
                    kind="skill",
                    source="templates/skills/ponytail/REFERENCE.md.tmpl",
                    content="new support\n",
                )
            )

            result = apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))

            self.assertEqual((repo / ".agents/skills/ponytail/SKILL.md").read_text(), "updated ponytail\n")
            self.assertEqual(local_prototype.read_text(), "local prototype edit\n")
            self.assertEqual((repo / ".agents/skills/ponytail/REFERENCE.md").read_text(), "new support\n")
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")
            check = check_generated_repository(repo)
            second_result = apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))

        written = set(result.written_paths)
        self.assertIn(".agents/skill-sources.yml", written)
        self.assertIn(".repo-familiar/bootstrap.yml", written)
        self.assertIn(".agents/skills/ponytail/REFERENCE.md", {asset.path for asset in metadata.generated_assets})
        self.assertEqual({item.asset.path for item in check.modified}, {".agents/skills/prototype/SKILL.md"})
        self.assertEqual(check.missing, ())
        self.assertEqual(second_result.written_paths, ())

    def test_preview_reports_conservative_non_skill_merge_strategies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = plan_project(options)
            for path in (".agents/tools.yml", ".gitignore", "AGENTS.md", "README.md", "docs/index.qmd"):
                current = _replace_plan_content(current, path, f"updated {path}\n")
            current.append(
                PlannedAsset(
                    path="docs/new-guide.qmd",
                    kind="documentation",
                    source="templates/basic/docs/new-guide.qmd.tmpl",
                    content="new guide\n",
                )
            )

            report = preview_upgrade(repo, _generated_assets(current))

        strategies = {
            item.asset.path: item.strategy
            for item in (*report.safe_to_auto_apply, *report.needs_user_review, *report.blocked, *report.unavailable)
        }
        self.assertEqual(strategies[".agents/tools.yml"], "mapping_merge_preview")
        self.assertEqual(strategies[".gitignore"], "line_union_preview")
        self.assertEqual(strategies["AGENTS.md"], "heading_merge_preview")
        self.assertEqual(strategies["README.md"], "manual_review")
        self.assertEqual(strategies["docs/index.qmd"], "manual_review")
        self.assertEqual(strategies["docs/new-guide.qmd"], "add_if_missing_preview")

    def test_cli_accepts_skills_preview_flags(self) -> None:
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
                result = main(["upgrade", "--path", str(repo), "--asset-group", "skills", "--preview"])

        self.assertEqual(result, 0)
        self.assertIn("Asset groups: skills", stdout.getvalue())

    def test_skill_sources_merge_preserves_other_top_level_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            sources = repo / ".agents/skill-sources.yml"
            existing_sources = sources.read_text().replace(
                '    notes: "Adapted from DietrichGebert/ponytail for repo-familiar selectable skill guidance."',
                '    notes: "Adapted from DietrichGebert/ponytail for repo-familiar selectable skill guidance."\n'
                '    custom_note: "preserve downstream field"',
            )
            sources.write_text(f"# keep me\n{existing_sources}\ncustom:\n  owner: downstream\n")
            current = _replace_plan_content(
                plan_project(options),
                ".agents/skill-sources.yml",
                "skills:\n  ponytail:\n    source_type: \"external\"\n    source_url: \"https://example.invalid/new\"\n",
            )

            apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))
            merged = sources.read_text()

        self.assertIn("# keep me", merged)
        self.assertIn("custom:\n  owner: downstream", merged)
        self.assertIn("https://example.invalid/new", merged)
        self.assertIn('custom_note: "preserve downstream field"', merged)

    def test_upgrade_refuses_symlinked_skill_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            target = repo / ".agents/skills/ponytail/SKILL.md"
            outside = root / "outside.md"
            outside.write_text("outside\n")
            target.unlink()
            target.symlink_to(outside)
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated\n")

            with self.assertRaisesRegex(ValueError, "symlinked asset path"):
                apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))
            self.assertEqual(outside.read_text(), "outside\n")

    def test_empty_skill_source_mapping_stays_a_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=(),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = plan_project(options)

            apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))

            self.assertIn("skills: {}", (repo / ".agents/skill-sources.yml").read_text())

    def test_symlinked_metadata_blocks_before_skill_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            skill = repo / ".agents/skills/ponytail/SKILL.md"
            original_skill = skill.read_text()
            metadata = repo / ".repo-familiar/bootstrap.yml"
            outside_metadata = root / "bootstrap.yml"
            outside_metadata.write_text(metadata.read_text())
            metadata.unlink()
            metadata.symlink_to(outside_metadata)
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated\n")

            with self.assertRaisesRegex(ValueError, "symlinked asset path"):
                apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))

            self.assertEqual(skill.read_text(), original_skill)

    def test_inline_skill_source_mapping_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            sources = repo / ".agents/skill-sources.yml"
            inline = 'skills: {ponytail: {source_type: "local-adapted"}}\n'
            sources.write_text(inline)
            skill = repo / ".agents/skills/ponytail/SKILL.md"
            original_skill = skill.read_text()
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated\n")

            with self.assertRaisesRegex(ValueError, "Inline YAML mappings are not supported"):
                apply_upgrade(repo, {asset.path: asset for asset in current}, asset_groups=("skills",))

            self.assertEqual(sources.read_text(), inline)
            self.assertEqual(skill.read_text(), original_skill)

    def test_cli_preview_reuses_unchanged_readme_render_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "different-directory-name"
            generate_project(
                GenerationOptions(
                    name="Display Name",
                    description="Original description.",
                    output_dir=repo,
                    generated_at="2026-05-10T00:00:00Z",
                )
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(["upgrade", "--path", str(repo), "--preview", "--format", "json"])

        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        review_paths = {item["path"] for item in payload["needs_user_review"]}
        self.assertNotIn("README.md", review_paths)

    def test_cli_apply_requires_skills_asset_group(self) -> None:
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
            stderr = StringIO()
            with redirect_stderr(stderr):
                result = main(["upgrade", "--path", str(repo), "--apply", "--reference-ref", "test-ref"])

        self.assertEqual(result, 1)
        self.assertIn("requires --asset-group skills", stderr.getvalue())

    def test_removed_reference_skill_asset_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("tdd",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = [asset for asset in plan_project(options) if not asset.path.endswith("/tdd/mocking.md")]

            report = preview_upgrade(repo, _generated_assets(current), asset_groups=("skills",))

        removed = next(item for item in report.blocked if item.asset.path.endswith("/tdd/mocking.md"))
        self.assertEqual(removed.status, "source-removed")
        self.assertEqual(removed.recommendation, "review-removed-reference-asset")

    def test_apply_records_current_reference_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated\n")

            apply_upgrade(
                repo,
                {asset.path: asset for asset in current},
                asset_groups=("skills",),
                reference_ref="new-reference-sha",
            )
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")

        self.assertEqual(metadata.reference_ref, "new-reference-sha")

    def test_cli_apply_end_to_end_is_safe_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail", "liteparse"),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            ponytail = repo / ".agents/skills/ponytail/SKILL.md"
            ponytail.write_text("old ponytail\n")
            support_path = ".agents/skills/liteparse/scripts/search.py"
            (repo / support_path).unlink()
            _rewrite_metadata(
                repo,
                replacements={
                    ".agents/skills/ponytail/SKILL.md": GeneratedAsset(
                        path=".agents/skills/ponytail/SKILL.md",
                        kind="skill",
                        source="templates/skills/ponytail/SKILL.md.tmpl",
                        content_sha256=_sha256("old ponytail\n"),
                    )
                },
                removed={support_path},
            )
            _git_init_commit(repo, "old generated snapshot")

            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "upgrade", "--path", str(repo), "--asset-group", "skills", "--apply",
                        "--reference-ref", "pilot-ref", "--format", "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            metadata = load_bootstrap_metadata(repo / ".repo-familiar/bootstrap.yml")
            check = check_generated_repository(repo)
            _git_commit(repo, "applied upgrade")

            second_stdout = StringIO()
            with redirect_stdout(second_stdout):
                second_result = main(
                    [
                        "upgrade", "--path", str(repo), "--asset-group", "skills", "--apply",
                        "--reference-ref", "pilot-ref", "--format", "json",
                    ]
                )

        self.assertEqual(result, 0)
        self.assertEqual(second_result, 0)
        self.assertIn(support_path, payload["written_paths"])
        self.assertEqual(metadata.reference_ref, "pilot-ref")
        self.assertEqual(check.modified, ())
        self.assertEqual(check.missing, ())
        self.assertEqual(json.loads(second_stdout.getvalue())["written_paths"], [])

    def test_cli_apply_refuses_dirty_git_worktree_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            _git_init_commit(repo, "generated snapshot")
            (repo / "local.txt").write_text("dirty\n")
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(
                    [
                        "upgrade", "--path", str(repo), "--asset-group", "skills", "--apply",
                        "--reference-ref", "test-ref",
                    ]
                )
            with redirect_stdout(StringIO()):
                override_result = main(
                    [
                        "upgrade", "--path", str(repo), "--asset-group", "skills", "--apply",
                        "--reference-ref", "test-ref", "--allow-dirty",
                    ]
                )

        self.assertEqual(result, 1)
        self.assertEqual(override_result, 0)
        self.assertIn("dirty Git worktree", stderr.getvalue())
        self.assertIn("--allow-dirty", stderr.getvalue())

    def test_apply_rolls_back_all_files_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated\n")
            tracked_paths = (
                ".agents/skills/ponytail/SKILL.md",
                ".agents/skill-sources.yml",
                ".repo-familiar/bootstrap.yml",
            )
            before = {path: (repo / path).read_text() for path in tracked_paths}
            skill_path = repo / ".agents/skills/ponytail/SKILL.md"
            skill_path.chmod(0o755)
            real_replace = upgrade_module.os.replace
            calls = 0

            def fail_second_replace(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated replace failure")
                return real_replace(source, target)

            with patch.object(upgrade_module.os, "replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    apply_upgrade(
                        repo,
                        {asset.path: asset for asset in current},
                        asset_groups=("skills",),
                        reference_ref="new-ref",
                    )

            after = {path: (repo / path).read_text() for path in tracked_paths}
            rolled_back_mode = skill_path.stat().st_mode & 0o777

        self.assertEqual(after, before)
        self.assertEqual(rolled_back_mode, 0o755)

    def test_apply_preserves_existing_file_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            skill = repo / ".agents/skills/ponytail/SKILL.md"
            skill.chmod(0o755)
            current = _changed_plan(options, ".agents/skills/ponytail/SKILL.md", "updated\n")

            apply_upgrade(
                repo,
                {asset.path: asset for asset in current},
                asset_groups=("skills",),
                reference_ref="new-ref",
            )

            mode = skill.stat().st_mode & 0o777

        self.assertEqual(mode, 0o755)

    def test_reference_provenance_fails_closed_for_broken_source_checkout(self) -> None:
        error = subprocess.CalledProcessError(1, ["git", "status"])
        with patch.object(cli_module.subprocess, "run", side_effect=error):
            with self.assertRaisesRegex(ValueError, "Unable to verify Reference Source provenance"):
                cli_module._current_reference_ref()

    def test_apply_fails_closed_for_broken_downstream_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "generated"
            options = GenerationOptions(
                name="Generated Project",
                description="Generated for upgrade tests.",
                output_dir=repo,
                skills=("ponytail",),
                generated_at="2026-05-10T00:00:00Z",
            )
            generate_project(options)
            (repo / ".git").mkdir()
            current = plan_project(options)

            with self.assertRaisesRegex(ValueError, "Git metadata is present but invalid"):
                apply_upgrade(
                    repo,
                    {asset.path: asset for asset in current},
                    asset_groups=("skills",),
                    reference_ref="new-ref",
                )


def _changed_plan(options: GenerationOptions, path: str, content: str) -> list[PlannedAsset]:
    return _replace_plan_content(plan_project(options), path, content)


def _replace_plan_content(assets: list[PlannedAsset], path: str, content: str) -> list[PlannedAsset]:
    return [
        PlannedAsset(asset.path, asset.kind, asset.source, content if asset.path == path else asset.content)
        for asset in assets
    ]


def _generated_assets(assets: list[PlannedAsset]):
    return {asset.path: asset.as_generated_asset() for asset in assets}


def _rewrite_metadata(
    repo: Path,
    *,
    replacements: dict[str, GeneratedAsset],
    removed: set[str],
) -> None:
    path = repo / ".repo-familiar/bootstrap.yml"
    metadata = load_bootstrap_metadata(path)
    assets = {
        asset.path: asset
        for asset in metadata.generated_assets
        if asset.path not in removed
    }
    assets.update(replacements)
    path.write_text(render_bootstrap_metadata(replace(metadata, generated_assets=tuple(assets[key] for key in sorted(assets)))))


def _git_init_commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    _git_commit(repo, message)


def _git_commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Upgrade Test", "-c", "user.email=upgrade@example.invalid", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


if __name__ == "__main__":
    unittest.main()
