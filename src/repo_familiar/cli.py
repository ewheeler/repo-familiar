from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from . import __version__
from . import profiles
from .generator import (
    ExistingBootstrapOptions,
    GenerationOptions,
    advise_existing_repository,
    audit_existing_repository,
    bootstrap_existing_repository,
    check_generated_repository,
    generate_project,
    list_agent_harnesses,
    list_design_profiles,
    list_memory_profiles,
    list_model_profiles,
    list_privacy_profiles,
    list_public_interest_profiles,
    list_prompt_profiles,
    list_repomap_profiles,
    list_safety_profiles,
    list_sandbox_profiles,
    list_secrets_profiles,
    list_skills,
    list_templates,
    list_tool_profiles,
    list_worktree_profiles,
    plan_project,
)
from .asset_plan import BOOTSTRAP_METADATA_PATH, PlannedAsset, asset_in_groups
from .interactive import (
    InteractiveCancelled,
    InteractiveUnavailable,
    prompt_existing_options,
    prompt_generation_options,
)
from .metadata import GeneratedAsset, load_bootstrap_metadata
from .skill_sources import check_skill_sources
from .upstream import diff_upstream_candidate
from .upgrade import apply_upgrade, preview_upgrade


@dataclass(frozen=True)
class TargetedAddCommand:
    required_attr: str | None
    required_message: str | None
    keep_attrs: tuple[str, ...]
    asset_groups: tuple[str, ...]


@dataclass(frozen=True)
class TargetedAddGuidance:
    generated_assets: tuple[GeneratedAsset, ...]
    warnings: tuple[str, ...]
    follow_up: tuple[str, ...]


@dataclass(frozen=True)
class ProfileFamilyCommand:
    selection_attr: str
    list_command: str
    list_help: str
    list_profiles: Callable[[], list[str]]
    add_command: str
    add_help: str
    required_message: str
    apply_help: str
    force_help: str
    asset_group: str
    add_selection_alias: str | None = None


SELECTION_ATTRS = (
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
    "skills",
)


PROFILE_FAMILY_COMMANDS = (
    ProfileFamilyCommand(
        selection_attr="model_profiles",
        list_command="list-model-profiles",
        list_help="list available model profiles",
        list_profiles=list_model_profiles,
        add_command="add-model",
        add_help="add selected model profiles to an existing repository",
        required_message="add-model requires at least one --model-profile",
        apply_help="write missing model profile assets",
        force_help="overwrite conflicting model assets",
        asset_group="models",
    ),
    ProfileFamilyCommand(
        selection_attr="tool_profiles",
        list_command="list-tool-profiles",
        list_help="list available tool profiles",
        list_profiles=list_tool_profiles,
        add_command="add-tool",
        add_help="add selected tool profiles to an existing repository",
        required_message="add-tool requires at least one --tool or --tool-profile",
        apply_help="write missing tool assets",
        force_help="overwrite conflicting tool assets",
        asset_group="tools",
        add_selection_alias="--tool",
    ),
    ProfileFamilyCommand(
        selection_attr="memory_profiles",
        list_command="list-memory-profiles",
        list_help="list available memory profiles",
        list_profiles=list_memory_profiles,
        add_command="add-memory",
        add_help="add selected memory profiles to an existing repository",
        required_message="add-memory requires at least one --memory-profile",
        apply_help="write missing memory profile assets",
        force_help="overwrite conflicting memory assets",
        asset_group="memory",
    ),
    ProfileFamilyCommand(
        selection_attr="prompt_profiles",
        list_command="list-prompt-profiles",
        list_help="list available prompt profiles",
        list_profiles=list_prompt_profiles,
        add_command="add-prompts",
        add_help="add selected prompt profiles to an existing repository",
        required_message="add-prompts requires at least one --prompt-profile",
        apply_help="write missing prompt profile assets",
        force_help="overwrite conflicting prompt assets",
        asset_group="prompts",
    ),
    ProfileFamilyCommand(
        selection_attr="safety_profiles",
        list_command="list-safety-profiles",
        list_help="list available safety profiles",
        list_profiles=list_safety_profiles,
        add_command="add-safety",
        add_help="add selected prompt/output safety profiles to an existing repository",
        required_message="add-safety requires at least one --safety-profile",
        apply_help="write missing safety profile assets",
        force_help="overwrite conflicting safety assets",
        asset_group="safety",
    ),
    ProfileFamilyCommand(
        selection_attr="privacy_profiles",
        list_command="list-privacy-profiles",
        list_help="list available privacy profiles",
        list_profiles=list_privacy_profiles,
        add_command="add-privacy",
        add_help="add selected privacy profiles to an existing repository",
        required_message="add-privacy requires at least one --privacy-profile",
        apply_help="write missing privacy profile assets",
        force_help="overwrite conflicting privacy assets",
        asset_group="privacy",
    ),
    ProfileFamilyCommand(
        selection_attr="repomap_profiles",
        list_command="list-repomap-profiles",
        list_help="list available repo map profiles",
        list_profiles=list_repomap_profiles,
        add_command="add-repomap",
        add_help="add selected repo map profiles to an existing repository",
        required_message="add-repomap requires at least one --repomap-profile",
        apply_help="write missing repo map profile assets",
        force_help="overwrite conflicting repo map assets",
        asset_group="repomap",
    ),
    ProfileFamilyCommand(
        selection_attr="sandbox_profiles",
        list_command="list-sandbox-profiles",
        list_help="list available sandbox profiles",
        list_profiles=list_sandbox_profiles,
        add_command="add-sandbox",
        add_help="add selected sandbox profiles to an existing repository",
        required_message="add-sandbox requires at least one --sandbox-profile",
        apply_help="write missing sandbox profile assets",
        force_help="overwrite conflicting sandbox assets",
        asset_group="sandbox",
    ),
    ProfileFamilyCommand(
        selection_attr="secrets_profiles",
        list_command="list-secrets-profiles",
        list_help="list available secrets profiles",
        list_profiles=list_secrets_profiles,
        add_command="add-secrets",
        add_help="add selected secrets profiles to an existing repository",
        required_message="add-secrets requires at least one --secrets-profile",
        apply_help="write missing secrets profile assets",
        force_help="overwrite conflicting secrets assets",
        asset_group="secrets",
    ),
    ProfileFamilyCommand(
        selection_attr="design_profiles",
        list_command="list-design-profiles",
        list_help="list available design profiles",
        list_profiles=list_design_profiles,
        add_command="add-design",
        add_help="add selected design profiles to an existing repository",
        required_message="add-design requires at least one --design-profile",
        apply_help="write missing design profile assets",
        force_help="overwrite conflicting design assets",
        asset_group="design",
    ),
    ProfileFamilyCommand(
        selection_attr="worktree_profiles",
        list_command="list-worktree-profiles",
        list_help="list available worktree profiles",
        list_profiles=list_worktree_profiles,
        add_command="add-worktree",
        add_help="add selected worktree profiles to an existing repository",
        required_message="add-worktree requires at least one --worktree-profile",
        apply_help="write missing worktree profile assets",
        force_help="overwrite conflicting worktree assets",
        asset_group="worktrees",
    ),
    ProfileFamilyCommand(
        selection_attr="public_interest_profiles",
        list_command="list-public-interest-profiles",
        list_help="list available public interest profiles",
        list_profiles=list_public_interest_profiles,
        add_command="add-public-interest",
        add_help="add selected public interest profiles to an existing repository",
        required_message="add-public-interest requires at least one --public-interest-profile",
        apply_help="write missing public interest profile assets",
        force_help="overwrite conflicting public interest assets",
        asset_group="public-interest",
    ),
)

