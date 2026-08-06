from __future__ import annotations

import unittest
from pathlib import Path

from repo_familiar import profiles
from repo_familiar.generator import GenerationOptions, plan_project

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_ASSET_PATHS = (
    ".agents/models.yml",
    ".agents/tools.yml",
    ".agents/memory.yml",
    ".agents/prompts.yml",
    ".agents/safety.yml",
    ".agents/privacy.yml",
    ".agents/public-interest.yml",
    ".agents/repomap.yml",
    ".agents/sandbox.yml",
    ".agents/secrets.yml",
    ".agents/skill-sources.yml",
    ".agents/design.yml",
    ".agents/worktrees.yml",
)


class ProfileRegistryTests(unittest.TestCase):
    def test_lists_profile_names(self) -> None:
        self.assertIn("paseo", profiles.list_names(profiles.AGENT_HARNESSES))
        self.assertIn("default-coding", profiles.list_names(profiles.MODEL_PROFILES))
        self.assertIn("browser-automation", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("flint-chart", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("flint-chart-mcp", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("micropython-wasm", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("ponytail-agent-rules", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("python-guardrails", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("sandbox-micropython-wasm", profiles.list_names(profiles.SANDBOX_PROFILES))
        self.assertIn("flint-chart-author", profiles.list_names(profiles.SKILLS))
        self.assertIn("playwright-cli", profiles.list_names(profiles.SKILLS))
        self.assertIn("ponytail", profiles.list_names(profiles.SKILLS))
        self.assertIn("repository-map", profiles.list_names(profiles.SKILLS))
        self.assertIn("setup-python-guardrails", profiles.list_names(profiles.SKILLS))
        self.assertIn("session-focus", profiles.list_names(profiles.SKILLS))
        self.assertIn("semantic-routing-map", profiles.list_names(profiles.REPOMAP_PROFILES))

    def test_validates_profile_selections(self) -> None:
        profiles.validate_profile_selections(
            {
                "model_profiles": ("default-coding",),
                "tool_profiles": ("cq",),
                "memory_profiles": ("memory-local",),
                "skills": ("grill-with-docs",),
            }
        )

        with self.assertRaisesRegex(ValueError, "Unknown tool profile"):
            profiles.validate_profile_selections({"tool_profiles": ("missing",)})

    def test_renders_profile_yaml(self) -> None:
        models = profiles.render_model_profiles(("default-coding",))
        tools = profiles.render_tool_profiles(("browser-automation",))
        memory = profiles.render_advisory_profiles(profiles.MEMORY_PROFILES, ("memory-local",))

        self.assertIn("default-coding:", models)
        self.assertIn("provider:", models)
        self.assertIn("paseo", models)
        self.assertIn("browser-automation:", tools)
        self.assertIn("screenshots", tools)
        self.assertIn("setup:", tools)
        self.assertIn("verify:", tools)
        self.assertIn("npx --no-install playwright --version", tools)
        self.assertNotIn("npx playwright-cli", tools)
        self.assertIn("headroom-mcp:", profiles.render_tool_profiles(("headroom-mcp",)))
        self.assertIn("headroom proxy --port 8787", profiles.render_tool_profiles(("headroom-proxy",)))
        self.assertIn("flint-chart:", profiles.render_tool_profiles(("flint-chart",)))
        self.assertIn("ChartAssemblyInput", profiles.render_tool_profiles(("flint-chart",)))
        self.assertIn("flint-chart-mcp:", profiles.render_tool_profiles(("flint-chart-mcp",)))
        self.assertIn("--disable-file-reference", profiles.render_tool_profiles(("flint-chart-mcp",)))
        self.assertIn("micropython-wasm:", profiles.render_tool_profiles(("micropython-wasm",)))
        self.assertIn("MicroPythonSession", profiles.render_tool_profiles(("micropython-wasm",)))
        self.assertIn("ponytail-agent-rules:", profiles.render_tool_profiles(("ponytail-agent-rules",)))
        self.assertIn("PONYTAIL_DEFAULT_MODE", profiles.render_tool_profiles(("ponytail-agent-rules",)))
        self.assertIn("python-guardrails:", profiles.render_tool_profiles(("python-guardrails",)))
        self.assertIn("pre-commit run --all-files", profiles.render_tool_profiles(("python-guardrails",)))
        self.assertIn("memory-local:", memory)
        self.assertIn(
            "project-owned semantic repository routing map",
            profiles.render_advisory_profiles(
                profiles.REPOMAP_PROFILES,
                ("semantic-routing-map",),
            ),
        )
        self.assertIn("sandbox-micropython-wasm", profiles.render_advisory_profiles(profiles.SANDBOX_PROFILES, ("sandbox-micropython-wasm",)))
        self.assertIn("sops-age", profiles.render_advisory_profiles(profiles.SECRETS_PROFILES, ("sops-age",)))

    def test_generated_profile_files_match_registry_renderers(self) -> None:
        options = _all_profile_options()
        generated = {asset.path: asset.content for asset in plan_project(options)}

        expected = {
            ".agents/models.yml": "profiles:\n" + profiles.render_model_profiles(options.model_profiles) + "\n",
            ".agents/tools.yml": "profiles:\n" + profiles.render_tool_profiles(options.tool_profiles) + "\n",
            ".agents/memory.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.MEMORY_PROFILES, options.memory_profiles) + "\n",
            ".agents/prompts.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.PROMPT_PROFILES, options.prompt_profiles) + "\n",
            ".agents/safety.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.SAFETY_PROFILES, options.safety_profiles) + "\n",
            ".agents/privacy.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.PRIVACY_PROFILES, options.privacy_profiles) + "\n",
            ".agents/public-interest.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.PUBLIC_INTEREST_PROFILES, options.public_interest_profiles) + "\n",
            ".agents/repomap.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.REPOMAP_PROFILES, options.repomap_profiles) + "\n",
            ".agents/sandbox.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.SANDBOX_PROFILES, options.sandbox_profiles) + "\n",
            ".agents/secrets.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.SECRETS_PROFILES, options.secrets_profiles) + "\n\nrules:\n  - Commit `.env.example` with placeholders or secret references only.\n  - Do not commit `.env`, `.env.*`, API keys, tokens, private keys, or credential JSON files.\n  - Prefer local or managed secret stores that inject values at process start.\n  - Keep secret values out of prompts, agent memory, and bootstrap metadata.\n",
            ".agents/skill-sources.yml": "skills:\n" + profiles.render_skill_sources(options.skills) + "\n",
            ".agents/design.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.DESIGN_PROFILES, options.design_profiles) + "\n",
            ".agents/worktrees.yml": "profiles:\n" + profiles.render_advisory_profiles(profiles.WORKTREE_PROFILES, options.worktree_profiles) + "\n",
        }
        for path, expected_content in expected.items():
            self.assertEqual(generated[path], expected_content, path)

    def test_skill_source_rendering_has_stable_mapping_order(self) -> None:
        rendered = profiles.render_skill_sources(("tdd", "cq"))

        self.assertLess(rendered.index("  cq:"), rendered.index("  tdd:"))

    def test_root_agents_dogfood_assets_match_registry_templates(self) -> None:
        generated = {asset.path: asset.content for asset in plan_project(_all_profile_options())}
        expected_paths = [
            *PROFILE_ASSET_PATHS,
            *(path for path in generated if path.startswith(".agents/skills/")),
        ]

        for path in expected_paths:
            self.assertEqual((REPO_ROOT / path).read_text(), generated[path], path)

    def test_root_skill_sources_cover_every_dogfood_skill(self) -> None:
        skill_source_names = _skill_source_names((REPO_ROOT / ".agents/skill-sources.yml").read_text())
        root_skill_names = {
            path.name
            for path in (REPO_ROOT / ".agents/skills").iterdir()
            if path.is_dir()
        }

        self.assertEqual(root_skill_names - skill_source_names, set())
        self.assertEqual(root_skill_names - set(profiles.SKILLS), set())
        self.assertIn("https://github.com/mattpocock/skills", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("https://github.com/andrewyng/context-hub/blob/main/cli/skills/get-api-docs/SKILL.md", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("https://github.com/run-llama/llamaparse-agent-skills/blob/main/skills/liteparse/SKILL.md", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("lit --version", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/SKILL.md", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("chub --help", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("playwright-cli --help", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("ponytail-agent-rules", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("setup-python-guardrails", (REPO_ROOT / ".agents/skill-sources.yml").read_text())
        self.assertIn("https://github.com/microsoft/flint-chart/blob/main/agent-skills/flint-chart-author/SKILL.md", (REPO_ROOT / ".agents/skill-sources.yml").read_text())

    def test_refreshed_skill_guidance_is_vendored(self) -> None:
        cq = (REPO_ROOT / ".agents/skills/cq/SKILL.md").read_text()
        diagnose = (REPO_ROOT / ".agents/skills/diagnose/SKILL.md").read_text()
        playwright = (REPO_ROOT / ".agents/skills/playwright-cli/SKILL.md").read_text()
        architecture = (
            REPO_ROOT / ".agents/skills/improve-codebase-architecture/SKILL.md"
        ).read_text()

        self.assertIn("waiting for their approval", cq)
        self.assertIn("redacted captured artifact", diagnose)
        self.assertIn('playwright-cli find "Sign in"', playwright)
        self.assertIn("Scope before scanning", architecture)


def _all_profile_options() -> GenerationOptions:
    return GenerationOptions(
        name="Profile Regression",
        description="Verify generated profile files match registry output.",
        output_dir=Path("unused"),
        model_profiles=tuple(profiles.MODEL_PROFILES),
        tool_profiles=tuple(profiles.TOOL_PROFILES),
        memory_profiles=tuple(profiles.MEMORY_PROFILES),
        prompt_profiles=tuple(profiles.PROMPT_PROFILES),
        safety_profiles=tuple(profiles.SAFETY_PROFILES),
        privacy_profiles=tuple(profiles.PRIVACY_PROFILES),
        public_interest_profiles=tuple(profiles.PUBLIC_INTEREST_PROFILES),
        repomap_profiles=tuple(profiles.REPOMAP_PROFILES),
        sandbox_profiles=tuple(profiles.SANDBOX_PROFILES),
        secrets_profiles=tuple(profiles.SECRETS_PROFILES),
        design_profiles=tuple(profiles.DESIGN_PROFILES),
        worktree_profiles=tuple(profiles.WORKTREE_PROFILES),
        skills=tuple(profiles.SKILLS),
        dry_run=True,
    )


def _skill_source_names(content: str) -> set[str]:
    names: set[str] = set()
    for line in content.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            names.add(line.strip()[:-1])
    return names


if __name__ == "__main__":
    unittest.main()
