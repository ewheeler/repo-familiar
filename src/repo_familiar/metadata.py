from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

SELECTED_OPTION_KEYS = (
    "agent_harnesses",
    "model_profiles",
    "tool_profiles",
    "memory_profiles",
    "prompt_profiles",
    "safety_profiles",
    "privacy_profiles",
    "repomap_profiles",
    "sandbox_profiles",
    "secrets_profiles",
    "design_profiles",
    "worktree_profiles",
    "public_interest_profiles",
    "sops_age_recipients",
    "skills",
)
MANAGED_SURFACE_STATES = {"written", "adopted", "edited", "skipped", "conflict"}
MANAGED_SURFACE_STRATEGIES = {
    "replace_if_unchanged",
    "line_union",
    "merge_preview_only",
    "manual_review",
    "unavailable",
}


@dataclass(frozen=True)
class GeneratedAsset:
    path: str
    kind: str
    source: str
    content_sha256: str | None = None


@dataclass(frozen=True)
class RenderContext:
    project_name: str
    project_description: str
    template: str
    docs: str
    selected_options_sha256: str
    source: str = "generation_inputs"


@dataclass(frozen=True)
class ManagedSurface:
    id: str
    version: int
    template: str
    state: str
    comparison_basis: str
    strategy: str
    render_context_sha256: str
    project_name: str
    project_description: str
    docs: str
    selected_options_sha256: str
    render_context_source: str


@dataclass(frozen=True)
class ManagedSurfaceAsset:
    surface_id: str
    path: str
    state: str
    comparison_basis: str
    strategy: str
    content_sha256: str | None = None


@dataclass(frozen=True)
class MetadataOperation:
    id: str
    at: str
    command: str
    mode: str
    surface_id: str | None = None


@dataclass(frozen=True)
class BootstrapMetadata:
    schema_version: int
    bootstrap_mode: str
    reference_type: str
    reference_url: str
    reference_ref: str
    generated_at: str
    generator_name: str
    generator_version: str
    selected_template: str
    selected_options: dict[str, tuple[str, ...]]
    docs: str
    generated_assets: tuple[GeneratedAsset, ...]
    render_context: RenderContext | None = None
    managed_surfaces: tuple[ManagedSurface, ...] = ()
    managed_surface_assets: tuple[ManagedSurfaceAsset, ...] = ()
    history: tuple[MetadataOperation, ...] = ()


def load_bootstrap_metadata(path: Path) -> BootstrapMetadata:
    return parse_bootstrap_metadata(path.read_text())


def parse_bootstrap_assets(content: str) -> list[GeneratedAsset]:
    return list(parse_bootstrap_metadata(content).generated_assets)


