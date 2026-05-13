from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from repo_familiar.metadata import (
    BootstrapMetadata,
    GeneratedAsset,
    load_bootstrap_metadata,
    parse_bootstrap_assets,
    parse_bootstrap_metadata,
    render_bootstrap_metadata,
)


class MetadataTests(unittest.TestCase):
    def test_round_trips_bootstrap_metadata(self) -> None:
        metadata = BootstrapMetadata(
            schema_version=1,
            bootstrap_mode="new_repository",
            reference_type="git",
            reference_url="https://example.invalid/repo-familiar.git",
            reference_ref="test-ref",
            generated_at="2026-05-10T00:00:00Z",
            generator_name="repo-familiar",
            generator_version="0.1.0",
            selected_template="basic",
            selected_options={
                "agent_harnesses": ("opencode",),
                "model_profiles": ("default-coding", "budget-review"),
                "tool_profiles": ("cq",),
                "memory_profiles": ("memory-local",),
                "prompt_profiles": (),
                "safety_profiles": (),
                "privacy_profiles": (),
                "repomap_profiles": ("hamilton-dag",),
                "sandbox_profiles": (),
                "secrets_profiles": ("dotenv-local",),
                "design_profiles": (),
                "worktree_profiles": (),
                "skills": ("grill-with-docs",),
            },
            docs="quarto",
            generated_assets=(
                GeneratedAsset(
                    path="AGENTS.md",
                    kind="agent_instructions",
                    source="templates/basic/AGENTS.md.tmpl",
                    content_sha256="abc123",
                ),
                GeneratedAsset(
                    path=".repo-familiar/bootstrap.yml",
                    kind="metadata",
                    source="generator:bootstrap",
                ),
            ),
        )

        rendered = render_bootstrap_metadata(metadata)
        parsed = parse_bootstrap_metadata(rendered)

        self.assertEqual(parsed.schema_version, 1)
        self.assertEqual(parsed.bootstrap_mode, "new_repository")
        self.assertEqual(parsed.reference_url, "https://example.invalid/repo-familiar.git")
        self.assertEqual(parsed.selected_options["model_profiles"], ("default-coding", "budget-review"))
        self.assertEqual(parsed.selected_options["prompt_profiles"], ())
        self.assertEqual(parsed.generated_assets, metadata.generated_assets)

    def test_render_preserves_schema_v1_sections_needed_for_upgrade(self) -> None:
        metadata = BootstrapMetadata(
            schema_version=1,
            bootstrap_mode="existing_repository",
            reference_type="git",
            reference_url="https://example.invalid/repo-familiar.git",
            reference_ref="abc123",
            generated_at="2026-05-10T00:00:00Z",
            generator_name="repo-familiar",
            generator_version="0.1.0",
            selected_template="basic",
            selected_options={
                "agent_harnesses": ("opencode",),
                "skills": ("grill-with-docs",),
            },
            docs="quarto",
            generated_assets=(
                GeneratedAsset("README.md", "documentation", "templates/basic/README.md.tmpl", "abc123"),
                GeneratedAsset(".repo-familiar/bootstrap.yml", "metadata", "generator:bootstrap"),
            ),
        )

        rendered = render_bootstrap_metadata(metadata)

        self.assertIn('bootstrap_mode: "existing_repository"', rendered)
        self.assertIn('url: "https://example.invalid/repo-familiar.git"', rendered)
        self.assertIn('ref: "abc123"', rendered)
        self.assertIn("  name: repo-familiar", rendered)
        self.assertIn('  skills:', rendered)
        self.assertIn('    - "grill-with-docs"', rendered)
        self.assertIn('  prompt_profiles: []', rendered)
        self.assertIn('    content_sha256: "abc123"', rendered)
        self.assertNotIn('path: ".repo-familiar/bootstrap.yml"\n    kind: "metadata"\n    source: "generator:bootstrap"\n    content_sha256', rendered)

    def test_parse_exposes_full_metadata_for_future_upgrade_commands(self) -> None:
        content = """schema_version: 1
bootstrap_mode: "new_repository"
reference_source:
  type: "git"
  url: "https://example.invalid/repo-familiar.git"
  ref: "v1"
generated_at: "2026-05-10T00:00:00Z"
generator:
  name: repo-familiar
  version: "0.1.0"
selected_options:
  template: "basic"
  agent_harnesses:
    - "opencode"
  model_profiles:
    - "default-coding"
  tool_profiles:
    - "cq"
  memory_profiles: []
  prompt_profiles: []
  safety_profiles: []
  privacy_profiles: []
  repomap_profiles: []
  sandbox_profiles: []
  secrets_profiles: []
  design_profiles: []
  worktree_profiles: []
  skills:
    - "get-api-docs"
  docs: "quarto"
generated_assets:
  - path: "README.md"
    kind: "documentation"
    source: "templates/basic/README.md.tmpl"
    content_sha256: "abc123"
"""

        parsed = parse_bootstrap_metadata(content)

        self.assertEqual(parsed.reference_type, "git")
        self.assertEqual(parsed.reference_url, "https://example.invalid/repo-familiar.git")
        self.assertEqual(parsed.reference_ref, "v1")
        self.assertEqual(parsed.generator_name, "repo-familiar")
        self.assertEqual(parsed.selected_template, "basic")
        self.assertEqual(parsed.selected_options["tool_profiles"], ("cq",))
        self.assertEqual(parsed.selected_options["skills"], ("get-api-docs",))
        self.assertEqual(parsed.docs, "quarto")

    def test_loads_metadata_from_path(self) -> None:
        content = """schema_version: 1
bootstrap_mode: "existing_repository"
reference_source:
  type: "local"
  url: "local"
  ref: "unknown"
generated_at: "2026-05-10T00:00:00Z"
generator:
  name: "repo-familiar"
  version: "0.1.0"
selected_options:
  template: "basic"
  agent_harnesses:
    - "opencode"
  model_profiles: []
  tool_profiles: []
  memory_profiles:
    - "memory-local"
  prompt_profiles: []
  safety_profiles: []
  privacy_profiles: []
  repomap_profiles: []
  sandbox_profiles: []
  secrets_profiles: []
  design_profiles: []
  worktree_profiles: []
  skills: []
  docs: "quarto"
generated_assets:
  - path: ".agents/memory.yml"
    kind: "template_config"
    source: "templates/basic/.agents/memory.yml.tmpl"
    content_sha256: "def456"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bootstrap.yml"
            path.write_text(content)

            metadata = load_bootstrap_metadata(path)

        self.assertEqual(metadata.bootstrap_mode, "existing_repository")
        self.assertEqual(metadata.selected_options["memory_profiles"], ("memory-local",))
        self.assertEqual(parse_bootstrap_assets(content)[0].path, ".agents/memory.yml")


if __name__ == "__main__":
    unittest.main()
