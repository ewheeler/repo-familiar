from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest

from repo_familiar import __version__
from repo_familiar.agent_plugins import plan_agent_plugin
from repo_familiar.cli import main


class AgentPluginTests(unittest.TestCase):
    def test_cli_exports_repository_map_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "repository-map-plugin"
            stdout = StringIO()

            with redirect_stdout(stdout):
                result = main(["export-plugin", "--output", str(output_dir)])

            self.assertEqual(result, 0)
            manifest = json.loads((output_dir / "plugin.json").read_text())
            self.assertEqual(
                manifest,
                {
                    "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                    "name": "repo-familiar-repository-map",
                    "version": __version__,
                    "description": "Selective semantic repository routing maps for coding agents.",
                    "license": "Apache-2.0",
                },
            )
            skill = (output_dir / "skills/repository-map/SKILL.md").read_text()
            self.assertIn("name: repository-map", skill)
            self.assertFalse((output_dir / ".agents").exists())
            self.assertIn("Exported Agent Plugin", stdout.getvalue())

    def test_planned_plugin_matches_agent_plugins_1_0_layout(self) -> None:
        assets = plan_agent_plugin()
        by_path = {asset.path: asset.content for asset in assets}

        self.assertEqual(
            set(by_path),
            {"plugin.json", "skills/repository-map/SKILL.md"},
        )
        manifest = json.loads(by_path["plugin.json"])
        self.assertEqual(
            manifest["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertRegex(
            manifest["name"],
            re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$"),
        )
        skill = by_path["skills/repository-map/SKILL.md"]
        frontmatter = skill.split("---", 2)[1]
        keys = {
            line.partition(":")[0]
            for line in frontmatter.splitlines()
            if line and not line.startswith(" ")
        }
        self.assertEqual(keys, {"name", "description"})
        self.assertIn("name: repository-map", frontmatter)

    def test_cli_refuses_nonempty_plugin_output_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "repository-map-plugin"
            output_dir.mkdir()
            existing = output_dir / "keep.txt"
            existing.write_text("keep me")

            result = main(["export-plugin", "--output", str(output_dir)])

            self.assertEqual(result, 1)
            self.assertEqual(existing.read_text(), "keep me")
            self.assertFalse((output_dir / "plugin.json").exists())


if __name__ == "__main__":
    unittest.main()
