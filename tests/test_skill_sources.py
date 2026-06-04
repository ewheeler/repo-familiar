from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from repo_familiar.skill_sources import check_skill_sources, parse_skill_sources


class SkillSourceCheckTests(unittest.TestCase):
    def test_parses_skill_source_records(self) -> None:
        records = parse_skill_sources(
            """skills:
  demo:
    source_type: "external"
    source_url: "https://github.com/example/project/blob/main/skills/demo/SKILL.md"
    notes: "Adapted."
"""
        )

        self.assertEqual(records[0].name, "demo")
        self.assertEqual(records[0].source_type, "external")
        self.assertEqual(records[0].notes, "Adapted.")

    def test_reports_missing_upstream_support_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / ".agents/skill-sources.yml"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                """skills:
  demo:
    source_type: "external"
    source_url: "https://github.com/example/project/blob/main/skills/demo/SKILL.md"
"""
            )
            skill_root = root / ".agents/skills/demo"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("same")

            report = check_skill_sources(
                source_file,
                root / ".agents/skills",
                repo_root=root,
                fetch_bytes=lambda url: b"same",
                fetch_json=_fake_github_json,
            )

        self.assertTrue(report.has_actionable_drift)
        self.assertEqual(report.checks[0].status, "matches-upstream")
        self.assertEqual(report.checks[0].missing_support_files, ("GUIDE.md",))

    def test_treats_local_sources_as_not_checked(self) -> None:
        records = parse_skill_sources(
            """skills:
  local-skill:
    source_type: "local"
    source_url: "local:repo-familiar"
"""
        )

        self.assertEqual(records[0].source_type, "local")


def _fake_github_json(url: str):
    if "/commits" in url:
        return [
            {
                "sha": "abc123",
                "commit": {"committer": {"date": "2026-06-01T00:00:00Z"}},
            }
        ]
    if "/contents/" in url:
        return [
            {"name": "SKILL.md", "type": "file"},
            {"name": "GUIDE.md", "type": "file"},
        ]
    raise AssertionError(f"Unexpected URL: {url}")


if __name__ == "__main__":
    unittest.main()
