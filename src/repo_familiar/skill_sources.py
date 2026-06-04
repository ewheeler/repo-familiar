from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request


STALE_STATUSES = {"fetch-error", "local-missing", "upstream-newer"}


@dataclass(frozen=True)
class SkillSourceRecord:
    name: str
    source_type: str
    source_url: str
    notes: str = ""


@dataclass(frozen=True)
class GitHubBlobSource:
    owner: str
    repo: str
    ref: str
    path: str


@dataclass(frozen=True)
class SkillSourceCheck:
    name: str
    source_type: str
    source_url: str
    status: str
    recommendation: str
    local_path: str | None = None
    upstream_path: str | None = None
    local_sha256: str | None = None
    upstream_sha256: str | None = None
    local_updated_at: str | None = None
    upstream_updated_at: str | None = None
    upstream_commit: str | None = None
    missing_support_files: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class SkillSourceReport:
    source_file: Path
    skills_root: Path
    checks: tuple[SkillSourceCheck, ...]

    @property
    def has_actionable_drift(self) -> bool:
        return any(check.status in STALE_STATUSES or check.missing_support_files for check in self.checks)


def check_skill_sources(
    source_file: Path,
    skills_root: Path,
    *,
    repo_root: Path | None = None,
    fetch_bytes=None,
    fetch_json=None,
) -> SkillSourceReport:
    fetch_bytes = fetch_bytes or _fetch_bytes
    fetch_json = fetch_json or _fetch_json
    records = parse_skill_sources(source_file.read_text())
    root = repo_root or source_file.resolve().parent.parent
    checks = [
        _check_record(record, skills_root, root, fetch_bytes=fetch_bytes, fetch_json=fetch_json)
        for record in records
    ]
    return SkillSourceReport(source_file=source_file, skills_root=skills_root, checks=tuple(checks))


def parse_skill_sources(content: str) -> tuple[SkillSourceRecord, ...]:
    records: list[SkillSourceRecord] = []
    current_name: str | None = None
    current: dict[str, str] = {}
    for line in content.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            if current_name:
                records.append(_record_from_mapping(current_name, current))
            current_name = line.strip()[:-1]
            current = {}
            continue
        if not current_name or not line.startswith("    "):
            continue
        key, separator, value = line.strip().partition(":")
        if separator and key in {"source_type", "source_url", "notes"}:
            current[key] = _unquote(value.strip())
    if current_name:
        records.append(_record_from_mapping(current_name, current))
    return tuple(records)