PROFILE_FAMILY_COMMANDS_BY_LIST = {spec.list_command: spec for spec in PROFILE_FAMILY_COMMANDS}
PROFILE_CATALOG_FAMILIES = tuple(profiles.PROFILE_CATALOGS)


def _build_targeted_add_commands() -> dict[str, TargetedAddCommand]:
    commands = {
        "add-skill": TargetedAddCommand("skills", "add-skill requires at least one --skill", ("skills",), ("skills", "metadata")),
        "add-docs": TargetedAddCommand(None, None, (), ("docs", "metadata")),
    }
    for spec in PROFILE_FAMILY_COMMANDS:
        commands[spec.add_command] = TargetedAddCommand(
            spec.selection_attr,
            spec.required_message,
            (spec.selection_attr,),
            (spec.asset_group, "metadata"),
        )
    return commands


TARGETED_ADD_COMMANDS = _build_targeted_add_commands()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-familiar",
        description="Generate a downstream repository with agentic engineering defaults.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-templates", help="list available project templates")
    subparsers.add_parser("list-agent-harnesses", help="list available agent harnesses")
    for spec in PROFILE_FAMILY_COMMANDS:
        subparsers.add_parser(spec.list_command, help=spec.list_help)
    subparsers.add_parser("list-skills", help="list available skills")

    catalog = subparsers.add_parser("catalog", help="catalog available profile families with one-line summaries")
    catalog.add_argument("family", choices=PROFILE_CATALOG_FAMILIES, help="profile family to inspect")
    catalog.add_argument("--format", choices=("text", "json"), default="text")

    describe = subparsers.add_parser("describe", help="describe one profile from an in-code registry")
    describe.add_argument("family", choices=PROFILE_CATALOG_FAMILIES, help="profile family to inspect")
    describe.add_argument("name", help="profile name")
    describe.add_argument("--format", choices=("text", "json"), default="text")

    advise = subparsers.add_parser("advise", help="recommend bootstrap stage, profiles, and memory use for a repository")
    advise.add_argument("--path", required=True, type=Path, help="existing repository path")
    advise.add_argument(
        "--intent",
        action="append",
        dest="intended_work",
        choices=("significant-refactor", "prompt-migration", "production-maintenance", "security-review", "docs-setup"),
        default=None,
        help="intended near-term work; may be passed multiple times",
    )
    advise.add_argument("--format", choices=("text", "json"), default="text")

    resolve = subparsers.add_parser("resolve-conflicts", help="preview safe conflict-resolution suggestions for existing repository bootstrap")
    resolve.add_argument("--path", required=True, type=Path, help="existing repository path")
    resolve.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(resolve)
    _add_asset_group_argument(resolve)
    resolve.add_argument("--format", choices=("text", "json"), default="text")

    check = subparsers.add_parser("check", help="check generated assets against bootstrap metadata")
    check.add_argument("--path", required=True, type=Path, help="generated or bootstrapped repository path")
    check.add_argument("--format", choices=("text", "json"), default="text")

    diff_upstream = subparsers.add_parser("diff-upstream-candidate", help="classify downstream generated asset changes for possible upstream contribution")
    diff_upstream.add_argument("--path", required=True, type=Path, help="generated or bootstrapped repository path")
    diff_upstream.add_argument("--format", choices=("text", "json"), default="text")

    upgrade = subparsers.add_parser("upgrade", help="preview upgrades or apply the safe skills refresh slice")
    upgrade.add_argument("--path", required=True, type=Path, help="generated or bootstrapped repository path")
    _add_asset_group_argument(upgrade)
    upgrade_mode = upgrade.add_mutually_exclusive_group()
    upgrade_mode.add_argument("--preview", action="store_true", help="preview refresh candidates without writing (default)")
    upgrade_mode.add_argument("--apply", action="store_true", help="apply safe refresh candidates; currently skills only")
    upgrade.add_argument("--reference-ref", default=None, help="current Reference Source commit, tag, or version recorded on apply")
    upgrade.add_argument("--allow-dirty", action="store_true", help="allow apply in a dirty Git worktree")
    upgrade.add_argument("--format", choices=("text", "json"), default="text")

    skill_sources = subparsers.add_parser("check-skill-sources", help="compare vendored skills with recorded upstream sources")
    skill_sources.add_argument("--source-file", type=Path, default=Path(".agents/skill-sources.yml"), help="skill source provenance file")
    skill_sources.add_argument("--skills-root", type=Path, default=Path(".agents/skills"), help="vendored skills directory")
    skill_sources.add_argument("--format", choices=("text", "json"), default="text")

    generate = subparsers.add_parser("generate", help="generate a downstream repository")
    generate.add_argument("--name", help="project display name")
    generate.add_argument("--output", type=Path, help="directory to create or populate")
    _add_selection_arguments(generate)
    generate.add_argument("--interactive", action="store_true", help="prompt for generation options with questionary")
    generate.add_argument("--force", action="store_true", help="overwrite generated files")
    generate.add_argument("--dry-run", action="store_true", help="preview generated assets")

    audit = subparsers.add_parser("audit", help="audit an existing repository for bootstrap")
    audit.add_argument("--path", required=True, type=Path, help="existing repository path")
    audit.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(audit)
    _add_asset_group_argument(audit)
    audit.add_argument("--format", choices=("text", "json"), default="text")

    bootstrap = subparsers.add_parser(
        "bootstrap-existing",
        help="add selected repo-familiar defaults to an existing repository",
    )
    bootstrap.add_argument("--path", type=Path, help="existing repository path")
    bootstrap.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(bootstrap)
    _add_asset_group_argument(bootstrap)
    bootstrap.add_argument("--interactive", action="store_true", help="prompt for bootstrap options with questionary")
    bootstrap.add_argument("--apply", action="store_true", help="write missing assets")
    bootstrap.add_argument("--force", action="store_true", help="overwrite conflicting assets")
    bootstrap.add_argument("--format", choices=("text", "json"), default="text")

    add_skill = subparsers.add_parser("add-skill", help="vendor selected skills into an existing repository")
    add_skill.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_skill.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_skill)
    add_skill.add_argument("--apply", action="store_true", help="write missing skill assets")
    add_skill.add_argument("--force", action="store_true", help="overwrite conflicting skill assets")
    add_skill.add_argument("--format", choices=("text", "json"), default="text")

    add_docs = subparsers.add_parser("add-docs", help="add documentation scaffold to an existing repository")
    add_docs.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_docs.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_docs)
    add_docs.add_argument("--apply", action="store_true", help="write missing documentation assets")
    add_docs.add_argument("--force", action="store_true", help="overwrite conflicting documentation assets")
    add_docs.add_argument("--format", choices=("text", "json"), default="text")

    for spec in PROFILE_FAMILY_COMMANDS:
        _add_profile_family_parser(subparsers, spec)

    return parser


