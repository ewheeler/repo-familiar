from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys

from .generator import (
    ExistingBootstrapOptions,
    GenerationOptions,
    advise_existing_repository,
    audit_existing_repository,
    bootstrap_existing_repository,
    check_generated_repository,
    generate_project,
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
from .asset_plan import BOOTSTRAP_METADATA_PATH
from .interactive import (
    InteractiveCancelled,
    InteractiveUnavailable,
    prompt_existing_options,
    prompt_generation_options,
)
from .metadata import load_bootstrap_metadata
from .upstream import diff_upstream_candidate
from .upgrade import preview_upgrade


@dataclass(frozen=True)
class TargetedAddCommand:
    required_attr: str | None
    required_message: str | None
    keep_attrs: tuple[str, ...]
    asset_groups: tuple[str, ...]


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


TARGETED_ADD_COMMANDS = {
    "add-skill": TargetedAddCommand("skills", "add-skill requires at least one --skill", ("skills",), ("skills", "metadata")),
    "add-tool": TargetedAddCommand("tool_profiles", "add-tool requires at least one --tool or --tool-profile", ("tool_profiles",), ("tools", "metadata")),
    "add-model": TargetedAddCommand("model_profiles", "add-model requires at least one --model-profile", ("model_profiles",), ("models", "metadata")),
    "add-docs": TargetedAddCommand(None, None, (), ("docs", "metadata")),
    "add-memory": TargetedAddCommand("memory_profiles", "add-memory requires at least one --memory-profile", ("memory_profiles",), ("memory", "metadata")),
    "add-prompts": TargetedAddCommand("prompt_profiles", "add-prompts requires at least one --prompt-profile", ("prompt_profiles",), ("prompts", "metadata")),
    "add-safety": TargetedAddCommand("safety_profiles", "add-safety requires at least one --safety-profile", ("safety_profiles",), ("safety", "metadata")),
    "add-privacy": TargetedAddCommand("privacy_profiles", "add-privacy requires at least one --privacy-profile", ("privacy_profiles",), ("privacy", "metadata")),
    "add-repomap": TargetedAddCommand("repomap_profiles", "add-repomap requires at least one --repomap-profile", ("repomap_profiles",), ("repomap", "metadata")),
    "add-sandbox": TargetedAddCommand("sandbox_profiles", "add-sandbox requires at least one --sandbox-profile", ("sandbox_profiles",), ("sandbox", "metadata")),
    "add-secrets": TargetedAddCommand("secrets_profiles", "add-secrets requires at least one --secrets-profile", ("secrets_profiles",), ("secrets", "metadata")),
    "add-design": TargetedAddCommand("design_profiles", "add-design requires at least one --design-profile", ("design_profiles",), ("design", "metadata")),
    "add-worktree": TargetedAddCommand("worktree_profiles", "add-worktree requires at least one --worktree-profile", ("worktree_profiles",), ("worktrees", "metadata")),
    "add-public-interest": TargetedAddCommand("public_interest_profiles", "add-public-interest requires at least one --public-interest-profile", ("public_interest_profiles",), ("public-interest", "metadata")),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-familiar",
        description="Generate a downstream repository with agentic engineering defaults.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-templates", help="list available project templates")
    subparsers.add_parser("list-model-profiles", help="list available model profiles")
    subparsers.add_parser("list-tool-profiles", help="list available tool profiles")
    subparsers.add_parser("list-memory-profiles", help="list available memory profiles")
    subparsers.add_parser("list-prompt-profiles", help="list available prompt profiles")
    subparsers.add_parser("list-safety-profiles", help="list available safety profiles")
    subparsers.add_parser("list-privacy-profiles", help="list available privacy profiles")
    subparsers.add_parser("list-repomap-profiles", help="list available repo map profiles")
    subparsers.add_parser("list-sandbox-profiles", help="list available sandbox profiles")
    subparsers.add_parser("list-secrets-profiles", help="list available secrets profiles")
    subparsers.add_parser("list-design-profiles", help="list available design profiles")
    subparsers.add_parser("list-worktree-profiles", help="list available worktree profiles")
    subparsers.add_parser("list-public-interest-profiles", help="list available public interest profiles")
    subparsers.add_parser("list-skills", help="list available skills")

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

    upgrade = subparsers.add_parser("upgrade", help="preview a read-only generated asset upgrade report")
    upgrade.add_argument("--path", required=True, type=Path, help="generated or bootstrapped repository path")
    upgrade.add_argument("--format", choices=("text", "json"), default="text")

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

    add_tool = subparsers.add_parser("add-tool", help="add selected tool profiles to an existing repository")
    add_tool.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_tool.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_tool)
    add_tool.add_argument("--tool", action="append", dest="tool_profiles", default=None)
    add_tool.add_argument("--apply", action="store_true", help="write missing tool assets")
    add_tool.add_argument("--force", action="store_true", help="overwrite conflicting tool assets")
    add_tool.add_argument("--format", choices=("text", "json"), default="text")

    add_model = subparsers.add_parser("add-model", help="add selected model profiles to an existing repository")
    add_model.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_model.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_model)
    add_model.add_argument("--apply", action="store_true", help="write missing model profile assets")
    add_model.add_argument("--force", action="store_true", help="overwrite conflicting model assets")
    add_model.add_argument("--format", choices=("text", "json"), default="text")

    add_docs = subparsers.add_parser("add-docs", help="add documentation scaffold to an existing repository")
    add_docs.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_docs.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_docs)
    add_docs.add_argument("--apply", action="store_true", help="write missing documentation assets")
    add_docs.add_argument("--force", action="store_true", help="overwrite conflicting documentation assets")
    add_docs.add_argument("--format", choices=("text", "json"), default="text")

    add_memory = subparsers.add_parser("add-memory", help="add selected memory profiles to an existing repository")
    add_memory.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_memory.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_memory)
    add_memory.add_argument("--apply", action="store_true", help="write missing memory profile assets")
    add_memory.add_argument("--force", action="store_true", help="overwrite conflicting memory assets")
    add_memory.add_argument("--format", choices=("text", "json"), default="text")

    add_prompts = subparsers.add_parser("add-prompts", help="add selected prompt profiles to an existing repository")
    add_prompts.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_prompts.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_prompts)
    add_prompts.add_argument("--apply", action="store_true", help="write missing prompt profile assets")
    add_prompts.add_argument("--force", action="store_true", help="overwrite conflicting prompt assets")
    add_prompts.add_argument("--format", choices=("text", "json"), default="text")

    add_safety = subparsers.add_parser("add-safety", help="add selected prompt/output safety profiles to an existing repository")
    add_safety.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_safety.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_safety)
    add_safety.add_argument("--apply", action="store_true", help="write missing safety profile assets")
    add_safety.add_argument("--force", action="store_true", help="overwrite conflicting safety assets")
    add_safety.add_argument("--format", choices=("text", "json"), default="text")

    add_privacy = subparsers.add_parser("add-privacy", help="add selected privacy profiles to an existing repository")
    add_privacy.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_privacy.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_privacy)
    add_privacy.add_argument("--apply", action="store_true", help="write missing privacy profile assets")
    add_privacy.add_argument("--force", action="store_true", help="overwrite conflicting privacy assets")
    add_privacy.add_argument("--format", choices=("text", "json"), default="text")

    add_repomap = subparsers.add_parser("add-repomap", help="add selected repo map profiles to an existing repository")
    add_repomap.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_repomap.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_repomap)
    add_repomap.add_argument("--apply", action="store_true", help="write missing repo map profile assets")
    add_repomap.add_argument("--force", action="store_true", help="overwrite conflicting repo map assets")
    add_repomap.add_argument("--format", choices=("text", "json"), default="text")

    add_sandbox = subparsers.add_parser("add-sandbox", help="add selected sandbox profiles to an existing repository")
    add_sandbox.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_sandbox.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_sandbox)
    add_sandbox.add_argument("--apply", action="store_true", help="write missing sandbox profile assets")
    add_sandbox.add_argument("--force", action="store_true", help="overwrite conflicting sandbox assets")
    add_sandbox.add_argument("--format", choices=("text", "json"), default="text")

    add_secrets = subparsers.add_parser("add-secrets", help="add selected secrets profiles to an existing repository")
    add_secrets.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_secrets.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_secrets)
    add_secrets.add_argument("--apply", action="store_true", help="write missing secrets profile assets")
    add_secrets.add_argument("--force", action="store_true", help="overwrite conflicting secrets assets")
    add_secrets.add_argument("--format", choices=("text", "json"), default="text")

    add_design = subparsers.add_parser("add-design", help="add selected design profiles to an existing repository")
    add_design.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_design.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_design)
    add_design.add_argument("--apply", action="store_true", help="write missing design profile assets")
    add_design.add_argument("--force", action="store_true", help="overwrite conflicting design assets")
    add_design.add_argument("--format", choices=("text", "json"), default="text")

    add_worktree = subparsers.add_parser("add-worktree", help="add selected worktree profiles to an existing repository")
    add_worktree.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_worktree.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_worktree)
    add_worktree.add_argument("--apply", action="store_true", help="write missing worktree profile assets")
    add_worktree.add_argument("--force", action="store_true", help="overwrite conflicting worktree assets")
    add_worktree.add_argument("--format", choices=("text", "json"), default="text")

    add_public_interest = subparsers.add_parser("add-public-interest", help="add selected public interest profiles to an existing repository")
    add_public_interest.add_argument("--path", required=True, type=Path, help="existing repository path")
    add_public_interest.add_argument("--name", default=None, help="project display name; defaults to directory name")
    _add_selection_arguments(add_public_interest)
    add_public_interest.add_argument("--apply", action="store_true", help="write missing public interest profile assets")
    add_public_interest.add_argument("--force", action="store_true", help="overwrite conflicting public interest assets")
    add_public_interest.add_argument("--format", choices=("text", "json"), default="text")

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

    if args.command == "list-model-profiles":
        for profile in list_model_profiles():
            print(profile)
        return 0

    if args.command == "list-tool-profiles":
        for profile in list_tool_profiles():
            print(profile)
        return 0

    if args.command == "list-memory-profiles":
        for profile in list_memory_profiles():
            print(profile)
        return 0

    if args.command == "list-prompt-profiles":
        for profile in list_prompt_profiles():
            print(profile)
        return 0

    if args.command == "list-safety-profiles":
        for profile in list_safety_profiles():
            print(profile)
        return 0

    if args.command == "list-privacy-profiles":
        for profile in list_privacy_profiles():
            print(profile)
        return 0

    if args.command == "list-repomap-profiles":
        for profile in list_repomap_profiles():
            print(profile)
        return 0

    if args.command == "list-sandbox-profiles":
        for profile in list_sandbox_profiles():
            print(profile)
        return 0

    if args.command == "list-secrets-profiles":
        for profile in list_secrets_profiles():
            print(profile)
        return 0

    if args.command == "list-design-profiles":
        for profile in list_design_profiles():
            print(profile)
        return 0

    if args.command == "list-worktree-profiles":
        for profile in list_worktree_profiles():
            print(profile)
        return 0

    if args.command == "list-public-interest-profiles":
        for profile in list_public_interest_profiles():
            print(profile)
        return 0

    if args.command == "list-skills":
        for skill in list_skills():
            print(skill)
        return 0

    if args.command == "check":
        return _check(args)

    if args.command == "diff-upstream-candidate":
        return _diff_upstream_candidate(args)

    if args.command == "upgrade":
        return _upgrade(args)

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
    try:
        report = preview_upgrade(args.path, _current_reference_assets(args.path))
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_upgrade_or_json(report, args.format)
    return 0


