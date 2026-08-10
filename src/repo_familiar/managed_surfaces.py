from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .asset_plan import BOOTSTRAP_METADATA_PATH
from .metadata import (
    BootstrapMetadata,
    GeneratedAsset,
    ManagedSurface,
    ManagedSurfaceAsset,
    MetadataOperation,
    RenderContext,
    load_bootstrap_metadata,
    render_bootstrap_metadata,
)

SURFACE_STRATEGIES = {
    "repository-foundation": "manual_review",
    "agent-runtime": "replace_if_unchanged",
    "divio-documentation": "manual_review",
    "python-runtime": "manual_review",
    "quality-and-ci": "manual_review",
    "reproducible-analysis": "manual_review",
    "quarto-static-client": "manual_review",
    "fastapi-api": "manual_review",
}


@dataclass(frozen=True)
class SurfaceAssetPreview:
    path: str
    status: str
    strategy: str
    current_sha256: str | None
    target_sha256: str


@dataclass(frozen=True)
class SurfacePreview:
    path: Path
    surface_id: str
    template: str
    assets: tuple[SurfaceAssetPreview, ...]
    can_attach_exact: bool
    can_attach_current: bool


@dataclass(frozen=True)
class SurfaceAttachResult:
    preview: SurfacePreview
    metadata_written: bool


@dataclass(frozen=True)
class TemplateMigrationPreview:
    path: Path
    current_template: str
    target_template: str
    surfaces: tuple[SurfacePreview, ...]


@dataclass(frozen=True)
class MetadataMigrationResult:
    path: Path
    previous_schema_version: int
    metadata: BootstrapMetadata
    metadata_written: bool


def build_render_context(
    project_name: str,
    project_description: str,
    template: str,
    docs: str,
    selected_options: dict[str, tuple[str, ...]],
    *,
    source: str = "generation_inputs",
) -> RenderContext:
    fingerprint = _sha256_json(
        {key: list(values) for key, values in sorted(selected_options.items())}
    )
    return RenderContext(
        project_name=project_name,
        project_description=project_description,
        template=template,
        docs=docs,
        selected_options_sha256=fingerprint,
        source=source,
    )


def build_managed_surfaces(
    template: str,
    render_context: RenderContext,
    assets: tuple[GeneratedAsset, ...],
    *,
    state: str,
    command: str,
    mode: str,
    at: str,
) -> tuple[
    tuple[ManagedSurface, ...],
    tuple[ManagedSurfaceAsset, ...],
    tuple[MetadataOperation, ...],
]:
    grouped: dict[str, list[GeneratedAsset]] = {}
    for asset in assets:
        if asset.kind == "metadata":
            continue
        grouped.setdefault(surface_id_for_path(asset.path), []).append(asset)

    surfaces: list[ManagedSurface] = []
    surface_assets: list[ManagedSurfaceAsset] = []
    operations: list[MetadataOperation] = []
    for surface_id in sorted(grouped):
        strategy = SURFACE_STRATEGIES[surface_id]
        context_sha = _surface_context_sha256(render_context, surface_id)
        surfaces.append(
            ManagedSurface(
                id=surface_id,
                version=1,
                template=template,
                state=state,
                comparison_basis="content_sha256",
                strategy=strategy,
                render_context_sha256=context_sha,
                project_name=render_context.project_name,
                project_description=render_context.project_description,
                docs=render_context.docs,
                selected_options_sha256=render_context.selected_options_sha256,
                render_context_source=render_context.source,
            )
        )
        for asset in sorted(grouped[surface_id], key=lambda item: item.path):
            surface_assets.append(
                ManagedSurfaceAsset(
                    surface_id=surface_id,
                    path=asset.path,
                    state=state,
                    comparison_basis=(
                        "content_sha256" if asset.content_sha256 else "presence_only"
                    ),
                    strategy=strategy,
                    content_sha256=asset.content_sha256,
                )
            )
        operations.append(
            MetadataOperation(
                id=_operation_id(command, mode, surface_id, at),
                at=at,
                command=command,
                mode=mode,
                surface_id=surface_id,
            )
        )
    return tuple(surfaces), tuple(surface_assets), tuple(operations)