def _add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--description", default="Generated with repo-familiar.")
    parser.add_argument("--template", default="basic")
    parser.add_argument("--docs", default="quarto")
    parser.add_argument(
        "--agent-harness",
        action="append",
        dest="agent_harnesses",
        default=None,
        help="agent harness to include; may be passed multiple times",
    )
    parser.add_argument(
        "--model-profile",
        action="append",
        dest="model_profiles",
        default=None,
        help="model profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--tool-profile",
        action="append",
        dest="tool_profiles",
        default=None,
        help="tool profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--memory-profile",
        action="append",
        dest="memory_profiles",
        default=None,
        help="memory profile to include; may be passed multiple times",
    )
    parser.add_argument("--prompt-profile", action="append", dest="prompt_profiles", default=None, help="prompt profile to include; may be passed multiple times")
    parser.add_argument("--safety-profile", action="append", dest="safety_profiles", default=None, help="safety profile to include; may be passed multiple times")
    parser.add_argument("--privacy-profile", action="append", dest="privacy_profiles", default=None, help="privacy profile to include; may be passed multiple times")
    parser.add_argument("--repomap-profile", action="append", dest="repomap_profiles", default=None, help="repo map profile to include; may be passed multiple times")
    parser.add_argument(
        "--sandbox-profile",
        action="append",
        dest="sandbox_profiles",
        default=None,
        help="sandbox profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--secrets-profile",
        action="append",
        dest="secrets_profiles",
        default=None,
        help="secrets profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--design-profile",
        action="append",
        dest="design_profiles",
        default=None,
        help="design profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--worktree-profile",
        action="append",
        dest="worktree_profiles",
        default=None,
        help="worktree profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--public-interest-profile",
        action="append",
        dest="public_interest_profiles",
        default=None,
        help="public interest profile to include; may be passed multiple times",
    )
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        default=None,
        help="skill to vendor; may be passed multiple times",
    )
    parser.add_argument("--reference-type", default="local")
    parser.add_argument("--reference-url", default="local")
    parser.add_argument("--reference-ref", default="unknown")
    parser.add_argument(
        "--generated-at",
        default=None,
        help="override generated_at timestamp; primarily useful for deterministic examples",
    )
    parser.add_argument(
        "--sops-age-recipient",
        action="append",
        dest="sops_age_recipients",
        default=None,
        help="age public recipient for optional SOPS scaffold; may be passed multiple times",
    )


def _add_profile_family_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    spec: ProfileFamilyCommand,
) -> None:
    parser = subparsers.add_parser(spec.add_command, help=spec.add_help)
    parser.add_argument("--path", required=True, type=Path, help="existing repository path")
    parser.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(parser)
    if spec.add_selection_alias:
        parser.add_argument(spec.add_selection_alias, action="append", dest=spec.selection_attr, default=None)
    parser.add_argument("--apply", action="store_true", help=spec.apply_help)
    parser.add_argument("--force", action="store_true", help=spec.force_help)
    parser.add_argument("--format", choices=("text", "json"), default="text")


