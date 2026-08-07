from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from . import __version__
from .asset_plan import PlannedAsset, plan_skill_assets


PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PLUGIN_NAME = "repo-familiar-repository-map"
PLUGIN_SKILL = "repository-map"


@dataclass(frozen=True)
class AgentPluginExportOptions:
    output_dir: Path


def export_agent_plugin(options: AgentPluginExportOptions) -> list[PlannedAsset]:
    _validate_output_dir(options.output_dir)
    assets = plan_agent_plugin()
    for asset in assets:
        target = options.output_dir / asset.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(asset.content)
    return assets


def plan_agent_plugin() -> list[PlannedAsset]:
    manifest = {
        "$schema": PLUGIN_SCHEMA,
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Selective semantic repository routing maps for coding agents.",
        "license": "Apache-2.0",
    }
    skills_root = Path(__file__).with_name("templates") / "skills"
    return [
        PlannedAsset(
            path="plugin.json",
            kind="template_config",
            source="generator:agent-plugin-manifest",
            content=json.dumps(manifest, indent=2) + "\n",
        ),
        *plan_skill_assets(
            skills_root,
            (PLUGIN_SKILL,),
            {},
            destination_root=Path("skills"),
        ),
    ]


def _validate_output_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    if not output_dir.is_dir():
        raise NotADirectoryError(f"Output path exists and is not a directory: {output_dir}")
    if any(output_dir.iterdir()):
        raise FileExistsError(
            f"Refusing to export into non-empty directory: {output_dir}"
        )