def migrate_metadata_v2(
    metadata: BootstrapMetadata,
    *,
    project_name: str,
    project_description: str,
    at: str | None = None,
) -> BootstrapMetadata:
    if metadata.schema_version >= 2:
        return metadata
    context = build_render_context(
        project_name,
        project_description,
        metadata.selected_template,
        metadata.docs,
        metadata.selected_options,
        source="inferred_from_repository",
    )
    migration_at = at or metadata.generated_at
    surfaces, assets, _ = build_managed_surfaces(
        metadata.selected_template,
        context,
        metadata.generated_assets,
        state="written",
        command="migrate-metadata",
        mode="apply",
        at=migration_at,
    )
    operation = MetadataOperation(
        id=_operation_id("migrate-metadata", "apply", "all", migration_at),
        at=migration_at,
        command="migrate-metadata",
        mode="apply",
    )
    return replace(
        metadata,
        schema_version=2,
        render_context=context,
        managed_surfaces=surfaces,
        managed_surface_assets=assets,
        history=(operation,),
    )


def migrate_metadata_file(path: Path, *, apply: bool) -> MetadataMigrationResult:
    metadata_path = path / BOOTSTRAP_METADATA_PATH
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Bootstrap metadata not found: {metadata_path}")
    existing = load_bootstrap_metadata(metadata_path)
    name, description = repository_identity(path)
    migrated = migrate_metadata_v2(
        existing,
        project_name=name,
        project_description=description,
        at=_utc_now(),
    )
    should_write = apply and existing.schema_version < 2
    if should_write:
        _write_metadata(metadata_path, migrated)
    return MetadataMigrationResult(
        path=path,
        previous_schema_version=existing.schema_version,
        metadata=migrated,
        metadata_written=should_write,
    )


def preview_managed_surface(
    path: Path,
    surface_id: str,
    template: str,
    *,
    asset_paths: tuple[str, ...] = (),
) -> SurfacePreview:
    planned_assets, _ = _planned_target(path, template)
    template_surface_ids = {
        surface_id_for_path(asset.path)
        for asset in planned_assets
        if asset.kind != "metadata"
    }
    if surface_id not in template_surface_ids:
        raise ValueError(f"Template {template} does not define Managed Surface {surface_id}")
    metadata_path = path / BOOTSTRAP_METADATA_PATH
    if metadata_path.is_file():
        name, description = repository_identity(path)
        metadata = migrate_metadata_v2(
            load_bootstrap_metadata(metadata_path),
            project_name=name,
            project_description=description,
        )
    else:
        metadata = None
    managed = {
        asset.path: asset
        for asset in (metadata.managed_surface_assets if metadata is not None else ())
        if asset.surface_id == surface_id
    }
    previews: list[SurfaceAssetPreview] = []
    if asset_paths:
        normalized_paths = _validate_explicit_asset_paths(asset_paths)
        for asset_path in normalized_paths:
            current_path = path / asset_path
            current_sha = _sha256_file(current_path) if current_path.is_file() else None
            owned = managed.get(asset_path)
            if current_sha is None:
                status = "missing"
            elif owned is not None:
                status = (
                    owned.state
                    if owned.content_sha256 is None or current_sha == owned.content_sha256
                    else "edited"
                )
            else:
                status = "current"
            previews.append(
                SurfaceAssetPreview(
                    path=asset_path,
                    status=status,
                    strategy="manual_review",
                    current_sha256=current_sha,
                    target_sha256=current_sha or "missing",
                )
            )
    else:
        targets = tuple(
            asset
            for asset in planned_assets
            if asset.kind != "metadata" and surface_id_for_path(asset.path) == surface_id
        )
        previews.extend(_preview_template_assets(path, surface_id, targets, managed))
    statuses = {preview.status for preview in previews}
    return SurfacePreview(
        path=path,
        surface_id=surface_id,
        template=template,
        assets=tuple(previews),
        can_attach_exact=statuses <= {"adoptable", "adopted", "written"},
        can_attach_current="missing" not in statuses,
    )