def _add_asset_group_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--asset-group",
        action="append",
        dest="asset_groups",
        choices=("all", "agent", "config", "design", "docs", "memory", "metadata", "models", "plan", "privacy", "public-interest", "prompts", "repomap", "safety", "sandbox", "secrets", "skills", "tools", "worktrees"),
        default=None,
        help="asset group to audit/apply; may be passed multiple times",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-templates":
        for template in list_templates():
            print(template)
        return 0

    if args.command == "list-agent-harnesses":
        for harness in list_agent_harnesses():
            print(harness)
        return 0

    if args.command in PROFILE_FAMILY_COMMANDS_BY_LIST:
        for profile in PROFILE_FAMILY_COMMANDS_BY_LIST[args.command].list_profiles():
            print(profile)
        return 0

    if args.command == "list-skills":
        for skill in list_skills():
            print(skill)
        return 0

    if args.command == "catalog":
        return _catalog(args)

    if args.command == "describe":
        return _describe(args)

    if args.command == "check":
        return _check(args)

    if args.command == "diff-upstream-candidate":
        return _diff_upstream_candidate(args)

    if args.command == "upgrade":
        return _upgrade(args)

    if args.command == "check-skill-sources":
        return _check_skill_sources(args)

    if args.command == "advise":
        return _advise(args)

    if args.command == "resolve-conflicts":
        return _resolve_conflicts(args)

    if args.command == "audit":
        return _audit(args)

    if args.command == "bootstrap-existing":
        return _bootstrap_existing(args)

    if args.command in TARGETED_ADD_COMMANDS:
        return _targeted_add(args, TARGETED_ADD_COMMANDS[args.command])

    if args.command != "generate":
        parser.print_help()
        return 2

    if args.interactive:
        try:
            options = prompt_generation_options(args)
        except (InteractiveCancelled, InteractiveUnavailable) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    else:
        if not args.name or not args.output:
            print("error: generate requires --name and --output unless --interactive is passed", file=sys.stderr)
            return 1
        options = GenerationOptions(
            name=args.name,
            description=args.description,
            output_dir=args.output,
            template=args.template,
            docs=args.docs,
            agent_harnesses=_tuple_or_default(args.agent_harnesses, ("opencode",)),
            model_profiles=_tuple_or_default(args.model_profiles, ("default-coding",)),
            tool_profiles=_tuple_or_default(args.tool_profiles, ("cq",)),
            memory_profiles=_tuple_or_default(args.memory_profiles, ("memory-local",)),
            prompt_profiles=_tuple_or_default(args.prompt_profiles, ()),
            safety_profiles=_tuple_or_default(args.safety_profiles, ()),
            privacy_profiles=_tuple_or_default(args.privacy_profiles, ()),
            repomap_profiles=_tuple_or_default(args.repomap_profiles, ()),
            sandbox_profiles=_tuple_or_default(args.sandbox_profiles, ()),
            secrets_profiles=_tuple_or_default(args.secrets_profiles, ("dotenv-local", "kvenv-azure-keyvault")),
            design_profiles=_tuple_or_default(args.design_profiles, ()),
            worktree_profiles=_tuple_or_default(args.worktree_profiles, ()),
            public_interest_profiles=_tuple_or_default(args.public_interest_profiles, ()),
            skills=_tuple_or_default(args.skills, ("grill-with-docs",)),
            reference_type=args.reference_type,
            reference_url=args.reference_url,
            reference_ref=args.reference_ref,
            generated_at=args.generated_at,
            sops_age_recipients=_tuple_or_default(args.sops_age_recipients, ()),
            force=args.force,
            dry_run=args.dry_run,
        )
    try:
        generated_assets = generate_project(options)
    except (FileExistsError, NotADirectoryError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if options.dry_run:
        print(f"Would generate {options.name} at {options.output_dir}")
        print(f"Would write {len(generated_assets)} assets:")
        for asset in generated_assets:
            print(f"- {asset.path} ({asset.kind}) from {asset.source}")
    else:
        print(f"Generated {options.name} at {options.output_dir}")
        print(f"Wrote {len(generated_assets)} assets")
    return 0


def _audit(args: argparse.Namespace) -> int:
    try:
        report = audit_existing_repository(_existing_options(args))
    except (FileExistsError, NotADirectoryError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_report_or_json(report, args.format)
    return 0


def _catalog(args: argparse.Namespace) -> int:
    profiles_for_family = profiles.catalog_profile_family(args.family)
    if args.format == "json":
        print(json.dumps({"family": args.family, "profiles": profiles_for_family}, indent=2))
        return 0
    print(f"{args.family} profiles:")
    for profile in profiles_for_family:
        print(f"- {profile['name']}: {profile['summary']}")
    return 0


def _describe(args: argparse.Namespace) -> int:
    try:
        profile = profiles.describe_profile_family(args.family, args.name)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps({"family": args.family, "name": args.name, "profile": profile}, indent=2))
        return 0
    print(f"{args.family} profile: {args.name}")
    _print_nested_mapping(profile)
    return 0


def _advise(args: argparse.Namespace) -> int:
    try:
        report = advise_existing_repository(args.path, _tuple_or_default(getattr(args, "intended_work", None), ()))
    except (NotADirectoryError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_advice_or_json(report, args.format)
    return 0


def _resolve_conflicts(args: argparse.Namespace) -> int:
    try:
        report = audit_existing_repository(_existing_options(args))
        suggestions = _conflict_suggestions(args.path, report.conflicts, _planned_assets_by_path(_existing_options(args)))
    except (FileExistsError, NotADirectoryError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps({"path": str(args.path), "suggestions": suggestions}, indent=2))
        return 0
    print(f"Conflict resolution preview: {args.path}")
    print("No files were changed.")
    for suggestion in suggestions:
        print(f"- {suggestion['path']}: {suggestion['strategy']} ({suggestion['recommendation']})")
        for detail in suggestion.get("details", []):
            print(f"  - {detail}")
    return 0


def _check(args: argparse.Namespace) -> int:
    try:
        report = check_generated_repository(args.path)
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_check_or_json(report, args.format)
    return 1 if report.modified or report.missing else 0


def _diff_upstream_candidate(args: argparse.Namespace) -> int:
    try:
        report = diff_upstream_candidate(args.path, _current_reference_assets(args.path))
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_upstream_diff_or_json(report, args.format)
    return 0


def _upgrade(args: argparse.Namespace) -> int:
    asset_groups = tuple(args.asset_groups or ("all",))
    try:
        current_plan = _current_reference_plan(args.path)
        if args.apply:
            result = apply_upgrade(
                args.path,
                {asset.path: asset for asset in current_plan},
                asset_groups=asset_groups,
                reference_ref=args.reference_ref or _current_reference_ref(),
                allow_dirty=args.allow_dirty,
            )
            report = result.report
        else:
            result = None
            report = preview_upgrade(
                args.path,
                {asset.path: asset.as_generated_asset() for asset in current_plan},
                asset_groups=asset_groups,
            )
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_upgrade_or_json(report, args.format, written_paths=result.written_paths if result else ())
    return 0


def _check_skill_sources(args: argparse.Namespace) -> int:
    try:
        report = check_skill_sources(args.source_file, args.skills_root)
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_skill_source_report_or_json(report, args.format)
    return 1 if report.has_actionable_drift else 0


def _current_reference_assets(path: Path) -> dict[str, GeneratedAsset]:
    return {asset.path: asset.as_generated_asset() for asset in _current_reference_plan(path)}


def _current_reference_plan(path: Path) -> list[PlannedAsset]:
    metadata = load_bootstrap_metadata(path / BOOTSTRAP_METADATA_PATH)
    project_name, project_description = _downstream_render_identity(path, metadata)
    options = GenerationOptions(
        name=project_name,
        description=project_description,
        output_dir=path,
        template=metadata.selected_template,
        docs=metadata.docs,
        agent_harnesses=metadata.selected_options.get("agent_harnesses", ("opencode",)),
        model_profiles=metadata.selected_options.get("model_profiles", ("default-coding",)),
        tool_profiles=metadata.selected_options.get("tool_profiles", ("cq",)),
        memory_profiles=metadata.selected_options.get("memory_profiles", ("memory-local",)),
        prompt_profiles=metadata.selected_options.get("prompt_profiles", ()),
        safety_profiles=metadata.selected_options.get("safety_profiles", ()),
        privacy_profiles=metadata.selected_options.get("privacy_profiles", ()),
        repomap_profiles=metadata.selected_options.get("repomap_profiles", ()),
        sandbox_profiles=metadata.selected_options.get("sandbox_profiles", ()),
        secrets_profiles=metadata.selected_options.get("secrets_profiles", ("dotenv-local", "kvenv-azure-keyvault")),
        design_profiles=metadata.selected_options.get("design_profiles", ()),
        worktree_profiles=metadata.selected_options.get("worktree_profiles", ()),
        public_interest_profiles=metadata.selected_options.get("public_interest_profiles", ()),
        skills=tuple(
            skill
            for skill in metadata.selected_options.get("skills", ("grill-with-docs",))
            if skill in list_skills()
        ),
        reference_type=metadata.reference_type,
        reference_url=metadata.reference_url,
        reference_ref=metadata.reference_ref,
        generated_at=metadata.generated_at,
        sops_age_recipients=metadata.selected_options.get("sops_age_recipients", ()),
        bootstrap_mode=metadata.bootstrap_mode,
        dry_run=True,
    )
    return plan_project(options)


def _current_reference_ref() -> str:
    source_root = Path(__file__).resolve().parents[2]
    if not (source_root / ".git").exists():
        return f"repo-familiar@{__version__}"
    try:
        status = subprocess.run(
            ["git", "-C", str(source_root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True,
        )
        if status.stdout.strip():
            raise ValueError(
                "Reference Source worktree is dirty; commit its changes or pass an explicit --reference-ref"
            )
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError(f"Unable to verify Reference Source provenance: {error}") from error
    return result.stdout.strip() or f"repo-familiar@{__version__}"


def _downstream_render_identity(path: Path, metadata) -> tuple[str, str]:
    fallback = (path.name, "Generated with repo-familiar.")
    readme_asset = next((asset for asset in metadata.generated_assets if asset.path == "README.md"), None)
    readme_path = path / "README.md"
    if not readme_asset or not readme_asset.content_sha256 or not readme_path.is_file() or readme_path.is_symlink():
        return fallback
    content = readme_path.read_text()
    if hashlib.sha256(content.encode()).hexdigest() != readme_asset.content_sha256:
        return fallback
    lines = content.splitlines()
    if not lines or not lines[0].startswith("# "):
        return fallback
    description = next((line for line in lines[1:] if line.strip()), fallback[1])
    return lines[0][2:].strip(), description.strip()


def _bootstrap_existing(args: argparse.Namespace, guidance: TargetedAddGuidance | None = None) -> int:
    if getattr(args, "interactive", False):
        try:
            options, apply = prompt_existing_options(args)
        except (InteractiveCancelled, InteractiveUnavailable) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    else:
        if not args.path:
            print("error: bootstrap-existing requires --path unless --interactive is passed", file=sys.stderr)
            return 1
        options = _existing_options(args)
        apply = args.apply
    try:
        if not apply:
            report = audit_existing_repository(options)
            _print_report_or_json(report, args.format, dry_run=True, guidance=guidance)
            return 0
        result = bootstrap_existing_repository(options)
    except (FileExistsError, NotADirectoryError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(_result_to_dict(result, guidance=guidance), indent=2))
    else:
        print(f"Bootstrapped existing repository at {options.path}")
        print(f"Wrote {len(result.written)} assets")
        for asset in result.written:
            print(f"- {asset.path} ({asset.kind})")
        if result.skipped_conflicts:
            print(f"Skipped {len(result.skipped_conflicts)} conflicting assets")
            for asset in result.skipped_conflicts:
                print(f"- {asset.path} ({asset.kind})")
        _print_targeted_add_guidance(guidance)
    return 0


def _existing_options(args: argparse.Namespace) -> ExistingBootstrapOptions:
    return ExistingBootstrapOptions(
        path=args.path,
        name=args.name,
        description=args.description,
        template=args.template,
        docs=args.docs,
        agent_harnesses=_tuple_or_default(args.agent_harnesses, ("opencode",)),
        model_profiles=_tuple_or_default(args.model_profiles, ("default-coding",)),
        tool_profiles=_tuple_or_default(args.tool_profiles, ("cq",)),
        memory_profiles=_tuple_or_default(args.memory_profiles, ("memory-local",)),
        prompt_profiles=_tuple_or_default(args.prompt_profiles, ()),
        safety_profiles=_tuple_or_default(args.safety_profiles, ()),
        privacy_profiles=_tuple_or_default(args.privacy_profiles, ()),
        repomap_profiles=_tuple_or_default(args.repomap_profiles, ()),
        sandbox_profiles=_tuple_or_default(args.sandbox_profiles, ()),
        secrets_profiles=_tuple_or_default(args.secrets_profiles, ("dotenv-local", "kvenv-azure-keyvault")),
        design_profiles=_tuple_or_default(args.design_profiles, ()),
        worktree_profiles=_tuple_or_default(args.worktree_profiles, ()),
        public_interest_profiles=_tuple_or_default(args.public_interest_profiles, ()),
        skills=_tuple_or_default(args.skills, ("grill-with-docs",)),
        reference_type=args.reference_type,
        reference_url=args.reference_url,
        reference_ref=args.reference_ref,
        generated_at=args.generated_at,
        sops_age_recipients=_tuple_or_default(args.sops_age_recipients, ()),
        asset_groups=_tuple_or_default(getattr(args, "asset_groups", None), ("all",)),
        force=getattr(args, "force", False),
    )


def _print_audit_report(report) -> None:
    print(f"Audit: {report.path}")
    print(f"Comparison basis: {report.comparison_basis}")
    print(f"Asset groups: {', '.join(report.asset_groups)}")
    print("Selected options:")
    for key, value in report.selected_options.items():
        rendered = ", ".join(value) if isinstance(value, tuple) else value
        print(f"- {key}: {rendered or '(none)'}")
    print(
        "Summary: "
        f"{len(report.missing)} missing, "
        f"{len(report.present)} present, "
        f"{len(report.conflicts)} conflicts"
    )
    _print_assets("Missing", report.missing)
    _print_assets("Present", report.present)
    _print_assets("Conflicts", report.conflicts)
    if report.conflicts:
        print("Conflicts are skipped unless --force is passed.")


def _print_assets(label: str, assets) -> None:
    print(f"{label}: {len(assets)}")
    for asset in assets:
        print(f"- {asset.path} ({asset.kind})")


def _print_report_or_json(report, output_format: str, *, dry_run: bool = False, guidance: TargetedAddGuidance | None = None) -> None:
    if output_format == "json":
        payload = _report_to_dict(report)
        if dry_run:
            payload["dry_run"] = True
        if guidance:
            payload["targeted_add"] = _guidance_to_dict(guidance)
        print(json.dumps(payload, indent=2))
        return
    _print_audit_report(report)
    if dry_run:
        print("Dry run only. Pass --apply to write missing assets.")
    _print_targeted_add_guidance(guidance, dry_run=dry_run)


def _report_to_dict(report) -> dict:
    return {
        "path": str(report.path),
        "comparison_basis": report.comparison_basis,
        "asset_groups": list(report.asset_groups),
        "selected_options": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in report.selected_options.items()
        },
        "summary": {
            "missing": len(report.missing),
            "present": len(report.present),
            "conflicts": len(report.conflicts),
        },
        "missing": [_asset_to_dict(asset) for asset in report.missing],
        "present": [_asset_to_dict(asset) for asset in report.present],
        "conflicts": [_asset_to_dict(asset) for asset in report.conflicts],
    }


def _result_to_dict(result, guidance: TargetedAddGuidance | None = None) -> dict:
    payload = {
        "report": _report_to_dict(result.report),
        "summary": {
            "written": len(result.written),
            "skipped_conflicts": len(result.skipped_conflicts),
        },
        "written": [_asset_to_dict(asset) for asset in result.written],
        "skipped_conflicts": [_asset_to_dict(asset) for asset in result.skipped_conflicts],
    }
    if guidance:
        payload["targeted_add"] = _guidance_to_dict(guidance)
    return payload


def _asset_to_dict(asset) -> dict[str, str]:
    payload = {"path": asset.path, "kind": asset.kind, "source": asset.source}
    if asset.content_sha256:
        payload["content_sha256"] = asset.content_sha256
    return payload


def _print_check_or_json(report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_check_report_to_dict(report), indent=2))
        return
    print(f"Check: {report.path}")
    print(
        "Summary: "
        f"{len(report.ok)} ok, "
        f"{len(report.modified)} modified, "
        f"{len(report.missing)} missing, "
        f"{len(report.unchecked)} unchecked"
    )
    _print_checked_assets("Modified", report.modified)
    _print_checked_assets("Missing", report.missing)
    _print_checked_assets("Unchecked", report.unchecked)


def _print_checked_assets(label: str, checked_assets) -> None:
    print(f"{label}: {len(checked_assets)}")
    for checked in checked_assets:
        print(f"- {checked.asset.path} ({checked.asset.kind})")


def _check_report_to_dict(report) -> dict:
    return {
        "path": str(report.path),
        "summary": {
            "ok": len(report.ok),
            "modified": len(report.modified),
            "missing": len(report.missing),
            "unchecked": len(report.unchecked),
        },
        "ok": [_checked_asset_to_dict(checked) for checked in report.ok],
        "modified": [_checked_asset_to_dict(checked) for checked in report.modified],
        "missing": [_checked_asset_to_dict(checked) for checked in report.missing],
        "unchecked": [_checked_asset_to_dict(checked) for checked in report.unchecked],
    }


def _checked_asset_to_dict(checked) -> dict:
    payload = _asset_to_dict(checked.asset)
    payload["status"] = checked.status
    if checked.current_sha256:
        payload["current_sha256"] = checked.current_sha256
    return payload


def _print_upstream_diff_or_json(report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_upstream_diff_to_dict(report), indent=2))
        return
    print(f"Upstream candidate diff: {report.path}")
    print(
        "Summary: "
        f"{len(report.unchanged)} unchanged, "
        f"{len(report.modified)} modified, "
        f"{len(report.missing)} missing, "
        f"{len(report.unchecked)} unchecked"
    )
    _print_upstream_diff_items("Modified", report.modified)
    _print_upstream_diff_items("Missing", report.missing)
    _print_upstream_diff_items("Unchecked", report.unchecked)


def _print_upstream_diff_items(label: str, items) -> None:
    print(f"{label}: {len(items)}")
    for item in items:
        print(f"- {item.asset.path} ({item.asset.kind}) {item.recommendation}; strategy={item.strategy}")


def _upstream_diff_to_dict(report) -> dict:
    return {
        "path": str(report.path),
        "summary": {
            "unchanged": len(report.unchanged),
            "modified": len(report.modified),
            "missing": len(report.missing),
            "unchecked": len(report.unchecked),
        },
        "unchanged": [_upstream_diff_item_to_dict(item) for item in report.unchanged],
        "modified": [_upstream_diff_item_to_dict(item) for item in report.modified],
        "missing": [_upstream_diff_item_to_dict(item) for item in report.missing],
        "unchecked": [_upstream_diff_item_to_dict(item) for item in report.unchecked],
    }


def _upstream_diff_item_to_dict(item) -> dict:
    payload = _asset_to_dict(item.asset)
    payload["status"] = item.status
    payload["recommendation"] = item.recommendation
    payload["current_reference_status"] = item.current_reference_status
    payload["strategy"] = item.strategy
    if item.current_sha256:
        payload["current_sha256"] = item.current_sha256
    if item.current_reference_sha256:
        payload["current_reference_sha256"] = item.current_reference_sha256
    return payload


def _print_upgrade_or_json(report, output_format: str, *, written_paths: tuple[str, ...] = ()) -> None:
    if output_format == "json":
        payload = _upgrade_to_dict(report)
        payload["written_paths"] = list(written_paths)
        print(json.dumps(payload, indent=2))
        return
    print(f"Upgrade preview: {report.path}")
    print(f"Asset groups: {', '.join(report.asset_groups)}")
    print(
        "Summary: "
        f"{len(report.safe_to_auto_apply)} safe_to_auto_apply, "
        f"{len(report.needs_user_review)} needs_user_review, "
        f"{len(report.blocked)} blocked, "
        f"{len(report.unavailable)} unavailable"
    )
    for note in report.notes:
        print(f"- {note}")
    if written_paths:
        print(f"Applied: {len(written_paths)} assets")
        for path in written_paths:
            print(f"- {path}")
    _print_upstream_diff_items("Safe to auto apply", report.safe_to_auto_apply)
    _print_upstream_diff_items("Needs user review", report.needs_user_review)
    _print_upstream_diff_items("Blocked", report.blocked)


def _upgrade_to_dict(report) -> dict:
    return {
        "path": str(report.path),
        "asset_groups": list(report.asset_groups),
        "summary": {
            "safe_to_auto_apply": len(report.safe_to_auto_apply),
            "needs_user_review": len(report.needs_user_review),
            "blocked": len(report.blocked),
            "unavailable": len(report.unavailable),
        },
        "safe_to_auto_apply": [_upstream_diff_item_to_dict(item) for item in report.safe_to_auto_apply],
        "needs_user_review": [_upstream_diff_item_to_dict(item) for item in report.needs_user_review],
        "blocked": [_upstream_diff_item_to_dict(item) for item in report.blocked],
        "unavailable": [_upstream_diff_item_to_dict(item) for item in report.unavailable],
        "notes": list(report.notes),
    }


def _print_skill_source_report_or_json(report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_skill_source_report_to_dict(report), indent=2))
        return
    print(f"Skill source check: {report.source_file}")
    summary = _skill_source_summary(report)
    print(
        "Summary: "
        f"{summary.get('matches-upstream', 0)} matches-upstream, "
        f"{summary.get('upstream-newer', 0)} upstream-newer, "
        f"{summary.get('content-differs', 0)} content-differs, "
        f"{summary.get('local-source', 0)} local-source, "
        f"{summary.get('unsupported-url', 0)} unsupported-url, "
        f"{summary.get('fetch-error', 0)} fetch-error, "
        f"{summary.get('local-missing', 0)} local-missing"
    )
    for check in report.checks:
        if check.status in {"upstream-newer", "fetch-error", "local-missing"} or check.missing_support_files:
            print(f"- {check.name}: {check.status} ({check.recommendation})")
            if check.upstream_updated_at:
                print(f"  upstream_updated_at: {check.upstream_updated_at}")
            if check.local_updated_at:
                print(f"  local_updated_at: {check.local_updated_at}")
            for missing_file in check.missing_support_files:
                print(f"  missing support file: {missing_file}")
            if check.error:
                print(f"  error: {check.error}")