def _current_reference_assets(path: Path) -> dict[str, object]:
    metadata = load_bootstrap_metadata(path / BOOTSTRAP_METADATA_PATH)
    options = GenerationOptions(
        name=path.name,
        description="Generated with repo-familiar.",
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
        skills=metadata.selected_options.get("skills", ("grill-with-docs",)),
        reference_type=metadata.reference_type,
        reference_url=metadata.reference_url,
        reference_ref=metadata.reference_ref,
        generated_at=metadata.generated_at,
        sops_age_recipients=metadata.selected_options.get("sops_age_recipients", ()),
        bootstrap_mode=metadata.bootstrap_mode,
        dry_run=True,
    )
    return {asset.path: asset.as_generated_asset() for asset in plan_project(options)}


def _bootstrap_existing(args: argparse.Namespace) -> int:
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
            _print_report_or_json(report, args.format, dry_run=True)
            return 0
        result = bootstrap_existing_repository(options)
    except (FileExistsError, NotADirectoryError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(_result_to_dict(result), indent=2))
    else:
        print(f"Bootstrapped existing repository at {options.path}")
        print(f"Wrote {len(result.written)} assets")
        for asset in result.written:
            print(f"- {asset.path} ({asset.kind})")
        if result.skipped_conflicts:
            print(f"Skipped {len(result.skipped_conflicts)} conflicting assets")
            for asset in result.skipped_conflicts:
                print(f"- {asset.path} ({asset.kind})")
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


