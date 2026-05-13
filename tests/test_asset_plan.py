from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from repo_familiar.asset_plan import (
    BOOTSTRAP_METADATA_PATH,
    PlannedAsset,
    asset_kind,
    filter_planned_assets,
    plan_skill_assets,
    plan_template_assets,
)


class AssetPlanTests(unittest.TestCase):
    def test_plans_template_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            template_root = Path(tmpdir) / "basic"
            docs = template_root / "docs"
            docs.mkdir(parents=True)
            (template_root / "README.md.tmpl").write_text("# $project_name\n")
            (docs / "index.qmd.tmpl").write_text("# $project_name docs\n")

            assets = plan_template_assets(template_root, "basic", {"project_name": "Demo"})

        paths = {asset.path for asset in assets}
        self.assertEqual(paths, {"README.md", "docs/index.qmd"})
        self.assertIn("# Demo", {asset.content.strip() for asset in assets})

    def test_plans_skill_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir) / "skills"
            skill_root = skills_root / "demo-skill"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md.tmpl").write_text("# $project_name\n")

            assets = plan_skill_assets(skills_root, ("demo-skill",), {"project_name": "Demo"})

        self.assertEqual(assets[0].path, ".agents/skills/demo-skill/SKILL.md")
        self.assertEqual(assets[0].kind, "skill")
        self.assertEqual(assets[0].content, "# Demo\n")

    def test_filters_asset_groups(self) -> None:
        assets = [
            PlannedAsset(path=".agents/tools.yml", kind="template_config", source="test", content=""),
            PlannedAsset(path="README.md", kind="documentation", source="test", content=""),
            PlannedAsset(path=BOOTSTRAP_METADATA_PATH, kind="metadata", source="test", content=""),
        ]

        filtered = filter_planned_assets(assets, ("tools", "metadata"))

        self.assertEqual([asset.path for asset in filtered], [".agents/tools.yml", BOOTSTRAP_METADATA_PATH])

    def test_generated_asset_checksum_distinguishes_metadata(self) -> None:
        docs_asset = PlannedAsset(path="README.md", kind="documentation", source="test", content="hello")
        metadata_asset = PlannedAsset(path=BOOTSTRAP_METADATA_PATH, kind="metadata", source="test", content="hello")

        self.assertIsNotNone(docs_asset.as_generated_asset().content_sha256)
        self.assertIsNone(metadata_asset.as_generated_asset().content_sha256)

    def test_asset_groups_cover_diff_upstream_candidate_inputs(self) -> None:
        assets = [
            PlannedAsset(path=".gitignore", kind="template_config", source="test", content=""),
            PlannedAsset(path=".env.example", kind="template_config", source="test", content=""),
            PlannedAsset(path=".agents/secrets.yml", kind="template_config", source="test", content=""),
            PlannedAsset(path=".agents/skill-sources.yml", kind="template_config", source="test", content=""),
            PlannedAsset(path=".agents/skills/demo/SKILL.md", kind="skill", source="test", content=""),
            PlannedAsset(path="docs/index.qmd", kind="documentation", source="test", content=""),
            PlannedAsset(path="README.md", kind="documentation", source="test", content=""),
            PlannedAsset(path="AGENTS.md", kind="agent_instructions", source="test", content=""),
            PlannedAsset(path="plan.md", kind="project_plan", source="test", content=""),
        ]

        self.assertEqual(
            [asset.path for asset in filter_planned_assets(assets, ("secrets",))],
            [".env.example", ".agents/secrets.yml"],
        )
        self.assertEqual(
            [asset.path for asset in filter_planned_assets(assets, ("skills",))],
            [".agents/skill-sources.yml", ".agents/skills/demo/SKILL.md"],
        )
        self.assertEqual(
            [asset.path for asset in filter_planned_assets(assets, ("docs",))],
            ["docs/index.qmd", "README.md"],
        )
        self.assertEqual(
            [asset.path for asset in filter_planned_assets(assets, ("agent", "plan", "config"))],
            [".gitignore", "AGENTS.md", "plan.md"],
        )

    def test_all_asset_group_returns_original_plan(self) -> None:
        assets = [
            PlannedAsset(path="README.md", kind="documentation", source="test", content=""),
            PlannedAsset(path=BOOTSTRAP_METADATA_PATH, kind="metadata", source="test", content=""),
        ]

        self.assertIs(filter_planned_assets(assets, ("all",)), assets)

    def test_unknown_asset_kind_is_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Template has no generated asset kind"):
            asset_kind("UNKNOWN.md")


if __name__ == "__main__":
    unittest.main()