def _skill_source_report_to_dict(report) -> dict:
    return {
        "source_file": str(report.source_file),
        "skills_root": str(report.skills_root),
        "summary": _skill_source_summary(report),
        "has_actionable_drift": report.has_actionable_drift,
        "checks": [check.__dict__ for check in report.checks],
    }


def _skill_source_summary(report) -> dict[str, int]:
    summary: dict[str, int] = {}
    for check in report.checks:
        summary[check.status] = summary.get(check.status, 0) + 1
    return summary


def _print_advice_or_json(report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_advice_to_dict(report), indent=2))
        return
    print(f"Advice: {report.path}")
    if report.intended_work:
        print(f"Intended work: {', '.join(report.intended_work)}")
    print(f"Recommended stage: {report.recommended_stage}")
    print("Recommended asset groups:")
    for group in report.recommended_asset_groups:
        print(f"- {group}")
    print("Recommended profiles:")
    _print_named_values("model", report.recommended_model_profiles)
    _print_named_values("tool", report.recommended_tool_profiles)
    _print_named_values("memory", report.recommended_memory_profiles)
    _print_named_values("prompt", report.recommended_prompt_profiles)
    _print_named_values("safety", report.recommended_safety_profiles)
    _print_named_values("privacy", report.recommended_privacy_profiles)
    _print_named_values("repomap", report.recommended_repomap_profiles)
    _print_named_values("sandbox", report.recommended_sandbox_profiles)
    _print_named_values("secrets", report.recommended_secrets_profiles)
    _print_named_values("design", report.recommended_design_profiles)
    _print_named_values("worktree", report.recommended_worktree_profiles)
    _print_named_values("public_interest", report.recommended_public_interest_profiles)
    _print_named_values("skills", report.recommended_skills)
    print("Rationale:")
    for item in report.rationale:
        print(f"- {item}")
    print("Memory guidance:")
    for item in report.memory_guidance:
        print(f"- {item}")
    print("Suggested next commands:")
    for command in report.next_commands:
        print(f"- {command}")