def _record_from_mapping(name: str, values: dict[str, str]) -> SkillSourceRecord:
    return SkillSourceRecord(
        name=name,
        source_type=values.get("source_type", ""),
        source_url=values.get("source_url", ""),
        notes=values.get("notes", ""),
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _check_record(record: SkillSourceRecord, skills_root: Path, repo_root: Path, *, fetch_bytes, fetch_json) -> SkillSourceCheck:
    local_path = skills_root / record.name / "SKILL.md"
    local_path_text = _display_path(local_path)
    if record.source_url.startswith("local:") or record.source_type == "local":
        return SkillSourceCheck(
            name=record.name,
            source_type=record.source_type,
            source_url=record.source_url,
            status="local-source",
            recommendation="no-upstream-check-needed",
            local_path=local_path_text,
        )
    blob = _parse_github_blob_url(record.source_url)
    if blob is None:
        return SkillSourceCheck(
            name=record.name,
            source_type=record.source_type,
            source_url=record.source_url,
            status="unsupported-url",
            recommendation="review-source-manually",
            local_path=local_path_text,
        )
    if not local_path.exists():
        return SkillSourceCheck(
            name=record.name,
            source_type=record.source_type,
            source_url=record.source_url,
            status="local-missing",
            recommendation="restore-vendored-skill-before-refresh",
            local_path=local_path_text,
            upstream_path=blob.path,
        )

    try:
        upstream_content = fetch_bytes(_github_raw_url(blob))
    except Exception as error:  # pragma: no cover - concrete exception types vary by runtime
        return SkillSourceCheck(
            name=record.name,
            source_type=record.source_type,
            source_url=record.source_url,
            status="fetch-error",
            recommendation="retry-upstream-check-or-review-source-manually",
            local_path=local_path_text,
            upstream_path=blob.path,
            error=f"{type(error).__name__}: {error}",
        )

    commit: dict[str, str | None] = {"sha": None, "date": None}
    metadata_error = None
    try:
        commit = _latest_github_commit(blob, fetch_json)
    except Exception as error:  # pragma: no cover - GitHub API rate limits are environment-dependent
        metadata_error = f"commit metadata unavailable: {type(error).__name__}: {error}"

    missing_support_files: list[str] = []
    try:
        missing_support_files = _missing_support_files(blob, skills_root / record.name, fetch_json)
    except Exception as error:  # pragma: no cover - GitHub API rate limits are environment-dependent
        detail = f"support file metadata unavailable: {type(error).__name__}: {error}"
        metadata_error = f"{metadata_error}; {detail}" if metadata_error else detail

    local_content = local_path.read_bytes()
    local_sha = _sha256(local_content)
    upstream_sha = _sha256(upstream_content)
    local_updated_at = _git_last_commit_time(repo_root, local_path)
    upstream_updated_at = commit.get("date")

    if local_sha == upstream_sha:
        status = "matches-upstream"
        recommendation = "no-refresh-needed"
    elif _is_upstream_newer(upstream_updated_at, local_updated_at):
        status = "upstream-newer"
        recommendation = "review-and-refresh-vendored-skill"
    else:
        status = "content-differs"
        recommendation = "review-local-adaptation-before-replacing"

    if missing_support_files and status == "matches-upstream":
        recommendation = "vendor-missing-support-files"

    return SkillSourceCheck(
        name=record.name,
        source_type=record.source_type,
        source_url=record.source_url,
        status=status,
        recommendation=recommendation,
        local_path=local_path_text,
        upstream_path=blob.path,
        local_sha256=local_sha,
        upstream_sha256=upstream_sha,
        local_updated_at=local_updated_at,
        upstream_updated_at=upstream_updated_at,
        upstream_commit=commit.get("sha"),
        missing_support_files=tuple(missing_support_files),
        error=metadata_error,
    )


def _parse_github_blob_url(url: str) -> GitHubBlobSource | None:
    parsed = urllib.parse.urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if parsed.netloc != "github.com" or len(parts) < 5 or parts[2] != "blob":
        return None
    return GitHubBlobSource(owner=parts[0], repo=parts[1], ref=parts[3], path="/".join(parts[4:]))


def _github_raw_url(source: GitHubBlobSource) -> str:
    return f"https://raw.githubusercontent.com/{source.owner}/{source.repo}/{source.ref}/{source.path}"


def _latest_github_commit(source: GitHubBlobSource, fetch_json) -> dict[str, str | None]:
    path = urllib.parse.quote(source.path)
    url = f"https://api.github.com/repos/{source.owner}/{source.repo}/commits?sha={source.ref}&path={path}&per_page=1"
    payload = fetch_json(url)
    if not payload:
        return {"sha": None, "date": None}
    commit = payload[0]
    return {
        "sha": commit.get("sha"),
        "date": commit.get("commit", {}).get("committer", {}).get("date"),
    }


def _missing_support_files(source: GitHubBlobSource, local_skill_root: Path, fetch_json) -> list[str]:
    upstream_parent = Path(source.path).parent
    upstream_root = "" if upstream_parent.as_posix() == "." else upstream_parent.as_posix()
    upstream_files = _github_contents_files(source.owner, source.repo, source.ref, upstream_root, fetch_json)
    local_files = {
        path.relative_to(local_skill_root).as_posix()
        for path in local_skill_root.rglob("*")
        if path.is_file()
    }
    return sorted(path for path in upstream_files if path not in local_files)


def _github_contents_files(owner: str, repo: str, ref: str, path: str, fetch_json, *, prefix: str = "") -> set[str]:
    quoted_path = urllib.parse.quote(path)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quoted_path}?ref={ref}"
    payload = fetch_json(url)
    files: set[str] = set()
    for item in payload:
        name = item.get("name", "")
        relative = f"{prefix}{name}"
        if item.get("type") == "file":
            files.add(relative)
        elif item.get("type") == "dir":
            files.update(
                _github_contents_files(
                    owner,
                    repo,
                    ref,
                    f"{path}/{name}",
                    fetch_json,
                    prefix=f"{relative}/",
                )
            )
    return files


def _git_last_commit_time(repo_root: Path, path: Path) -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return output or None


def _is_upstream_newer(upstream_updated_at: str | None, local_updated_at: str | None) -> bool:
    if not upstream_updated_at or not local_updated_at:
        return False
    return _parse_datetime(upstream_updated_at) > _parse_datetime(local_updated_at)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "repo-familiar-skill-source-check"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _fetch_json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-familiar-skill-source-check",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _display_path(path: Path) -> str:
    return path.as_posix()
