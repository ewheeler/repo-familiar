from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from . import __version__
from .asset_plan import BOOTSTRAP_METADATA_PATH, PlannedAsset, asset_in_groups
from .metadata import GeneratedAsset, load_bootstrap_metadata, render_bootstrap_metadata
from .upstream import UpstreamCandidateDiff


@dataclass(frozen=True)
class UpgradeReport:
    path: Path
    asset_groups: tuple[str, ...]
    safe_to_auto_apply: tuple[UpstreamCandidateDiff, ...]
    needs_user_review: tuple[UpstreamCandidateDiff, ...]
    blocked: tuple[UpstreamCandidateDiff, ...]
    unavailable: tuple[UpstreamCandidateDiff, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class UpgradeApplyResult:
    report: UpgradeReport
    written_paths: tuple[str, ...]


def preview_upgrade(
    path: Path,
    current_reference_assets: dict[str, GeneratedAsset] | None = None,
    *,
    asset_groups: tuple[str, ...] = ("all",),
) -> UpgradeReport:
    metadata_path = _safe_path(path, BOOTSTRAP_METADATA_PATH)
    if not metadata_path.exists():
        raise FileNotFoundError(f"Bootstrap metadata not found: {metadata_path}")

    metadata = load_bootstrap_metadata(metadata_path)
    references = current_reference_assets or {}
    recorded = {
        asset.path: asset
        for asset in metadata.generated_assets
        if _in_groups(asset.path, asset_groups)
    }
    safe: list[UpstreamCandidateDiff] = []
    review: list[UpstreamCandidateDiff] = []
    blocked: list[UpstreamCandidateDiff] = []
    unavailable: list[UpstreamCandidateDiff] = []

    for asset in recorded.values():
        candidate = _recorded_candidate(path, asset, references.get(asset.path))
        _classify(candidate, safe, review, blocked, unavailable)

    for reference in references.values():
        if reference.path in recorded or not _in_groups(reference.path, asset_groups):
            continue
        candidate = _new_reference_candidate(path, reference)
        _classify(candidate, safe, review, blocked, unavailable)

    return UpgradeReport(
        path=path,
        asset_groups=asset_groups,
        safe_to_auto_apply=tuple(safe),
        needs_user_review=tuple(review),
        blocked=tuple(blocked),
        unavailable=tuple(unavailable),
        notes=(
            "Read-only preview; no files were changed.",
            "Apply is currently limited to unchanged vendored skills and missing skill support files.",
            "Docs, profile, and template assets report conservative merge strategies but remain preview-only.",
        ),
    )


def apply_upgrade(
    path: Path,
    current_reference_assets: dict[str, PlannedAsset],
    *,
    asset_groups: tuple[str, ...],
    reference_ref: str | None = None,
    allow_dirty: bool = False,
) -> UpgradeApplyResult:
    if set(asset_groups) != {"skills"}:
        raise ValueError("Upgrade apply currently requires --asset-group skills")
    if not allow_dirty and _git_worktree_is_dirty(path):
        raise ValueError("Refusing upgrade apply in a dirty Git worktree; commit/stash changes or pass --allow-dirty")

    generated = {key: asset.as_generated_asset() for key, asset in current_reference_assets.items()}
    report = preview_upgrade(path, generated, asset_groups=asset_groups)
    safe_paths = {
        item.asset.path
        for item in report.safe_to_auto_apply
        if item.asset.path.startswith(".agents/skills/")
    }
    refreshed_assets: dict[str, GeneratedAsset] = {}
    safe_targets = {asset_path: _safe_path(path, asset_path) for asset_path in safe_paths}
    source_path = ".agents/skill-sources.yml"
    source_target = _safe_path(path, source_path)
    metadata_path = _safe_path(path, BOOTSTRAP_METADATA_PATH)
    planned_sources = current_reference_assets.get(source_path)
    merged_sources = None
    if planned_sources:
        merged_sources = _merge_yaml_mapping(
            source_target.read_text() if source_target.exists() else "skills:\n",
            planned_sources.content,
            "skills",
        )

    writes: dict[str, str] = {}
    for asset_path in sorted(safe_paths):
        planned = current_reference_assets[asset_path]
        if not safe_targets[asset_path].exists() or safe_targets[asset_path].read_text() != planned.content:
            writes[asset_path] = planned.content
        refreshed_assets[asset_path] = planned.as_generated_asset()

    if planned_sources and merged_sources is not None:
        if not source_target.exists() or source_target.read_text() != merged_sources:
            writes[source_path] = merged_sources
        refreshed_assets[source_path] = GeneratedAsset(
            path=source_path,
            kind=planned_sources.kind,
            source=planned_sources.source,
            content_sha256=_content_sha256(merged_sources),
        )

    metadata = load_bootstrap_metadata(metadata_path)
    assets_by_path = {asset.path: asset for asset in metadata.generated_assets}
    assets_by_path.update(refreshed_assets)
    updated_metadata = replace(
        metadata,
        reference_ref=reference_ref or f"repo-familiar@{__version__}",
        generator_version=__version__,
        generated_assets=tuple(assets_by_path[key] for key in sorted(assets_by_path)),
    )
    rendered_metadata = render_bootstrap_metadata(updated_metadata)
    if metadata_path.read_text() != rendered_metadata:
        writes[BOOTSTRAP_METADATA_PATH] = rendered_metadata

    _commit_writes(path, writes)
    return UpgradeApplyResult(report=report, written_paths=tuple(writes))


def _recorded_candidate(
    root: Path,
    asset: GeneratedAsset,
    reference: GeneratedAsset | None,
) -> UpstreamCandidateDiff:
    target = _safe_path(root, asset.path)
    reference_sha = reference.content_sha256 if reference else None
    strategy = _strategy(asset.path)
    if reference is None:
        return UpstreamCandidateDiff(
            asset=asset,
            status="source-removed",
            recommendation="review-removed-reference-asset",
            current_sha256=_content_sha256(target.read_text()) if target.is_file() else None,
            current_reference_status="source-missing-from-current-reference",
            strategy=strategy,
        )
    if not target.exists():
        recommendation = "add-missing-support-file" if _is_skill_support(asset.path) and reference else "restore-generated-asset"
        return UpstreamCandidateDiff(
            asset=asset,
            status="missing",
            recommendation=recommendation,
            current_reference_sha256=reference_sha,
            current_reference_status="reference-may-have-changed" if reference else "source-missing-from-current-reference",
            strategy="add_missing_support_file" if recommendation == "add-missing-support-file" else strategy,
        )
    if not asset.content_sha256:
        return UpstreamCandidateDiff(asset=asset, status="unchecked", recommendation="review-metadata-manually", strategy=strategy)

    current_sha = _content_sha256(target.read_text())
    if current_sha != asset.content_sha256:
        return UpstreamCandidateDiff(
            asset=asset,
            status="modified",
            recommendation="preserve-downstream-change",
            current_sha256=current_sha,
            current_reference_sha256=reference_sha,
            current_reference_status=_reference_status(asset, reference),
            strategy=strategy,
        )
    return UpstreamCandidateDiff(
        asset=asset,
        status="unchanged",
        recommendation="refresh-generated-asset" if _reference_status(asset, reference) == "reference-may-have-changed" else "no-upstream-action",
        current_sha256=current_sha,
        current_reference_sha256=reference_sha,
        current_reference_status=_reference_status(asset, reference),
        strategy=strategy,
    )


def _new_reference_candidate(root: Path, reference: GeneratedAsset) -> UpstreamCandidateDiff:
    target = _safe_path(root, reference.path)
    if _is_skill_support(reference.path) and not target.exists():
        return UpstreamCandidateDiff(
            asset=reference,
            status="missing",
            recommendation="add-missing-support-file",
            current_reference_sha256=reference.content_sha256,
            current_reference_status="reference-may-have-changed",
            strategy="add_missing_support_file",
        )
    strategy = "add_if_missing_preview" if not target.exists() else _strategy(reference.path)
    return UpstreamCandidateDiff(
        asset=reference,
        status="untracked-reference-asset",
        recommendation="add-new-reference-asset" if not target.exists() else "review-new-reference-asset",
        current_reference_sha256=reference.content_sha256,
        current_reference_status="reference-may-have-changed",
        strategy=strategy,
    )


def _classify(candidate, safe, review, blocked, unavailable) -> None:
    if candidate.strategy == "add_missing_support_file":
        safe.append(candidate)
    elif candidate.asset.path == ".agents/skill-sources.yml" and candidate.current_reference_sha256 is not None and candidate.current_reference_status != "reference-unchanged":
        safe.append(candidate)
    elif (
        candidate.status == "unchanged"
        and candidate.current_reference_status == "reference-may-have-changed"
        and candidate.strategy == "replace_if_unchanged"
    ):
        safe.append(candidate)
    elif candidate.status == "modified" and candidate.asset.path.startswith(".agents/skills/"):
        review.append(candidate)
    elif candidate.status in ("modified", "missing", "source-removed"):
        blocked.append(candidate)
    elif candidate.current_reference_status == "reference-may-have-changed" or candidate.status == "unchecked":
        review.append(candidate)
    else:
        unavailable.append(candidate)


def _strategy(path: str) -> str:
    if path.startswith(".agents/skills/"):
        return "replace_if_unchanged"
    if path == ".agents/skill-sources.yml":
        return "mapping_merge"
    if path.startswith(".agents/") and path.endswith(".yml"):
        return "mapping_merge_preview"
    if path == ".gitignore":
        return "line_union_preview"
    if path == "AGENTS.md":
        return "heading_merge_preview"
    if path == "opencode.json":
        return "json_merge_preview"
    if path.startswith("docs/") or path in ("README.md", "plan.md"):
        return "manual_review"
    return "replace_if_unchanged_preview"


def _in_groups(path: str, asset_groups: tuple[str, ...]) -> bool:
    return "all" in asset_groups or asset_in_groups(path, asset_groups)


def _is_skill_support(path: str) -> bool:
    return path.startswith(".agents/skills/") and not path.endswith("/SKILL.md")


def _reference_status(asset: GeneratedAsset, reference: GeneratedAsset | None) -> str:
    if reference is None:
        return "source-missing-from-current-reference"
    if not asset.content_sha256 or not reference.content_sha256:
        return "not_checked"
    return "reference-unchanged" if asset.content_sha256 == reference.content_sha256 else "reference-may-have-changed"


def _merge_yaml_mapping(existing: str, generated: str, section: str) -> str:
    existing_entries = _yaml_entries(existing, section)
    generated_entries = _yaml_entries(generated, section)
    merged = dict(existing_entries)
    for key, generated_entry in generated_entries.items():
        merged[key] = _merge_yaml_entry(existing_entries.get(key), generated_entry)
    lines = [f"{section}:"] if merged else [f"{section}: {{}}"]
    for key in sorted(merged):
        lines.extend(merged[key])
    replacement = "\n".join(lines)
    section_start, section_end = _yaml_section_bounds(existing, section)
    if section_start is None:
        prefix = existing.rstrip("\n")
        return f"{prefix}\n{replacement}\n" if prefix else f"{replacement}\n"
    existing_lines = existing.splitlines()
    return "\n".join([*existing_lines[:section_start], replacement, *existing_lines[section_end:]]) + "\n"


def _merge_yaml_entry(existing: list[str] | None, generated: list[str]) -> list[str]:
    if not existing:
        return generated
    existing_fields = _yaml_entry_fields(existing)
    generated_fields = _yaml_entry_fields(generated)
    fields = dict(existing_fields)
    fields.update(generated_fields)
    comments = [line for line in existing[1:] if line.lstrip().startswith("#") and line not in generated]
    ordered_keys = [*generated_fields, *[key for key in existing_fields if key not in generated_fields]]
    lines = [generated[0], *comments]
    for key in ordered_keys:
        lines.extend(fields[key])
    seen_comments: set[str] = set()
    deduplicated: list[str] = []
    for line in lines:
        if line.lstrip().startswith("#"):
            if line in seen_comments:
                continue
            seen_comments.add(line)
        deduplicated.append(line)
    return deduplicated


def _yaml_entry_fields(entry: list[str]) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in entry[1:]:
        if line.startswith("    ") and not line.startswith("      ") and ":" in line and not line.lstrip().startswith("#"):
            current = line.strip().split(":", 1)[0]
            fields[current] = [line]
        elif current:
            fields[current].append(line)
    return fields


def _yaml_entries(content: str, section: str) -> dict[str, list[str]]:
    entries: dict[str, list[str]] = {}
    current: str | None = None
    in_section = False
    for line in content.splitlines():
        if line == f"{section}:":
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            break
        if not in_section:
            continue
        if line.startswith("  ") and not line.startswith("    ") and ":" in line and not line.endswith(":"):
            raise ValueError(f"Inline YAML mappings are not supported for upgrade merges in {section}")
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current = line.strip()[:-1]
            entries[current] = [line]
        elif current:
            entries[current].append(line)
    return entries


def _yaml_section_bounds(content: str, section: str) -> tuple[int | None, int]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{section}:"):
            continue
        if line not in (f"{section}:", f"{section}: {{}}"):
            raise ValueError(f"Inline YAML mappings are not supported for upgrade merges in {section}")
        end = index + 1
        while end < len(lines) and (not lines[end] or lines[end].startswith(" ")):
            end += 1
        return index, end
    return None, len(lines)


def _safe_path(root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Generated asset path escapes repository: {relative_path}")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Refusing to refresh symlinked asset path: {relative_path}")
    try:
        current.resolve(strict=False).relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"Generated asset path escapes repository: {relative_path}") from error
    return current


