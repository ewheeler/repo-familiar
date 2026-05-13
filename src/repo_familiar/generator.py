from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re

from . import __version__
from .advice import AdviceReport, advise_existing_repository as _advise_existing_repository
from .asset_plan import (
    BOOTSTRAP_METADATA_PATH,
    PlannedAsset,
    asset_kind,
    filter_planned_assets,
    plan_skill_assets,
    plan_template_assets,
)
from .metadata import (
    BootstrapMetadata,
    GeneratedAsset,
    load_bootstrap_metadata,
    render_bootstrap_metadata,
)
from . import profiles as profile_registry


@dataclass(frozen=True)
class GenerationOptions:
    name: str
    description: str
    output_dir: Path
    template: str = "basic"
    docs: str = "quarto"
    agent_harnesses: tuple[str, ...] = ("opencode",)
    model_profiles: tuple[str, ...] = ("default-coding",)
    tool_profiles: tuple[str, ...] = ("cq",)
    memory_profiles: tuple[str, ...] = ("memory-local",)
    prompt_profiles: tuple[str, ...] = ()
    safety_profiles: tuple[str, ...] = ()
    privacy_profiles: tuple[str, ...] = ()
    repomap_profiles: tuple[str, ...] = ()
    sandbox_profiles: tuple[str, ...] = ()
    secrets_profiles: tuple[str, ...] = ("dotenv-local", "kvenv-azure-keyvault")
    design_profiles: tuple[str, ...] = ()
    worktree_profiles: tuple[str, ...] = ()
    skills: tuple[str, ...] = ("grill-with-docs",)
    reference_type: str = "local"
    reference_url: str = "local"
    reference_ref: str = "unknown"
    generated_at: str | None = None
    bootstrap_mode: str = "new_repository"
    force: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class ExistingBootstrapOptions:
    path: Path
    name: str | None = None
    description: str = "Bootstrapped with repo-familiar."
    template: str = "basic"
    docs: str = "quarto"
    agent_harnesses: tuple[str, ...] = ("opencode",)
    model_profiles: tuple[str, ...] = ("default-coding",)
    tool_profiles: tuple[str, ...] = ("cq",)
    memory_profiles: tuple[str, ...] = ("memory-local",)
    prompt_profiles: tuple[str, ...] = ()
    safety_profiles: tuple[str, ...] = ()
    privacy_profiles: tuple[str, ...] = ()
    repomap_profiles: tuple[str, ...] = ()
    sandbox_profiles: tuple[str, ...] = ()
    secrets_profiles: tuple[str, ...] = ("dotenv-local", "kvenv-azure-keyvault")
    design_profiles: tuple[str, ...] = ()
    worktree_profiles: tuple[str, ...] = ()
    skills: tuple[str, ...] = ("grill-with-docs",)
    reference_type: str = "local"
    reference_url: str = "local"
    reference_ref: str = "unknown"
    generated_at: str | None = None
    asset_groups: tuple[str, ...] = ("all",)
    force: bool = False


@dataclass(frozen=True)
class AuditReport:
    path: Path
    missing: tuple[GeneratedAsset, ...]
    present: tuple[GeneratedAsset, ...]
    conflicts: tuple[GeneratedAsset, ...]


@dataclass(frozen=True)
class BootstrapExistingResult:
    report: AuditReport
    written: tuple[GeneratedAsset, ...]
    skipped_conflicts: tuple[GeneratedAsset, ...]


@dataclass(frozen=True)
class CheckedAsset:
    asset: GeneratedAsset
    status: str
    current_sha256: str | None = None


@dataclass(frozen=True)
class CheckReport:
    path: Path
    ok: tuple[CheckedAsset, ...]
    modified: tuple[CheckedAsset, ...]
    missing: tuple[CheckedAsset, ...]
    unchecked: tuple[CheckedAsset, ...]


def generate_project(options: GenerationOptions) -> list[GeneratedAsset]:
    output_dir = options.output_dir
    if not options.dry_run:
        _validate_output_dir(output_dir, force=options.force)
        output_dir.mkdir(parents=True, exist_ok=True)

    planned_assets = plan_project(options)
    if not options.dry_run:
        for asset in planned_assets:
            _write_text(output_dir / asset.path, asset.content, force=options.force)
    return [asset.as_generated_asset() for asset in planned_assets]


def plan_project(options: GenerationOptions) -> list[PlannedAsset]:
    _validate_options(options)
    template_root = _template_root(options.template)
    context = _template_context(options)
    planned_assets = plan_template_assets(template_root, options.template, context)
    planned_assets.extend(
        plan_skill_assets(Path(__file__).with_name("templates") / "skills", options.skills, context)
    )

    generated_assets = [asset.as_generated_asset() for asset in planned_assets]
    bootstrap_asset = PlannedAsset(
        path=BOOTSTRAP_METADATA_PATH,
        kind=asset_kind(BOOTSTRAP_METADATA_PATH),
        source="generator:bootstrap",
        content="",
    )
    all_assets = [*generated_assets, bootstrap_asset.as_generated_asset()]
    return [
        *planned_assets,
        PlannedAsset(
            path=bootstrap_asset.path,
            kind=bootstrap_asset.kind,
            source=bootstrap_asset.source,
            content=_render_bootstrap(options, all_assets),
        ),
    ]