def _print_report_or_json(report, output_format: str, *, dry_run: bool = False) -> None:
    if output_format == "json":
        payload = _report_to_dict(report)
        if dry_run:
            payload["dry_run"] = True
        print(json.dumps(payload, indent=2))
        return
    _print_audit_report(report)
    if dry_run:
        print("Dry run only. Pass --apply to write missing assets.")


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


def _result_to_dict(result) -> dict:
    return {
        "report": _report_to_dict(result.report),
        "summary": {
            "written": len(result.written),
            "skipped_conflicts": len(result.skipped_conflicts),
        },
        "written": [_asset_to_dict(asset) for asset in result.written],
        "skipped_conflicts": [_asset_to_dict(asset) for asset in result.skipped_conflicts],
    }


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
        print(f"- {item.asset.path} ({item.asset.kind}) {item.recommendation}")


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
    if item.current_sha256:
        payload["current_sha256"] = item.current_sha256
    if item.current_reference_sha256:
        payload["current_reference_sha256"] = item.current_reference_sha256
    return payload


def _print_upgrade_or_json(report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_upgrade_to_dict(report), indent=2))
        return
    print(f"Upgrade preview: {report.path}")
    print(
        "Summary: "
        f"{len(report.safe_to_auto_apply)} safe_to_auto_apply, "
        f"{len(report.needs_user_review)} needs_user_review, "
        f"{len(report.blocked)} blocked, "
        f"{len(report.unavailable)} unavailable"
    )
    for note in report.notes:
        print(f"- {note}")
    _print_upstream_diff_items("Needs user review", report.needs_user_review)
    _print_upstream_diff_items("Blocked", report.blocked)


def _upgrade_to_dict(report) -> dict:
    return {
        "path": str(report.path),
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


def _planned_assets_by_path(options: ExistingBootstrapOptions) -> dict[str, object]:
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


def _conflict_suggestions(path: Path, conflicts, planned_by_path: dict[str, object]) -> list[dict]:
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
    return _bootstrap_existing(args)


def _keep_only_selection_attrs(args: argparse.Namespace, keep_attrs: tuple[str, ...]) -> None:
    selected = {
        attr: getattr(args, attr, None) or []
        for attr in SELECTION_ATTRS
    }
    for attr in SELECTION_ATTRS:
        setattr(args, attr, selected[attr] if attr in keep_attrs else [])
