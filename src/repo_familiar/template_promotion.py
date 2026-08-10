from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .asset_plan import BOOTSTRAP_METADATA_PATH
from .managed_surfaces import (
    build_managed_surfaces,
    migrate_metadata_v2,
    new_metadata_operation,
    plan_template_target,
    repository_identity,
    surface_id_for_path,
)
from .metadata import load_bootstrap_metadata, render_bootstrap_metadata
from .surface_promotion import SurfacePromotionPreview, preview_surface_promotion
from .upgrade import _commit_writes, _git_worktree_is_dirty

SURFACE_PROMOTION_ORDER = (
    "repository-foundation",
    "agent-runtime",
    "python-runtime",
    "quality-and-ci",
    "reproducible-analysis",
    "fastapi-api",
    "quarto-static-client",
    "divio-documentation",
)


@dataclass(frozen=True)
class TemplatePromotionPreview:
    path: Path
    current_template: str
    target_template: str
    surfaces: tuple[SurfacePromotionPreview, ...]
    removed_surface_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    can_apply: bool


@dataclass(frozen=True)
class TemplatePromotionResult:
    preview: TemplatePromotionPreview
    written_paths: tuple[str, ...]
    selected_template_changed: bool


def preview_template_promotion(
    path: Path,
    target_template: str,
) -> TemplatePromotionPreview:
    metadata_path = path / BOOTSTRAP_METADATA_PATH
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Bootstrap metadata not found: {metadata_path}")
    project_name, project_description = repository_identity(path)
    metadata = migrate_metadata_v2(
        load_bootstrap_metadata(metadata_path),
        project_name=project_name,
        project_description=project_description,
    )
    target = _plan_target_for_promotion(path, metadata, target_template)
    target_surface_ids = {
        surface_id_for_path(asset.path)
        for asset in target.assets
        if asset.kind != "metadata"
    }
    unknown_surface_ids = target_surface_ids - set(SURFACE_PROMOTION_ORDER)
    if unknown_surface_ids:
        raise ValueError(
            "Target template defines unordered Managed Surfaces: "
            + ", ".join(sorted(unknown_surface_ids))
        )
    ordered_surface_ids = tuple(
        surface_id for surface_id in SURFACE_PROMOTION_ORDER if surface_id in target_surface_ids
    )
    surfaces = tuple(
        preview_surface_promotion(path, surface_id, target_template)
        for surface_id in ordered_surface_ids
    )
    current_surface_ids = {surface.id for surface in metadata.managed_surfaces}
    removed_surface_ids = tuple(sorted(current_surface_ids - target_surface_ids))
    blockers = [
        f"{surface.surface_id}: {blocker}"
        for surface in surfaces
        for blocker in surface.blockers
    ]
    if removed_surface_ids:
        blockers.append(
            "Target template omits currently managed surfaces; broad promotion never deletes them: "
            + ", ".join(removed_surface_ids)
        )
    return TemplatePromotionPreview(
        path=path,
        current_template=metadata.selected_template,
        target_template=target_template,
        surfaces=surfaces,
        removed_surface_ids=removed_surface_ids,
        blockers=tuple(blockers),
        can_apply=not blockers,
    )


def promote_template(
    path: Path,
    target_template: str,
    *,
    apply: bool,
    allow_dirty: bool = False,
    reference_ref: str | None = None,
) -> TemplatePromotionResult:
    preview = preview_template_promotion(path, target_template)
    if not apply:
        return TemplatePromotionResult(
            preview=preview,
            written_paths=(),
            selected_template_changed=False,
        )
    if not preview.can_apply:
        raise ValueError("Template promotion is blocked: " + "; ".join(preview.blockers))
    if not allow_dirty and _git_worktree_is_dirty(path):
        raise ValueError(
            "Refusing template promotion in a dirty Git worktree; commit/stash changes "
            "or pass --allow-dirty"
        )

    metadata_path = path / BOOTSTRAP_METADATA_PATH
    project_name, project_description = repository_identity(path)
    metadata = migrate_metadata_v2(
        load_bootstrap_metadata(metadata_path),
        project_name=project_name,
        project_description=project_description,
    )
    selected_template_changed = metadata.selected_template != target_template
    target = _plan_target_for_promotion(path, metadata, target_template)
    target_by_path = {asset.path: asset for asset in target.assets}
    writes = {
        asset.path: target_by_path[asset.path].content
        for surface in preview.surfaces
        for asset in surface.assets
        if asset.action in ("create", "replace")
    }
    target_generated_assets = tuple(
        asset.as_generated_asset() for asset in target.assets
    )
    at = _operation_time()
    surfaces, surface_assets, _ = build_managed_surfaces(
        target_template,
        target.render_context,
        target_generated_assets,
        state="written",
        command="promote-template",
        mode="apply",
        at=at,
    )
    preview_by_path = {
        asset.path: asset
        for surface in preview.surfaces
        for asset in surface.assets
    }
    surface_assets = tuple(
        replace(
            asset,
            state=(
                "adopted"
                if preview_by_path[asset.path].status in ("adopted", "adoptable")
                else "written"
            ),
            strategy=preview_by_path[asset.path].strategy,
        )
        for asset in surface_assets
    )
    adopted_surface_ids = {
        asset.surface_id for asset in surface_assets if asset.state == "adopted"
    }
    surfaces = tuple(
        replace(
            surface,
            state=("adopted" if surface.id in adopted_surface_ids else "written"),
        )
        for surface in surfaces
    )
    state_by_path = {asset.path: asset.state for asset in surface_assets}
    target_generated_assets = tuple(
        asset
        for asset in target_generated_assets
        if asset.kind == "metadata" or state_by_path.get(asset.path) == "written"
    )
    target_surface_ids = {surface.id for surface in surfaces}
    ordered_surface_ids = tuple(
        surface_id
        for surface_id in SURFACE_PROMOTION_ORDER
        if surface_id in target_surface_ids
    )
    updated = replace(
        metadata,
        schema_version=2,
        reference_ref=reference_ref or metadata.reference_ref,
        generator_version=__version__,
        selected_template=target_template,
        selected_options=target.selected_options,
        docs=target.docs,
        generated_assets=target_generated_assets,
        render_context=target.render_context,
        managed_surfaces=surfaces,
        managed_surface_assets=surface_assets,
    )
    if not writes and render_bootstrap_metadata(updated) == metadata_path.read_text():
        return TemplatePromotionResult(
            preview=preview,
            written_paths=(),
            selected_template_changed=False,
        )
    operations = tuple(
        new_metadata_operation(
            "promote-template",
            "apply",
            surface_id,
            at=at,
        )
        for surface_id in ordered_surface_ids
    )
    updated = replace(updated, history=(*metadata.history, *operations))
    writes[BOOTSTRAP_METADATA_PATH] = render_bootstrap_metadata(updated)
    _commit_writes(path, writes)
    return TemplatePromotionResult(
        preview=preview,
        written_paths=tuple(writes),
        selected_template_changed=selected_template_changed,
    )


def _operation_time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")  # noqa: UP017


def _plan_target_for_promotion(path: Path, metadata, target_template: str):
    target = plan_template_target(path, target_template)
    if metadata.selected_template == target_template and metadata.render_context is not None:
        target = replace(
            target,
            render_context=replace(
                target.render_context,
                source=metadata.render_context.source,
            ),
        )
    return target