def audit_existing_repository(options: ExistingBootstrapOptions) -> AuditReport:
    if not options.path.exists() or not options.path.is_dir():
        raise NotADirectoryError(f"Existing repository path is not a directory: {options.path}")

    generation_options = _generation_options_from_existing(options)
    missing: list[GeneratedAsset] = []
    present: list[GeneratedAsset] = []
    conflicts: list[GeneratedAsset] = []
    for asset in filter_planned_assets(plan_project(generation_options), options.asset_groups):
        generated_asset = asset.as_generated_asset()
        target = options.path / asset.path
        if not target.exists():
            missing.append(generated_asset)
        elif asset.path == ".repo-familiar/bootstrap.yml" and target.is_file():
            present.append(generated_asset)
        elif target.is_file() and target.read_text() == asset.content:
            present.append(generated_asset)
        else:
            conflicts.append(generated_asset)

    return AuditReport(
        path=options.path,
        missing=tuple(missing),
        present=tuple(present),
        conflicts=tuple(conflicts),
    )


def bootstrap_existing_repository(options: ExistingBootstrapOptions) -> BootstrapExistingResult:
    report = audit_existing_repository(options)
    generation_options = _generation_options_from_existing(options)
    planned_assets = filter_planned_assets(plan_project(generation_options), options.asset_groups)
    planned_by_path = {asset.path: asset for asset in planned_assets}
    writable_assets = list(report.missing)
    skipped_conflicts = list(report.conflicts)
    if options.force:
        writable_assets.extend(report.conflicts)
        skipped_conflicts = []

    if BOOTSTRAP_METADATA_PATH in planned_by_path:
        written_asset_paths = {asset.path for asset in writable_assets}
        bootstrap_asset = planned_by_path[BOOTSTRAP_METADATA_PATH].as_generated_asset()
        if bootstrap_asset.path in written_asset_paths:
            actual_assets = [
                planned_by_path[asset.path].as_generated_asset()
                for asset in writable_assets
            ]
            planned_by_path[bootstrap_asset.path] = PlannedAsset(
                path=bootstrap_asset.path,
                kind=bootstrap_asset.kind,
                source=bootstrap_asset.source,
                content=_render_bootstrap(generation_options, actual_assets),
            )

    written: list[GeneratedAsset] = []
    for generated_asset in writable_assets:
        planned_asset = planned_by_path[generated_asset.path]
        _write_text(options.path / planned_asset.path, planned_asset.content, force=options.force)
        written.append(generated_asset)

    return BootstrapExistingResult(
        report=report,
        written=tuple(written),
        skipped_conflicts=tuple(skipped_conflicts),
    )


def check_generated_repository(path: Path) -> CheckReport:
    bootstrap_path = path / ".repo-familiar/bootstrap.yml"
    if not bootstrap_path.exists():
        raise FileNotFoundError(f"Bootstrap metadata not found: {bootstrap_path}")

    metadata = load_bootstrap_metadata(bootstrap_path)
    ok: list[CheckedAsset] = []
    modified: list[CheckedAsset] = []
    missing: list[CheckedAsset] = []
    unchecked: list[CheckedAsset] = []
    for asset in metadata.generated_assets:
        target = path / asset.path
        if not target.exists():
            missing.append(CheckedAsset(asset=asset, status="missing"))
        elif not asset.content_sha256:
            unchecked.append(CheckedAsset(asset=asset, status="unchecked"))
        else:
            current_sha256 = _content_sha256(target.read_text())
            checked = CheckedAsset(
                asset=asset,
                status="ok" if current_sha256 == asset.content_sha256 else "modified",
                current_sha256=current_sha256,
            )
            if checked.status == "ok":
                ok.append(checked)
            else:
                modified.append(checked)

    return CheckReport(
        path=path,
        ok=tuple(ok),
        modified=tuple(modified),
        missing=tuple(missing),
        unchecked=tuple(unchecked),
    )


def advise_existing_repository(path: Path) -> AdviceReport:
    return _advise_existing_repository(path)


def list_templates() -> list[str]:
    templates_root = Path(__file__).with_name("templates")
    return sorted(
        path.name
        for path in templates_root.iterdir()
        if path.is_dir() and path.name != "skills"
    )


def list_model_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.MODEL_PROFILES)


def list_tool_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.TOOL_PROFILES)


def list_memory_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.MEMORY_PROFILES)


def list_prompt_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.PROMPT_PROFILES)


def list_safety_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.SAFETY_PROFILES)


def list_privacy_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.PRIVACY_PROFILES)


def list_repomap_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.REPOMAP_PROFILES)


def list_sandbox_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.SANDBOX_PROFILES)


def list_secrets_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.SECRETS_PROFILES)


def list_design_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.DESIGN_PROFILES)


def list_worktree_profiles() -> list[str]:
    return profile_registry.list_names(profile_registry.WORKTREE_PROFILES)


