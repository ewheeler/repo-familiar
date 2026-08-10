from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .asset_plan import BOOTSTRAP_METADATA_PATH
from .managed_surfaces import (
    build_managed_surfaces,
    migrate_metadata_v2,
    plan_surface_target,
    preview_managed_surface,
    repository_identity,
)
from .metadata import load_bootstrap_metadata, render_bootstrap_metadata
from .upgrade import _commit_writes, _git_worktree_is_dirty


@dataclass(frozen=True)
class SurfacePromotionAsset:
    path: str
    status: str
    action: str
    strategy: str


@dataclass(frozen=True)
class SurfacePromotionPreview:
    path: Path
    surface_id: str
    target_template: str
    assets: tuple[SurfacePromotionAsset, ...]
    extra_managed_paths: tuple[str, ...]
    blockers: tuple[str, ...]
    can_apply: bool


@dataclass(frozen=True)
class SurfacePromotionResult:
    preview: SurfacePromotionPreview
    written_paths: tuple[str, ...]


def preview_surface_promotion(
    path: Path,
    surface_id: str,
    target_template: str,
) -> SurfacePromotionPreview:
    metadata_path = path / BOOTSTRAP_METADATA_PATH
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Bootstrap metadata not found: {metadata_path}")
    target = plan_surface_target(path, surface_id, target_template)
    surface_preview = preview_managed_surface(path, surface_id, target_template)
    project_name, project_description = repository_identity(path)
    metadata = migrate_metadata_v2(
        load_bootstrap_metadata(metadata_path),
        project_name=project_name,
        project_description=project_description,
    )
    target_paths = {asset.path for asset in target.assets}
    current_surface_paths = {
        asset.path
        for asset in metadata.managed_surface_assets
        if asset.surface_id == surface_id
    }
    extra_paths = tuple(sorted(current_surface_paths - target_paths))
    assets: list[SurfacePromotionAsset] = []
    blockers: list[str] = []
    for asset in surface_preview.assets:
        if asset.status == "missing":
            action = "create"
        elif asset.status in ("written", "adopted", "adoptable"):
            action = "keep"
        elif (
            asset.status == "target-differs"
            and asset.strategy == "replace_if_unchanged"
        ):
            action = "replace"
        else:
            action = "blocked"
            blockers.append(f"{asset.path}: {asset.status} requires manual review")
        assets.append(
            SurfacePromotionAsset(
                path=asset.path,
                status=asset.status,
                action=action,
                strategy=asset.strategy,
            )
        )
    if extra_paths:
        blockers.append(
            "Managed Surface has paths outside the target template: "
            + ", ".join(extra_paths)
        )
    return SurfacePromotionPreview(
        path=path,
        surface_id=surface_id,
        target_template=target_template,
        assets=tuple(assets),
        extra_managed_paths=extra_paths,
        blockers=tuple(blockers),
        can_apply=not blockers,
    )


def promote_surface(
    path: Path,
    surface_id: str,
    target_template: str,
    *,
    apply: bool,
    allow_dirty: bool = False,
    reference_ref: str | None = None,
) -> SurfacePromotionResult:
    preview = preview_surface_promotion(path, surface_id, target_template)
    if not apply:
        return SurfacePromotionResult(preview=preview, written_paths=())
    if not preview.can_apply:
        raise ValueError("Surface promotion is blocked: " + "; ".join(preview.blockers))
    if not allow_dirty and _git_worktree_is_dirty(path):
        raise ValueError(
            "Refusing surface promotion in a dirty Git worktree; commit/stash changes "
            "or pass --allow-dirty"
        )

    metadata_path = path / BOOTSTRAP_METADATA_PATH
    project_name, project_description = repository_identity(path)
    metadata = migrate_metadata_v2(
        load_bootstrap_metadata(metadata_path),
        project_name=project_name,
        project_description=project_description,
    )
    target = plan_surface_target(path, surface_id, target_template)
    target_by_path = {asset.path: asset for asset in target.assets}
    writes = {
        asset.path: target_by_path[asset.path].content
        for asset in preview.assets
        if asset.action in ("create", "replace")
    }

    at = _operation_time()
    generated_assets = tuple(asset.as_generated_asset() for asset in target.assets)
    surfaces, surface_assets, operations = build_managed_surfaces(
        target_template,
        target.render_context,
        generated_assets,
        state="written",
        command="promote-surface",
        mode="apply",
        at=at,
    )
    current_surface_paths = {
        asset.path
        for asset in metadata.managed_surface_assets
        if asset.surface_id == surface_id
    }
    generated_by_path = {
        asset.path: asset
        for asset in metadata.generated_assets
        if asset.path not in current_surface_paths
    }
    generated_by_path.update({asset.path: asset for asset in generated_assets})
    updated = replace(
        metadata,
        schema_version=2,
        generator_version=__version__,
        reference_ref=reference_ref or metadata.reference_ref,
        generated_assets=tuple(
            generated_by_path[path_key] for path_key in sorted(generated_by_path)
        ),
        managed_surfaces=tuple(
            sorted(
                [surface for surface in metadata.managed_surfaces if surface.id != surface_id]
                + list(surfaces),
                key=lambda surface: surface.id,
            )
        ),
        managed_surface_assets=tuple(
            sorted(
                [
                    asset
                    for asset in metadata.managed_surface_assets
                    if asset.surface_id != surface_id
                ]
                + list(surface_assets),
                key=lambda asset: (asset.surface_id, asset.path),
            )
        ),
    )
    rendered_without_operation = render_bootstrap_metadata(updated)
    if not writes and rendered_without_operation == metadata_path.read_text():
        return SurfacePromotionResult(preview=preview, written_paths=())
    updated = replace(updated, history=(*metadata.history, *operations))
    writes[BOOTSTRAP_METADATA_PATH] = render_bootstrap_metadata(updated)
    _commit_writes(path, writes)
    return SurfacePromotionResult(preview=preview, written_paths=tuple(writes))


def _operation_time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")  # noqa: UP017
