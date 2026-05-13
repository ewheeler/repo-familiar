from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .metadata import GeneratedAsset
from .upstream import UpstreamCandidateDiff, diff_upstream_candidate


@dataclass(frozen=True)
class UpgradeReport:
    path: Path
    safe_to_auto_apply: tuple[UpstreamCandidateDiff, ...]
    needs_user_review: tuple[UpstreamCandidateDiff, ...]
    blocked: tuple[UpstreamCandidateDiff, ...]
    unavailable: tuple[UpstreamCandidateDiff, ...]
    notes: tuple[str, ...]


def preview_upgrade(path: Path, current_reference_assets: dict[str, GeneratedAsset] | None = None) -> UpgradeReport:
    diff = diff_upstream_candidate(path, current_reference_assets)
    safe_to_auto_apply: list[UpstreamCandidateDiff] = []
    needs_user_review: list[UpstreamCandidateDiff] = []
    blocked: list[UpstreamCandidateDiff] = []
    unavailable: list[UpstreamCandidateDiff] = []

    for item in (*diff.unchanged, *diff.modified, *diff.missing, *diff.unchecked):
        if item.status == "unchecked":
            needs_user_review.append(item)
        elif item.status == "missing":
            blocked.append(item)
        elif item.status == "modified":
            blocked.append(item)
        elif item.current_reference_status == "reference-unchanged":
            unavailable.append(item)
        elif item.current_reference_status == "reference-may-have-changed":
            needs_user_review.append(item)
        elif item.current_reference_status == "source-missing-from-current-reference":
            blocked.append(item)
        else:
            unavailable.append(item)

    return UpgradeReport(
        path=path,
        safe_to_auto_apply=tuple(safe_to_auto_apply),
        needs_user_review=tuple(needs_user_review),
        blocked=tuple(blocked),
        unavailable=tuple(unavailable),
        notes=(
            "Read-only preview only; no files were changed.",
            "No safe auto-apply path exists yet because Bootstrap Metadata does not record enough template context for exact rendered comparisons.",
            "Resolve modified or missing generated assets before any future write-capable upgrade.",
        ),
    )