def list_skills() -> list[str]:
    return profile_registry.list_names(profile_registry.SKILLS)


def _validate_options(options: GenerationOptions) -> None:
    profile_registry.validate_profile_selections(
        {
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
            "skills": options.skills,
        }
    )
    if options.docs != "quarto":
        raise ValueError("Only docs=quarto is supported by the initial generator")
    if options.template not in list_templates():
        known = ", ".join(list_templates())
        raise ValueError(f"Unknown template: {options.template}. Known templates: {known}")


def _template_root(template: str) -> Path:
    root = Path(__file__).with_name("templates") / template
    if not root.exists():
        raise ValueError(f"Unknown template: {template}")
    return root


def _validate_output_dir(output_dir: Path, *, force: bool) -> None:
    if force or not output_dir.exists():
        return
    if not output_dir.is_dir():
        raise NotADirectoryError(f"Output path exists and is not a directory: {output_dir}")
    if any(output_dir.iterdir()):
        raise FileExistsError(
            f"Refusing to generate into non-empty directory without --force: {output_dir}"
        )


def _template_context(options: GenerationOptions) -> dict[str, str]:
    return {
        "project_name": options.name,
        "project_slug": _slugify(options.name),
        "project_description": options.description,
        "agent_harnesses_list": _markdown_list(options.agent_harnesses),
        "model_profiles_yaml": profile_registry.render_model_profiles(options.model_profiles),
        "selected_model_profiles_list": _markdown_list(options.model_profiles),
        "tool_profiles_yaml": profile_registry.render_tool_profiles(options.tool_profiles),
        "selected_tool_profiles_list": _markdown_list(options.tool_profiles),
        "memory_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.MEMORY_PROFILES, options.memory_profiles),
        "selected_memory_profiles_list": _markdown_list(options.memory_profiles),
        "prompt_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.PROMPT_PROFILES, options.prompt_profiles),
        "selected_prompt_profiles_list": _markdown_list(options.prompt_profiles),
        "safety_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.SAFETY_PROFILES, options.safety_profiles),
        "selected_safety_profiles_list": _markdown_list(options.safety_profiles),
        "privacy_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.PRIVACY_PROFILES, options.privacy_profiles),
        "selected_privacy_profiles_list": _markdown_list(options.privacy_profiles),
        "repomap_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.REPOMAP_PROFILES, options.repomap_profiles),
        "selected_repomap_profiles_list": _markdown_list(options.repomap_profiles),
        "sandbox_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.SANDBOX_PROFILES, options.sandbox_profiles),
        "selected_sandbox_profiles_list": _markdown_list(options.sandbox_profiles),
        "secrets_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.SECRETS_PROFILES, options.secrets_profiles),
        "selected_secrets_profiles_list": _markdown_list(options.secrets_profiles),
        "design_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.DESIGN_PROFILES, options.design_profiles),
        "selected_design_profiles_list": _markdown_list(options.design_profiles),
        "worktree_profiles_yaml": profile_registry.render_advisory_profiles(profile_registry.WORKTREE_PROFILES, options.worktree_profiles),
        "selected_worktree_profiles_list": _markdown_list(options.worktree_profiles),
        "selected_skills_list": _markdown_list(options.skills),
        "skill_sources_yaml": profile_registry.render_skill_sources(options.skills),
    }


def _render_bootstrap(options: GenerationOptions, assets: list[GeneratedAsset]) -> str:
    metadata = BootstrapMetadata(
        schema_version=1,
        bootstrap_mode=options.bootstrap_mode,
        reference_type=options.reference_type,
        reference_url=options.reference_url,
        reference_ref=options.reference_ref,
        generated_at=options.generated_at or _utc_now(),
        generator_name="repo-familiar",
        generator_version=__version__,
        selected_template=options.template,
        selected_options={
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
            "skills": options.skills,
        },
        docs=options.docs,
        generated_assets=tuple(assets),
    )
    return render_bootstrap_metadata(metadata)


def _write_text(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _markdown_list(values: tuple[str, ...]) -> str:
    return "\n".join(f"- `{value}`" for value in values)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "generated-project"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _generation_options_from_existing(options: ExistingBootstrapOptions) -> GenerationOptions:
    return GenerationOptions(
        name=options.name or options.path.name,
        description=options.description,
        output_dir=options.path,
        template=options.template,
        docs=options.docs,
        agent_harnesses=options.agent_harnesses,
        model_profiles=options.model_profiles,
        tool_profiles=options.tool_profiles,
        memory_profiles=options.memory_profiles,
        prompt_profiles=options.prompt_profiles,
        safety_profiles=options.safety_profiles,
        privacy_profiles=options.privacy_profiles,
        repomap_profiles=options.repomap_profiles,
        sandbox_profiles=options.sandbox_profiles,
        secrets_profiles=options.secrets_profiles,
        design_profiles=options.design_profiles,
        worktree_profiles=options.worktree_profiles,
        skills=options.skills,
        reference_type=options.reference_type,
        reference_url=options.reference_url,
        reference_ref=options.reference_ref,
        generated_at=options.generated_at,
        bootstrap_mode="existing_repository",
        force=options.force,
    )


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