def _print_named_values(label: str, values: tuple[str, ...]) -> None:
    rendered = ", ".join(values) if values else "(none)"
    print(f"- {label}: {rendered}")


def _print_nested_mapping(mapping: dict, *, indent: str = "") -> None:
    for key, value in mapping.items():
        if isinstance(value, dict):
            print(f"{indent}{key}:")
            _print_nested_mapping(value, indent=f"{indent}  ")
            continue
        if isinstance(value, list):
            print(f"{indent}{key}:")
            for item in value:
                print(f"{indent}  - {item}")
            continue
        print(f"{indent}{key}: {value}")


def _advice_to_dict(report) -> dict:
    return {
        "path": str(report.path),
        "intended_work": list(report.intended_work),
        "signals": report.signals.__dict__,
        "recommended_stage": report.recommended_stage,
        "recommended_asset_groups": list(report.recommended_asset_groups),
        "recommended_profiles": {
            "model_profiles": list(report.recommended_model_profiles),
            "tool_profiles": list(report.recommended_tool_profiles),
            "memory_profiles": list(report.recommended_memory_profiles),
            "prompt_profiles": list(report.recommended_prompt_profiles),
            "safety_profiles": list(report.recommended_safety_profiles),
            "privacy_profiles": list(report.recommended_privacy_profiles),
            "repomap_profiles": list(report.recommended_repomap_profiles),
            "sandbox_profiles": list(report.recommended_sandbox_profiles),
            "secrets_profiles": list(report.recommended_secrets_profiles),
            "design_profiles": list(report.recommended_design_profiles),
            "worktree_profiles": list(report.recommended_worktree_profiles),
            "public_interest_profiles": list(report.recommended_public_interest_profiles),
            "skills": list(report.recommended_skills),
        },
        "rationale": list(report.rationale),
        "memory_guidance": list(report.memory_guidance),
        "next_commands": list(report.next_commands),
    }


