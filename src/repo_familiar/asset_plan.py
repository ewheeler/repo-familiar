from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from string import Template

from .metadata import GeneratedAsset


BOOTSTRAP_METADATA_PATH = ".repo-familiar/bootstrap.yml"

ASSET_KINDS = {
    ".gitignore": "template_config",
    ".env.example": "template_config",
    "AGENTS.md": "agent_instructions",
    "README.md": "documentation",
    ".agents/design.yml": "template_config",
    ".agents/memory.yml": "template_config",
    ".agents/models.yml": "template_config",
    ".agents/privacy.yml": "template_config",
    ".agents/public-interest.yml": "template_config",
    ".agents/prompts.yml": "template_config",
    ".agents/repomap.yml": "template_config",
    ".agents/sandbox.yml": "template_config",
    ".agents/secrets.yml": "template_config",
    ".agents/safety.yml": "template_config",
    ".agents/skill-sources.yml": "template_config",
    ".agents/tools.yml": "template_config",
    ".agents/worktrees.yml": "template_config",
    "docs/_quarto.yml": "documentation",
    "docs/index.qmd": "documentation",
    "docs/usage.qmd": "documentation",
    "docs/architecture.qmd": "documentation",
    "plan.md": "project_plan",
    BOOTSTRAP_METADATA_PATH: "metadata",
}


@dataclass(frozen=True)
class PlannedAsset:
    path: str
    kind: str
    source: str
    content: str

    def as_generated_asset(self) -> GeneratedAsset:
        checksum = None if self.kind == "metadata" else _content_sha256(self.content)
        return GeneratedAsset(
            path=self.path,
            kind=self.kind,
            source=self.source,
            content_sha256=checksum,
        )


def plan_template_assets(template_root: Path, template_name: str, context: dict[str, str]) -> list[PlannedAsset]:
    planned_assets: list[PlannedAsset] = []
    for source_path in sorted(template_root.rglob("*.tmpl")):
        relative_template = source_path.relative_to(template_root)
        relative_output = relative_template.with_suffix("")
        path = relative_output.as_posix()
        planned_assets.append(
            PlannedAsset(
                path=path,
                kind=asset_kind(path),
                source=f"templates/{template_name}/{relative_template.as_posix()}",
                content=Template(source_path.read_text()).safe_substitute(context),
            )
        )
    return planned_assets


def plan_skill_assets(skills_root: Path, skills: tuple[str, ...], context: dict[str, str]) -> list[PlannedAsset]:
    planned_assets: list[PlannedAsset] = []
    for skill in skills:
        skill_root = skills_root / skill
        if not skill_root.exists():
            raise ValueError(f"Unknown skill template: {skill}")
        for source_path in sorted(skill_root.rglob("*.tmpl")):
            relative_template = source_path.relative_to(skill_root)
            relative_output = relative_template.with_suffix("")
            path = (Path(".agents/skills") / skill / relative_output).as_posix()
            planned_assets.append(
                PlannedAsset(
                    path=path,
                    kind=asset_kind(path),
                    source=f"templates/skills/{skill}/{relative_template.as_posix()}",
                    content=Template(source_path.read_text()).safe_substitute(context),
                )
            )
    return planned_assets


def filter_planned_assets(
    planned_assets: list[PlannedAsset],
    asset_groups: tuple[str, ...],
) -> list[PlannedAsset]:
    if "all" in asset_groups:
        return planned_assets
    return [asset for asset in planned_assets if asset_in_groups(asset.path, asset_groups)]


def asset_in_groups(path: str, asset_groups: tuple[str, ...]) -> bool:
    if "metadata" in asset_groups and path == BOOTSTRAP_METADATA_PATH:
        return True
    if "skills" in asset_groups and (path.startswith(".agents/skills/") or path == ".agents/skill-sources.yml"):
        return True
    if "tools" in asset_groups and path == ".agents/tools.yml":
        return True
    if "memory" in asset_groups and path == ".agents/memory.yml":
        return True
    if "prompts" in asset_groups and path == ".agents/prompts.yml":
        return True
    if "safety" in asset_groups and path == ".agents/safety.yml":
        return True
    if "privacy" in asset_groups and path == ".agents/privacy.yml":
        return True
    if "public-interest" in asset_groups and path == ".agents/public-interest.yml":
        return True
    if "repomap" in asset_groups and path == ".agents/repomap.yml":
        return True
    if "sandbox" in asset_groups and path == ".agents/sandbox.yml":
        return True
    if "secrets" in asset_groups and path in (".agents/secrets.yml", ".env.example"):
        return True
    if "design" in asset_groups and path == ".agents/design.yml":
        return True
    if "worktrees" in asset_groups and path == ".agents/worktrees.yml":
        return True
    if "models" in asset_groups and path == ".agents/models.yml":
        return True
    if "agent" in asset_groups and path == "AGENTS.md":
        return True
    if "docs" in asset_groups and (path.startswith("docs/") or path == "README.md"):
        return True
    if "plan" in asset_groups and path == "plan.md":
        return True
    if "config" in asset_groups and path == ".gitignore":
        return True
    return False


def asset_kind(path: str) -> str:
    if path.startswith(".agents/skills/"):
        return "skill"
    try:
        return ASSET_KINDS[path]
    except KeyError as error:
        raise ValueError(f"Template has no generated asset kind: {path}") from error


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