def _git_worktree_is_dirty(path: Path) -> bool:
    try:
        inside = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if inside.returncode != 0:
            if _has_git_marker(path):
                raise ValueError("Unable to verify Git worktree state for upgrade: Git metadata is present but invalid")
            return False
        if inside.stdout.strip() != "true":
            raise ValueError("Unable to verify Git worktree state for upgrade: unexpected git rev-parse output")
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError(f"Unable to verify Git worktree state for upgrade: {error}") from error
    return bool(status.stdout.strip())


def _has_git_marker(path: Path) -> bool:
    return any((candidate / ".git").exists() or (candidate / ".git").is_symlink() for candidate in (path, *path.parents))


def _commit_writes(root: Path, writes: dict[str, str]) -> None:
    targets = {relative: _safe_path(root, relative) for relative in writes}
    originals = {
        relative: target.read_text() if target.exists() else None
        for relative, target in targets.items()
    }
    modes = {
        relative: (target.stat().st_mode & 0o777) if target.exists() else 0o644
        for relative, target in targets.items()
    }
    staged: dict[str, Path] = {}
    replaced: list[str] = []
    try:
        for relative, content in writes.items():
            target = targets[relative]
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".repo-familiar-upgrade-", dir=target.parent)
            with os.fdopen(descriptor, "w") as handle:
                handle.write(content)
            os.chmod(temporary, modes[relative])
            staged[relative] = Path(temporary)
        for relative in writes:
            os.replace(staged[relative], targets[relative])
            replaced.append(relative)
    except Exception:
        for relative in reversed(replaced):
            original = originals[relative]
            target = targets[relative]
            if original is None:
                target.unlink(missing_ok=True)
            else:
                descriptor, temporary = tempfile.mkstemp(prefix=".repo-familiar-rollback-", dir=target.parent)
                with os.fdopen(descriptor, "w") as handle:
                    handle.write(original)
                os.chmod(temporary, modes[relative])
                os.replace(temporary, target)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