def _planned_assets_by_path(options: ExistingBootstrapOptions) -> dict[str, PlannedAsset]:
    generation_options = GenerationOptions(
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
        public_interest_profiles=options.public_interest_profiles,
        skills=options.skills,
        reference_type=options.reference_type,
        reference_url=options.reference_url,
        reference_ref=options.reference_ref,
        generated_at=options.generated_at,
        sops_age_recipients=options.sops_age_recipients,
        bootstrap_mode="existing_repository",
        dry_run=True,
    )
    return {asset.path: asset for asset in plan_project(generation_options)}


def _conflict_suggestions(path: Path, conflicts, planned_by_path: dict[str, PlannedAsset]) -> list[dict]:
    suggestions = []
    for conflict in conflicts:
        planned = planned_by_path.get(conflict.path)
        existing_path = path / conflict.path
        if not planned or not existing_path.is_file():
            suggestions.append({"path": conflict.path, "strategy": "manual-review", "recommendation": "review manually", "details": []})
            continue
        existing = existing_path.read_text()
        generated = planned.content
        if conflict.path == ".gitignore":
            additions = _missing_gitignore_lines(existing, generated)
            suggestions.append({"path": conflict.path, "strategy": "line-union", "recommendation": "append missing ignore patterns", "details": additions})
        elif conflict.path == "AGENTS.md":
            additions = _missing_markdown_headings(existing, generated)
            suggestions.append({"path": conflict.path, "strategy": "markdown-heading-merge", "recommendation": "append missing generated sections", "details": additions})
        elif conflict.path in ("README.md", "plan.md") or conflict.path.startswith(".agents/"):
            suggestions.append({"path": conflict.path, "strategy": "preview-only", "recommendation": "preserve existing file and review generated version manually", "details": []})
        else:
            suggestions.append({"path": conflict.path, "strategy": "manual-review", "recommendation": "review manually", "details": []})
    return suggestions