def attach_managed_surface(
    path: Path,
    surface_id: str,
    template: str,
    *,
    apply: bool,
    accept_current: bool = False,
    asset_paths: tuple[str, ...] = (),
) -> SurfaceAttachResult:
    preview = preview_managed_surface(
        path, surface_id, template, asset_paths=asset_paths
    )
    if not apply:
        return SurfaceAttachResult(preview=preview, metadata_written=False)
    if not preview.can_attach_current:
        raise ValueError("Managed Surface attach is blocked because required files are missing")
    if not preview.can_attach_exact and not accept_current:
        raise ValueError(
            "Managed Surface contains edited or conflicting files; rerun with --accept-current "
            "to adopt their current checksums without rewriting them"
        )

    _, target_options = _planned_target(path, template)
    name, description = repository_identity(path)
    metadata_path = path / BOOTSTRAP_METADATA_PATH
    if metadata_path.is_file():
        metadata = migrate_metadata_v2(
            load_bootstrap_metadata(metadata_path),
            project_name=name,
            project_description=description,
            at=_utc_now(),
        )
    else:
        metadata = _new_existing_metadata(name, description)

    at = _utc_now()
    context = build_render_context(
        name,
        description,
        template,
        target_options.docs,
        _selected_options(target_options),
        source="attach_preview",
    )
    surface = ManagedSurface(
        id=surface_id,
        version=1,
        template=template,
        state="adopted",
        comparison_basis="content_sha256",
        strategy="manual_review",
        render_context_sha256=_surface_context_sha256(context, surface_id),
        project_name=context.project_name,
        project_description=context.project_description,
        docs=context.docs,
        selected_options_sha256=context.selected_options_sha256,
        render_context_source=context.source,
    )
    newly_adopted_assets = tuple(
        ManagedSurfaceAsset(
            surface_id=surface_id,
            path=preview_asset.path,
            state="adopted",
            comparison_basis="content_sha256",
            strategy="manual_review",
            content_sha256=_sha256_file(path / preview_asset.path),
        )
        for preview_asset in preview.assets
    )
    adopted_by_path = {
        asset.path: asset
        for asset in metadata.managed_surface_assets
        if asset.surface_id == surface_id
    }
    adopted_by_path.update({asset.path: asset for asset in newly_adopted_assets})
    updated = replace(
        metadata,
        schema_version=2,
        managed_surfaces=tuple(
            sorted(
                [item for item in metadata.managed_surfaces if item.id != surface_id]
                + [surface],
                key=lambda item: item.id,
            )
        ),
        managed_surface_assets=tuple(
            sorted(
                [
                    item
                    for item in metadata.managed_surface_assets
                    if item.surface_id != surface_id
                ]
                + list(adopted_by_path.values()),
                key=lambda item: (item.surface_id, item.path),
            )
        ),
    )
    if metadata_path.is_file() and render_bootstrap_metadata(updated) == metadata_path.read_text():
        return SurfaceAttachResult(preview=preview, metadata_written=False)
    operation = MetadataOperation(
        id=_operation_id("attach", "apply", surface_id, at),
        at=at,
        command="attach",
        mode="apply",
        surface_id=surface_id,
    )
    updated = replace(updated, history=(*metadata.history, operation))
    _write_metadata(metadata_path, updated)
    return SurfaceAttachResult(preview=preview, metadata_written=True)


def preview_template_migration(path: Path, target_template: str) -> TemplateMigrationPreview:
    planned_assets, _ = _planned_target(path, target_template)
    surface_ids = sorted(
        {
            surface_id_for_path(asset.path)
            for asset in planned_assets
            if asset.kind != "metadata"
        }
    )
    metadata_path = path / BOOTSTRAP_METADATA_PATH
    current_template = (
        load_bootstrap_metadata(metadata_path).selected_template
        if metadata_path.is_file()
        else "basic"
    )
    return TemplateMigrationPreview(
        path=path,
        current_template=current_template,
        target_template=target_template,
        surfaces=tuple(
            preview_managed_surface(path, surface_id, target_template)
            for surface_id in surface_ids
        ),
    )


def surface_id_for_path(path: str) -> str:
    if path.startswith(".agents/") or path == "opencode.json":
        return "agent-runtime"
    if path.startswith("docs/"):
        return "divio-documentation"
    if path in ("pyproject.toml", "uv.lock", ".python-version"):
        return "python-runtime"
    if path == ".pre-commit-config.yaml" or path.startswith(".github/workflows/"):
        return "quality-and-ci"
    if path.startswith("app/") or path in (
        "STATIC_QUARTO_APPLICATION.md",
        "tests/test_browser.py",
    ):
        return "quarto-static-client"
    if path.endswith("/api.py") or path == "tests/test_api.py":
        return "fastapi-api"
    if path.startswith(("src/", "tests/", "data/", "config/")) or path == "REPRODUCIBILITY.md":
        return "reproducible-analysis"
    return "repository-foundation"


def _planned_target(path: Path, template: str):
    from .generator import GenerationOptions, plan_project, resolve_generation_options

    name, description = repository_identity(path)
    options = resolve_generation_options(
        GenerationOptions(
            name=name,
            description=description,
            output_dir=path,
            template=template,
            dry_run=True,
        )
    )
    return plan_project(options), options