def parse_bootstrap_metadata(content: str) -> BootstrapMetadata:
    schema_version = 1
    bootstrap_mode = "unknown"
    reference_type = "unknown"
    reference_url = "unknown"
    reference_ref = "unknown"
    generated_at = "unknown"
    generator_name = "unknown"
    generator_version = "unknown"
    selected_template = "unknown"
    selected_options: dict[str, tuple[str, ...]] = {key: () for key in SELECTED_OPTION_KEYS}
    docs = "unknown"
    assets: list[GeneratedAsset] = []
    render_context_record: dict[str, str] = {}
    surfaces: list[ManagedSurface] = []
    surface_assets: list[ManagedSurfaceAsset] = []
    history: list[MetadataOperation] = []
    current_asset: dict[str, str] | None = None
    current_surface: dict[str, str] | None = None
    current_surface_asset: dict[str, str] | None = None
    current_operation: dict[str, str] | None = None
    section: str | None = None
    current_sequence_key: str | None = None

    for line in content.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            if current_surface:
                surfaces.append(_surface_from_record(current_surface))
                current_surface = None
            if current_surface_asset:
                surface_assets.append(_surface_asset_from_record(current_surface_asset))
                current_surface_asset = None
            if current_operation:
                history.append(_operation_from_record(current_operation))
                current_operation = None
            section = line[:-1]
            current_sequence_key = None
            continue
        if line.startswith("schema_version: "):
            schema_version = int(_parse_yaml_scalar(line.split(": ", 1)[1]))
            continue
        if line.startswith("bootstrap_mode: "):
            bootstrap_mode = _parse_yaml_scalar(line.split(": ", 1)[1])
            continue
        if line.startswith("generated_at: "):
            generated_at = _parse_yaml_scalar(line.split(": ", 1)[1])
            continue

        if section == "reference_source":
            if line.startswith("  type: "):
                reference_type = _parse_yaml_scalar(line.split(": ", 1)[1])
            elif line.startswith("  url: "):
                reference_url = _parse_yaml_scalar(line.split(": ", 1)[1])
            elif line.startswith("  ref: "):
                reference_ref = _parse_yaml_scalar(line.split(": ", 1)[1])
            continue

        if section == "generator":
            if line.startswith("  name: "):
                generator_name = _parse_yaml_scalar(line.split(": ", 1)[1])
            elif line.startswith("  version: "):
                generator_version = _parse_yaml_scalar(line.split(": ", 1)[1])
            continue

        if section == "selected_options":
            if line.startswith("  template: "):
                selected_template = _parse_yaml_scalar(line.split(": ", 1)[1])
                current_sequence_key = None
            elif line.startswith("  docs: "):
                docs = _parse_yaml_scalar(line.split(": ", 1)[1])
                current_sequence_key = None
            elif line.startswith("  ") and line.endswith(": []"):
                key = line.strip().split(":", 1)[0]
                selected_options[key] = ()
                current_sequence_key = None
            elif line.startswith("  ") and line.endswith(":"):
                current_sequence_key = line.strip()[:-1]
                selected_options[current_sequence_key] = ()
            elif current_sequence_key and line.startswith("    - "):
                value = _parse_yaml_scalar(line.split("- ", 1)[1])
                selected_options[current_sequence_key] = (*selected_options[current_sequence_key], value)
            continue

        if section == "render_context":
            if line.startswith("  ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                render_context_record[key] = _parse_yaml_scalar(value)
            continue

        if section == "generated_assets":
            if line.startswith("  - path: "):
                if current_asset:
                    assets.append(_asset_from_record(current_asset))
                current_asset = {"path": _parse_yaml_scalar(line.split(": ", 1)[1])}
            elif current_asset is not None and line.startswith("    ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                current_asset[key] = _parse_yaml_scalar(value)
            continue

        if section == "managed_surfaces":
            if line.startswith("  - id: "):
                if current_surface:
                    surfaces.append(_surface_from_record(current_surface))
                current_surface = {"id": _parse_yaml_scalar(line.split(": ", 1)[1])}
            elif current_surface is not None and line.startswith("    ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                current_surface[key] = _parse_yaml_scalar(value)
            continue

        if section == "managed_surface_assets":
            if line.startswith("  - surface_id: "):
                if current_surface_asset:
                    surface_assets.append(_surface_asset_from_record(current_surface_asset))
                current_surface_asset = {
                    "surface_id": _parse_yaml_scalar(line.split(": ", 1)[1])
                }
            elif current_surface_asset is not None and line.startswith("    ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                current_surface_asset[key] = _parse_yaml_scalar(value)
            continue

        if section == "history":
            if line.startswith("  - id: "):
                if current_operation:
                    history.append(_operation_from_record(current_operation))
                current_operation = {"id": _parse_yaml_scalar(line.split(": ", 1)[1])}
            elif current_operation is not None and line.startswith("    ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                current_operation[key] = _parse_yaml_scalar(value)

    if current_asset:
        assets.append(_asset_from_record(current_asset))
    if current_surface:
        surfaces.append(_surface_from_record(current_surface))
    if current_surface_asset:
        surface_assets.append(_surface_asset_from_record(current_surface_asset))
    if current_operation:
        history.append(_operation_from_record(current_operation))

    render_context = (
        _render_context_from_record(render_context_record) if render_context_record else None
    )

    metadata = BootstrapMetadata(
        schema_version=schema_version,
        bootstrap_mode=bootstrap_mode,
        reference_type=reference_type,
        reference_url=reference_url,
        reference_ref=reference_ref,
        generated_at=generated_at,
        generator_name=generator_name,
        generator_version=generator_version,
        selected_template=selected_template,
        selected_options=selected_options,
        docs=docs,
        generated_assets=tuple(assets),
        render_context=render_context,
        managed_surfaces=tuple(surfaces),
        managed_surface_assets=tuple(surface_assets),
        history=tuple(history),
    )
    _validate_bootstrap_metadata(metadata)
    return metadata


def render_bootstrap_metadata(metadata: BootstrapMetadata) -> str:
    _validate_bootstrap_metadata(metadata)
    lines = [
        f"schema_version: {metadata.schema_version}",
        f"bootstrap_mode: {_yaml_scalar(metadata.bootstrap_mode)}",
        "reference_source:",
        f"  type: {_yaml_scalar(metadata.reference_type)}",
        f"  url: {_yaml_scalar(metadata.reference_url)}",
        f"  ref: {_yaml_scalar(metadata.reference_ref)}",
        f"generated_at: {_yaml_scalar(metadata.generated_at)}",
        "generator:",
        f"  name: {metadata.generator_name}",
        f"  version: {_yaml_scalar(metadata.generator_version)}",
        "selected_options:",
        f"  template: {_yaml_scalar(metadata.selected_template)}",
    ]
    for key in SELECTED_OPTION_KEYS:
        lines.extend(_yaml_sequence_block(f"  {key}", metadata.selected_options.get(key, ())))
    lines.extend([f"  docs: {_yaml_scalar(metadata.docs)}", "generated_assets:"])
    for asset in metadata.generated_assets:
        lines.extend(
            [
                f"  - path: {_yaml_scalar(asset.path)}",
                f"    kind: {_yaml_scalar(asset.kind)}",
                f"    source: {_yaml_scalar(asset.source)}",
            ]
        )
        if asset.content_sha256:
            lines.append(f"    content_sha256: {_yaml_scalar(asset.content_sha256)}")
    if metadata.schema_version >= 2 and metadata.render_context is not None:
        context = metadata.render_context
        lines.extend(
            [
                "render_context:",
                f"  project_name: {_yaml_scalar(context.project_name)}",
                f"  project_description: {_yaml_scalar(context.project_description)}",
                f"  template: {_yaml_scalar(context.template)}",
                f"  docs: {_yaml_scalar(context.docs)}",
                f"  selected_options_sha256: {_yaml_scalar(context.selected_options_sha256)}",
                f"  source: {_yaml_scalar(context.source)}",
                "managed_surfaces:",
            ]
        )
        for surface in metadata.managed_surfaces:
            lines.extend(
                [
                    f"  - id: {_yaml_scalar(surface.id)}",
                    f"    version: {surface.version}",
                    f"    template: {_yaml_scalar(surface.template)}",
                    f"    state: {_yaml_scalar(surface.state)}",
                    f"    comparison_basis: {_yaml_scalar(surface.comparison_basis)}",
                    f"    strategy: {_yaml_scalar(surface.strategy)}",
                    f"    render_context_sha256: {_yaml_scalar(surface.render_context_sha256)}",
                    f"    project_name: {_yaml_scalar(surface.project_name)}",
                    f"    project_description: {_yaml_scalar(surface.project_description)}",
                    f"    docs: {_yaml_scalar(surface.docs)}",
                    f"    selected_options_sha256: {_yaml_scalar(surface.selected_options_sha256)}",
                    f"    render_context_source: {_yaml_scalar(surface.render_context_source)}",
                ]
            )
        lines.append("managed_surface_assets:")
        for asset in metadata.managed_surface_assets:
            lines.extend(
                [
                    f"  - surface_id: {_yaml_scalar(asset.surface_id)}",
                    f"    path: {_yaml_scalar(asset.path)}",
                    f"    state: {_yaml_scalar(asset.state)}",
                    f"    comparison_basis: {_yaml_scalar(asset.comparison_basis)}",
                    f"    strategy: {_yaml_scalar(asset.strategy)}",
                ]
            )
            if asset.content_sha256:
                lines.append(f"    content_sha256: {_yaml_scalar(asset.content_sha256)}")
        lines.append("history:")
        for operation in metadata.history:
            lines.extend(
                [
                    f"  - id: {_yaml_scalar(operation.id)}",
                    f"    at: {_yaml_scalar(operation.at)}",
                    f"    command: {_yaml_scalar(operation.command)}",
                    f"    mode: {_yaml_scalar(operation.mode)}",
                ]
            )
            if operation.surface_id:
                lines.append(f"    surface_id: {_yaml_scalar(operation.surface_id)}")
    return "\n".join(lines) + "\n"


def _asset_from_record(record: dict[str, str]) -> GeneratedAsset:
    return GeneratedAsset(
        path=record["path"],
        kind=record.get("kind", "unknown"),
        source=record.get("source", "unknown"),
        content_sha256=record.get("content_sha256"),
    )


def _render_context_from_record(record: dict[str, str]) -> RenderContext:
    return RenderContext(
        project_name=record["project_name"],
        project_description=record["project_description"],
        template=record["template"],
        docs=record["docs"],
        selected_options_sha256=record["selected_options_sha256"],
        source=record.get("source", "generation_inputs"),
    )


def _surface_from_record(record: dict[str, str]) -> ManagedSurface:
    return ManagedSurface(
        id=record["id"],
        version=int(record.get("version", "1")),
        template=record.get("template", "unknown"),
        state=record.get("state", "unknown"),
        comparison_basis=record.get("comparison_basis", "unknown"),
        strategy=record.get("strategy", "manual_review"),
        render_context_sha256=record.get("render_context_sha256", "unknown"),
        project_name=record.get("project_name", "unknown"),
        project_description=record.get("project_description", "unknown"),
        docs=record.get("docs", "unknown"),
        selected_options_sha256=record.get("selected_options_sha256", "unknown"),
        render_context_source=record.get("render_context_source", "unknown"),
    )


def _surface_asset_from_record(record: dict[str, str]) -> ManagedSurfaceAsset:
    return ManagedSurfaceAsset(
        surface_id=record["surface_id"],
        path=record["path"],
        state=record.get("state", "unknown"),
        comparison_basis=record.get("comparison_basis", "unknown"),
        strategy=record.get("strategy", "manual_review"),
        content_sha256=record.get("content_sha256"),
    )


def _operation_from_record(record: dict[str, str]) -> MetadataOperation:
    return MetadataOperation(
        id=record["id"],
        at=record["at"],
        command=record["command"],
        mode=record["mode"],
        surface_id=record.get("surface_id"),
    )


def _validate_bootstrap_metadata(metadata: BootstrapMetadata) -> None:
    if metadata.schema_version not in (1, 2):
        raise ValueError(f"Unsupported Bootstrap Metadata schema: {metadata.schema_version}")
    if metadata.schema_version == 1:
        return
    if metadata.render_context is None:
        raise ValueError("Metadata v2 requires render_context")
    surface_ids = [surface.id for surface in metadata.managed_surfaces]
    if len(surface_ids) != len(set(surface_ids)):
        raise ValueError("Metadata v2 Managed Surface IDs must be unique")
    known_surfaces = set(surface_ids)
    asset_paths: set[str] = set()
    for surface in metadata.managed_surfaces:
        if surface.state not in MANAGED_SURFACE_STATES:
            raise ValueError(f"Invalid Managed Surface state: {surface.state}")
        if surface.strategy not in MANAGED_SURFACE_STRATEGIES:
            raise ValueError(f"Invalid Managed Surface strategy: {surface.strategy}")
        expected_context_sha = _managed_surface_context_sha256(surface)
        if surface.render_context_sha256 != expected_context_sha:
            raise ValueError(
                f"Managed Surface render context fingerprint does not match stored inputs: {surface.id}"
            )
    for asset in metadata.managed_surface_assets:
        if asset.surface_id not in known_surfaces:
            raise ValueError(
                f"Managed Surface asset references unknown surface: {asset.surface_id}"
            )
        if asset.state not in MANAGED_SURFACE_STATES:
            raise ValueError(f"Invalid Managed Surface asset state: {asset.state}")
        if asset.strategy not in MANAGED_SURFACE_STRATEGIES:
            raise ValueError(f"Invalid Managed Surface asset strategy: {asset.strategy}")
        if asset.path in asset_paths:
            raise ValueError(f"Managed Surface asset path has multiple owners: {asset.path}")
        asset_paths.add(asset.path)
    operation_ids = [operation.id for operation in metadata.history]
    if len(operation_ids) != len(set(operation_ids)):
        raise ValueError("Metadata v2 operation IDs must be unique")


def _managed_surface_context_sha256(surface: ManagedSurface) -> str:
    value = {
        "surface_id": surface.id,
        "project_name": surface.project_name,
        "project_description": surface.project_description,
        "template": surface.template,
        "docs": surface.docs,
        "selected_options_sha256": surface.selected_options_sha256,
        "source": surface.render_context_source,
    }
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode()).hexdigest()


def _yaml_sequence_block(key: str, values: tuple[str, ...]) -> list[str]:
    if not values:
        return [f"{key}: []"]
    return [f"{key}:", *[f"    - {_yaml_scalar(value)}" for value in values]]


def _yaml_scalar(value) -> str:
    return json.dumps(str(value))


def _parse_yaml_scalar(value: str) -> str:
    value = value.strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
