from __future__ import annotations

import unittest

from repo_familiar import profiles


class ProfileRegistryTests(unittest.TestCase):
    def test_lists_profile_names(self) -> None:
        self.assertIn("default-coding", profiles.list_names(profiles.MODEL_PROFILES))
        self.assertIn("browser-automation", profiles.list_names(profiles.TOOL_PROFILES))
        self.assertIn("playwright-cli", profiles.list_names(profiles.SKILLS))

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
        self.assertIn("browser-automation:", tools)
        self.assertIn("screenshots", tools)
        self.assertIn("memory-local:", memory)


if __name__ == "__main__":
    unittest.main()
