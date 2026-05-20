from __future__ import annotations

from dataclasses import dataclass
import json
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


@dataclass(frozen=True)
class GeneratedAsset:
    path: str
    kind: str
    source: str
    content_sha256: str | None = None


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
    current_asset: dict[str, str] | None = None
    section: str | None = None
    current_sequence_key: str | None = None

    for line in content.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
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

        if section == "generated_assets":
            if line.startswith("  - path: "):
                if current_asset:
                    assets.append(_asset_from_record(current_asset))
                current_asset = {"path": _parse_yaml_scalar(line.split(": ", 1)[1])}
            elif current_asset is not None and line.startswith("    ") and ": " in line:
                key, value = line.strip().split(": ", 1)
                current_asset[key] = _parse_yaml_scalar(value)

    if current_asset:
        assets.append(_asset_from_record(current_asset))

    return BootstrapMetadata(
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
    )


def render_bootstrap_metadata(metadata: BootstrapMetadata) -> str:
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
    return "\n".join(lines) + "\n"


def _asset_from_record(record: dict[str, str]) -> GeneratedAsset:
    return GeneratedAsset(
        path=record["path"],
        kind=record.get("kind", "unknown"),
        source=record.get("source", "unknown"),
        content_sha256=record.get("content_sha256"),
    )


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