def _missing_gitignore_lines(existing: str, generated: str) -> list[str]:
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip() and not line.strip().startswith("#")}
    return [line for line in generated.splitlines() if line.strip() and not line.strip().startswith("#") and line.strip() not in existing_lines]


def _missing_markdown_headings(existing: str, generated: str) -> list[str]:
    existing_headings = {line.strip() for line in existing.splitlines() if line.startswith("#")}
    return [line.strip() for line in generated.splitlines() if line.startswith("#") and line.strip() not in existing_headings]


def _tuple_or_default(value, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    return tuple(value)


def _targeted_add(args: argparse.Namespace, descriptor: TargetedAddCommand) -> int:
    if descriptor.required_attr and not getattr(args, descriptor.required_attr):
        print(f"error: {descriptor.required_message}", file=sys.stderr)
        return 1
    _keep_only_selection_attrs(args, descriptor.keep_attrs)
    args.asset_groups = descriptor.asset_groups
    guidance = _build_targeted_add_guidance(_existing_options(args), args.command)
    return _bootstrap_existing(args, guidance=guidance)


def _keep_only_selection_attrs(args: argparse.Namespace, keep_attrs: tuple[str, ...]) -> None:
    selected = {
        attr: getattr(args, attr, None) or []
        for attr in SELECTION_ATTRS
    }
    for attr in SELECTION_ATTRS:
        setattr(args, attr, selected[attr] if attr in keep_attrs else [])


def _print_targeted_add_guidance(guidance: TargetedAddGuidance | None, *, dry_run: bool = False) -> None:
    if not guidance:
        return
    if dry_run:
        print("Targeted add preview:")
        print("Generated assets in scope:")
        for asset in guidance.generated_assets:
            print(f"- {asset.path} ({asset.kind})")
    if guidance.warnings:
        print("Warnings:")
        for warning in guidance.warnings:
            print(f"- {warning}")
    if guidance.follow_up:
        print("Follow-up verification:")
        for step in guidance.follow_up:
            print(f"- {step}")


def _guidance_to_dict(guidance: TargetedAddGuidance) -> dict:
    return {
        "generated_assets": [_asset_to_dict(asset) for asset in guidance.generated_assets],
        "warnings": list(guidance.warnings),
        "follow_up": list(guidance.follow_up),
    }


def _build_targeted_add_guidance(options: ExistingBootstrapOptions, command_name: str) -> TargetedAddGuidance:
    planned_assets = tuple(
        asset.as_generated_asset()
        for path, asset in sorted(_planned_assets_by_path(options).items())
        if asset_in_groups(path, options.asset_groups)
    )
    warnings = _targeted_add_warnings(options, command_name)
    follow_up = [f"After applying, run `repo-familiar check --path {options.path}`."]
    dependency_preview = _targeted_add_dependency_preview(options)
    if dependency_preview:
        follow_up.append(f"Preview related generated config with `{dependency_preview}` before expecting harness-specific behavior.")
    return TargetedAddGuidance(
        generated_assets=planned_assets,
        warnings=tuple(warnings),
        follow_up=tuple(follow_up),
    )


def _targeted_add_warnings(options: ExistingBootstrapOptions, command_name: str) -> list[str]:
    if command_name != "add-tool":
        return []
    recorded_harnesses = _recorded_agent_harnesses(options.path)
    warnings: list[str] = []
    for name in options.tool_profiles:
        profile = profiles.TOOL_PROFILES[name]
        generated_assets = tuple(profile.get("generated_assets", ()))
        omitted_assets = tuple(path for path in generated_assets if not asset_in_groups(path, options.asset_groups))
        if omitted_assets:
            warnings.append(
                f"`{name}` also affects {_render_backticked_paths(omitted_assets)}, but `{command_name}` only updates {_render_backticked_values(options.asset_groups)}; no change to {_render_backticked_paths(omitted_assets)} will happen in this run."
            )
        required_harnesses = tuple(profile.get("requires_agent_harnesses", ()))
        missing_harnesses = tuple(harness for harness in required_harnesses if harness not in recorded_harnesses)
        if missing_harnesses:
            warnings.append(
                f"This repository does not currently record the {_render_backticked_values(missing_harnesses)} harness in bootstrap metadata, so `{name}` remains guidance-only until that harness is selected."
            )
    return warnings


def _targeted_add_dependency_preview(options: ExistingBootstrapOptions) -> str | None:
    if not options.tool_profiles:
        return None
    dependent_profiles: list[str] = []
    required_harnesses: list[str] = []
    dependent_asset_groups: list[str] = []
    for name in options.tool_profiles:
        profile = profiles.TOOL_PROFILES[name]
        generated_assets = tuple(profile.get("generated_assets", ()))
        omitted_assets = [path for path in generated_assets if not asset_in_groups(path, options.asset_groups)]
        if not omitted_assets:
            continue
        dependent_profiles.append(name)
        required_harnesses.extend(profile.get("requires_agent_harnesses", ()))
        for path in omitted_assets:
            dependent_asset_groups.extend(_asset_groups_for_path(path))
    if not dependent_profiles:
        return None
    parts = ["repo-familiar", "audit", "--path", str(options.path)]
    for harness in dict.fromkeys(required_harnesses):
        parts.extend(["--agent-harness", harness])
    for profile_name in dict.fromkeys(dependent_profiles):
        parts.extend(["--tool-profile", profile_name])
    for asset_group in dict.fromkeys([*dependent_asset_groups, "metadata"]):
        parts.extend(["--asset-group", asset_group])
    return " ".join(parts)


def _asset_groups_for_path(path: str) -> tuple[str, ...]:
    groups = (
        "agent",
        "config",
        "design",
        "docs",
        "memory",
        "metadata",
        "models",
        "plan",
        "privacy",
        "public-interest",
        "prompts",
        "repomap",
        "safety",
        "sandbox",
        "secrets",
        "skills",
        "tools",
        "worktrees",
    )
    return tuple(group for group in groups if asset_in_groups(path, (group,)))


def _recorded_agent_harnesses(path: Path) -> tuple[str, ...]:
    bootstrap_path = path / BOOTSTRAP_METADATA_PATH
    if not bootstrap_path.exists():
        return ()
    return load_bootstrap_metadata(bootstrap_path).selected_options.get("agent_harnesses", ())


def _render_backticked_paths(paths: tuple[str, ...]) -> str:
    return _render_backticked_values(paths)


def _render_backticked_values(values: tuple[str, ...]) -> str:
    if len(values) == 1:
        return f"`{values[0]}`"
    return ", ".join(f"`{value}`" for value in values)