def _preview_template_assets(path: Path, surface_id: str, targets, managed):
    previews: list[SurfaceAssetPreview] = []
    for target in targets:
        current_path = path / target.path
        target_sha = _sha256_text(target.content)
        current_sha = _sha256_file(current_path) if current_path.is_file() else None
        owned = managed.get(target.path)
        if current_sha is None:
            status = "missing"
        elif owned is not None:
            if owned.content_sha256 is not None and current_sha != owned.content_sha256:
                status = "edited"
            elif current_sha == target_sha:
                status = owned.state
            else:
                status = "target-differs"
        elif current_sha == target_sha:
            status = "adoptable"
        else:
            status = "conflict"
        previews.append(
            SurfaceAssetPreview(
                path=target.path,
                status=status,
                strategy=SURFACE_STRATEGIES[surface_id],
                current_sha256=current_sha,
                target_sha256=target_sha,
            )
        )
    return previews


def _validate_explicit_asset_paths(asset_paths: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in asset_paths:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() == BOOTSTRAP_METADATA_PATH:
            raise ValueError(f"Unsafe Managed Surface asset path: {value}")
        normalized.append(path.as_posix())
    if len(normalized) != len(set(normalized)):
        raise ValueError("Managed Surface asset paths must be unique")
    return tuple(sorted(normalized))


def _new_existing_metadata(name: str, description: str):
    selected_options = {
        "agent_harnesses": (),
        "model_profiles": (),
        "tool_profiles": (),
        "memory_profiles": (),
        "prompt_profiles": (),
        "safety_profiles": (),
        "privacy_profiles": (),
        "repomap_profiles": (),
        "sandbox_profiles": (),
        "secrets_profiles": (),
        "design_profiles": (),
        "worktree_profiles": (),
        "public_interest_profiles": (),
        "sops_age_recipients": (),
        "skills": (),
    }
    context = build_render_context(
        name,
        description,
        "basic",
        "quarto",
        selected_options,
        source="inferred_from_repository",
    )
    return BootstrapMetadata(
        schema_version=2,
        bootstrap_mode="existing_repository",
        reference_type="local",
        reference_url="local",
        reference_ref=__version__,
        generated_at=_utc_now(),
        generator_name="repo-familiar",
        generator_version=__version__,
        selected_template="basic",
        selected_options=selected_options,
        docs="quarto",
        generated_assets=(
            GeneratedAsset(BOOTSTRAP_METADATA_PATH, "metadata", "managed-surfaces:attach"),
        ),
        render_context=context,
    )


def _selected_options(options) -> dict[str, tuple[str, ...]]:
    return {
        "agent_harnesses": options.agent_harnesses,
        "model_profiles": options.model_profiles,
        "tool_profiles": options.tool_profiles,
        "memory_profiles": options.memory_profiles,
        "prompt_profiles": options.prompt_profiles,
        "safety_profiles": options.safety_profiles,
        "privacy_profiles": options.privacy_profiles,
        "repomap_profiles": options.repomap_profiles,
        "sandbox_profiles": options.sandbox_profiles,
        "secrets_profiles": options.secrets_profiles,
        "design_profiles": options.design_profiles,
        "worktree_profiles": options.worktree_profiles,
        "public_interest_profiles": options.public_interest_profiles,
        "sops_age_recipients": options.sops_age_recipients,
        "skills": options.skills,
    }


def repository_identity(path: Path) -> tuple[str, str]:
    readme = path / "README.md"
    if readme.is_file():
        lines = readme.read_text().splitlines()
        name = lines[0][2:].strip() if lines and lines[0].startswith("# ") else path.name
        description = next(
            (line.strip() for line in lines[1:] if line.strip() and not line.startswith("#")),
            "Managed by repo-familiar.",
        )
        return name, description
    return path.name, "Managed by repo-familiar."


def _write_metadata(path: Path, metadata: BootstrapMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".yml.tmp")
    temporary.write_text(render_bootstrap_metadata(metadata))
    temporary.replace(path)


def _surface_context_sha256(context: RenderContext, surface_id: str) -> str:
    return _sha256_json(
        {
            "surface_id": surface_id,
            "project_name": context.project_name,
            "project_description": context.project_description,
            "template": context.template,
            "docs": context.docs,
            "selected_options_sha256": context.selected_options_sha256,
            "source": context.source,
        }
    )


def _operation_id(command: str, mode: str, surface_id: str, at: str) -> str:
    return "op-" + _sha256_text(f"{command}:{mode}:{surface_id}:{at}")[:16]


def new_metadata_operation(
    command: str,
    mode: str,
    surface_id: str | None = None,
    *,
    at: str | None = None,
) -> MetadataOperation:
    operation_at = at or _utc_now()
    identity = surface_id or "all"
    return MetadataOperation(
        id=_operation_id(command, mode, identity, operation_at),
        at=operation_at,
        command=command,
        mode=mode,
        surface_id=surface_id,
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _sha256_json(value) -> str:
    return _sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")  # noqa: UP017
