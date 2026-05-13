from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .asset_plan import BOOTSTRAP_METADATA_PATH
from .metadata import GeneratedAsset, load_bootstrap_metadata


@dataclass(frozen=True)
class UpstreamCandidateDiff:
    asset: GeneratedAsset
    status: str
    recommendation: str
    current_sha256: str | None = None
    current_reference_sha256: str | None = None
    current_reference_status: str = "not_checked"


@dataclass(frozen=True)
class UpstreamCandidateReport:
    path: Path
    unchanged: tuple[UpstreamCandidateDiff, ...]
    modified: tuple[UpstreamCandidateDiff, ...]
    missing: tuple[UpstreamCandidateDiff, ...]
    unchecked: tuple[UpstreamCandidateDiff, ...]


def diff_upstream_candidate(path: Path, current_reference_assets: dict[str, GeneratedAsset] | None = None) -> UpstreamCandidateReport:
    bootstrap_path = path / BOOTSTRAP_METADATA_PATH
    if not bootstrap_path.exists():
        raise FileNotFoundError(f"Bootstrap metadata not found: {bootstrap_path}")

    metadata = load_bootstrap_metadata(bootstrap_path)
    unchanged: list[UpstreamCandidateDiff] = []
    modified: list[UpstreamCandidateDiff] = []
    missing: list[UpstreamCandidateDiff] = []
    unchecked: list[UpstreamCandidateDiff] = []

    for asset in metadata.generated_assets:
        target = path / asset.path
        current_reference_asset = (current_reference_assets or {}).get(asset.path)
        current_reference_sha256 = current_reference_asset.content_sha256 if current_reference_asset else None
        current_reference_status = _current_reference_status(asset, current_reference_asset)

        if not target.exists():
            missing.append(
                UpstreamCandidateDiff(
                    asset=asset,
                    status="missing",
                    recommendation="restore-generated-asset",
                    current_reference_sha256=current_reference_sha256,
                    current_reference_status=current_reference_status,
                )
            )
            continue

        if not asset.content_sha256:
            unchecked.append(
                UpstreamCandidateDiff(
                    asset=asset,
                    status="unchecked",
                    recommendation="review-metadata-manually",
                    current_reference_sha256=current_reference_sha256,
                    current_reference_status=current_reference_status,
                )
            )
            continue

        current_sha256 = _content_sha256(target.read_text())
        if current_sha256 == asset.content_sha256:
            unchanged.append(
                UpstreamCandidateDiff(
                    asset=asset,
                    status="unchanged",
                    recommendation="no-upstream-action",
                    current_sha256=current_sha256,
                    current_reference_sha256=current_reference_sha256,
                    current_reference_status=current_reference_status,
                )
            )
        else:
            modified.append(
                UpstreamCandidateDiff(
                    asset=asset,
                    status="modified",
                    recommendation=_modified_recommendation(asset.path),
                    current_sha256=current_sha256,
                    current_reference_sha256=current_reference_sha256,
                    current_reference_status=current_reference_status,
                )
            )

    return UpstreamCandidateReport(
        path=path,
        unchanged=tuple(unchanged),
        modified=tuple(modified),
        missing=tuple(missing),
        unchecked=tuple(unchecked),
    )


def _current_reference_status(asset: GeneratedAsset, current_reference_asset: GeneratedAsset | None) -> str:
    if asset.kind == "metadata":
        return "not_checked"
    if current_reference_asset is None:
        return "source-missing-from-current-reference"
    if not asset.content_sha256 or not current_reference_asset.content_sha256:
        return "not_checked"
    if asset.content_sha256 == current_reference_asset.content_sha256:
        return "reference-unchanged"
    return "reference-may-have-changed"


def _modified_recommendation(path: str) -> str:
    if path in (".env.example", ".agents/secrets.yml"):
        return "review-private-or-local-only"
    if path.startswith(".agents/skills/") or path.startswith("docs/") or path in ("AGENTS.md", "README.md", "plan.md"):
        return "review-for-upstream-improvement"
    if path.startswith(".agents/"):
        return "review-profile-improvement"
    return "review-local-customization"


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
