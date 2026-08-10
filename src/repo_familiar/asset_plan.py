from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from string import Template

from .metadata import GeneratedAsset


BOOTSTRAP_METADATA_PATH = ".repo-familiar/bootstrap.yml"


@dataclass(frozen=True)
class TemplateLayer:
    name: str
    overrides: frozenset[str] = frozenset()


TEMPLATE_COMPOSITIONS = {
    "basic": (TemplateLayer("basic"),),
    "python-reproducible": (
        TemplateLayer("basic"),
        TemplateLayer(
            "python-reproducible",
            frozenset(
                {
                    "AGENTS.md",
                    "README.md",
                    ".gitignore",
                    "docs/architecture.qmd",
                    "docs/explanation.qmd",
                    "docs/reference.qmd",
                    "docs/tutorials.qmd",
                }
            ),
        ),
    ),
    "static-quarto-application": (
        TemplateLayer("basic"),
        TemplateLayer(
            "python-reproducible",
            frozenset(
                {
                    "AGENTS.md",
                    "README.md",
                    ".gitignore",
                    "docs/architecture.qmd",
                    "docs/explanation.qmd",
                    "docs/reference.qmd",
                    "docs/tutorials.qmd",
                }
            ),
        ),
        TemplateLayer(
            "static-quarto-application",
            frozenset(
                {
                    "AGENTS.md",
                    "README.md",
                    "pyproject.toml",
                    "uv.lock",
                    "docs/architecture.qmd",
                    "docs/reference.qmd",
                    "docs/tutorials.qmd",
                }
            ),
        ),
    ),
}

ASSET_KINDS = {
    ".gitignore": "template_config",
    ".env.example": "template_config",
    "opencode.json": "template_config",
    "AGENTS.md": "agent_instructions",
    "README.md": "documentation",
    "REPRODUCIBILITY.md": "documentation",
    "STATIC_QUARTO_APPLICATION.md": "documentation",
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
    "docs/tutorials.qmd": "documentation",
    "docs/how-to.qmd": "documentation",
    "docs/reference.qmd": "documentation",
    "docs/explanation.qmd": "documentation",
    "docs/usage.qmd": "documentation",
    "docs/architecture.qmd": "documentation",
    "docs/secrets.qmd": "documentation",
    "plan.md": "project_plan",
    ".sops.yaml": "template_config",
    "secrets/.gitignore": "template_config",
    "secrets/README.md": "documentation",
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
        path = _render_output_path(relative_output, context)
        planned_assets.append(
            PlannedAsset(
                path=path,
                kind=asset_kind(path),
                source=f"templates/{template_name}/{relative_template.as_posix()}",
                content=Template(source_path.read_text()).safe_substitute(context),
            )
        )
    return planned_assets


def plan_composed_template_assets(
    templates_root: Path,
    template_name: str,
    context: dict[str, str],
    compositions: dict[str, tuple[TemplateLayer, ...]] | None = None,
) -> list[PlannedAsset]:
    registry = compositions or TEMPLATE_COMPOSITIONS
    try:
        layers = registry[template_name]
    except KeyError as error:
        known = ", ".join(sorted(registry))
        raise ValueError(f"Unknown template: {template_name}. Known templates: {known}") from error

    planned_by_path: dict[str, PlannedAsset] = {}
    for layer in layers:
        layer_root = templates_root / layer.name
        if not layer_root.is_dir():
            raise ValueError(f"Template layer is missing: {layer.name}")
        used_overrides: set[str] = set()
        for asset in plan_template_assets(layer_root, layer.name, context):
            previous = planned_by_path.get(asset.path)
            if previous is None:
                planned_by_path[asset.path] = asset
                continue
            if asset.path not in layer.overrides:
                raise ValueError(
                    f"Template {template_name} layer {layer.name} collides at {asset.path} "
                    f"without a declared override (previous: {previous.source}, incoming: {asset.source})"
                )
            used_overrides.add(asset.path)
            planned_by_path[asset.path] = asset
        unused = layer.overrides - used_overrides
        if unused:
            raise ValueError(
                f"Template {template_name} layer {layer.name} declares unused overrides: "
                f"{', '.join(sorted(unused))}"
            )
    return [planned_by_path[path] for path in sorted(planned_by_path)]


def validate_unique_assets(planned_assets: list[PlannedAsset]) -> None:
    sources_by_path: dict[str, str] = {}
    for asset in planned_assets:
        previous_source = sources_by_path.get(asset.path)
        if previous_source is not None:
            raise ValueError(
                f"Duplicate generated asset path: {asset.path} "
                f"(previous: {previous_source}, incoming: {asset.source})"
            )
        sources_by_path[asset.path] = asset.source


def plan_skill_assets(
    skills_root: Path,
    skills: tuple[str, ...],
    context: dict[str, str],
    destination_root: Path = Path(".agents/skills"),
) -> list[PlannedAsset]:
    planned_assets: list[PlannedAsset] = []
    for skill in skills:
        skill_root = skills_root / skill
        if not skill_root.exists():
            raise ValueError(f"Unknown skill template: {skill}")
        for source_path in sorted(skill_root.rglob("*.tmpl")):
            relative_template = source_path.relative_to(skill_root)
            relative_output = relative_template.with_suffix("")
            path = (destination_root / skill / relative_output).as_posix()
            planned_assets.append(
                PlannedAsset(
                    path=path,
                    kind="skill",
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
    if "secrets" in asset_groups and path in (".sops.yaml", "secrets/.gitignore", "secrets/README.md", "docs/secrets.qmd"):
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
    if "config" in asset_groups and path in (".gitignore", "opencode.json"):
        return True
    if "python" in asset_groups and (
        path in (
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".pre-commit-config.yaml",
            "REPRODUCIBILITY.md",
        )
        or path.startswith(("src/", "tests/", "config/", "data/", ".github/workflows/"))
    ):
        return True
    if "application" in asset_groups and (
        path in ("STATIC_QUARTO_APPLICATION.md", "pyproject.toml", "uv.lock")
        or path.startswith("app/")
        or path.endswith("/api.py")
        or path in ("tests/test_api.py", "tests/test_browser.py")
    ):
        return True
    return False


def asset_kind(path: str) -> str:
    if path.startswith(".agents/skills/"):
        return "skill"
    if path == "pyproject.toml":
        return "dependency_manifest"
    if path == "uv.lock":
        return "dependency_lock"
    if path.startswith("src/"):
        return "source_code"
    if path.startswith("tests/"):
        return "test_code"
    if path.startswith("data/"):
        return "data_fixture"
    if path.startswith("app/"):
        return "source_code"
    if path in (".python-version", ".pre-commit-config.yaml") or path.startswith(".github/workflows/") or path.startswith("config/"):
        return "template_config"
    try:
        return ASSET_KINDS[path]
    except KeyError as error:
        raise ValueError(f"Template has no generated asset kind: {path}") from error


def _render_output_path(relative_output: Path, context: dict[str, str]) -> str:
    rendered = Template(relative_output.as_posix()).safe_substitute(context)
    path = Path(rendered)
    if path.is_absolute() or ".." in path.parts or "$" in rendered:
        raise ValueError(f"Unsafe or unresolved generated asset path: {rendered}")
    return path.as_posix()


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
