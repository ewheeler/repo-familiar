from __future__ import annotations

from pathlib import Path

from .generator import (
    ExistingBootstrapOptions,
    GenerationOptions,
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
)


class InteractiveUnavailable(RuntimeError):
    pass


class InteractiveCancelled(RuntimeError):
    pass


def prompt_generation_options(args) -> GenerationOptions:
    questionary = _load_questionary()
    name = args.name or _ask_text(questionary, "Project name", default="Generated Project")
    output = args.output or Path(_ask_text(questionary, "Output directory", default=_default_output(name)))
    template = args.template or "basic"
    if len(list_templates()) > 1:
        template = _ask_select(questionary, "Template", choices=list_templates(), default=template)
    description = _ask_text(questionary, "Project description", default=args.description or "Generated with repo-familiar.")
    options = GenerationOptions(
        name=name,
        description=description,
        output_dir=Path(output),
        template=template,
        docs=args.docs or "quarto",
        agent_harnesses=_ask_many(questionary, "Agent harnesses", list_agent_harnesses(), _tuple_from_args(args.agent_harnesses, ("opencode",))),
        model_profiles=_ask_many(questionary, "Model profiles", list_model_profiles(), _tuple_from_args(args.model_profiles, ("default-coding",))),
        tool_profiles=_ask_many(questionary, "Tool profiles", list_tool_profiles(), _tuple_from_args(args.tool_profiles, ("cq",))),
        memory_profiles=_ask_many(questionary, "Memory profiles", list_memory_profiles(), _tuple_from_args(args.memory_profiles, ("memory-local",))),
        prompt_profiles=_ask_many(questionary, "Prompt profiles", list_prompt_profiles(), _tuple_from_args(args.prompt_profiles, ())),
        safety_profiles=_ask_many(questionary, "Safety profiles", list_safety_profiles(), _tuple_from_args(args.safety_profiles, ())),
        privacy_profiles=_ask_many(questionary, "Privacy profiles", list_privacy_profiles(), _tuple_from_args(args.privacy_profiles, ())),
        repomap_profiles=_ask_many(questionary, "Repo map profiles", list_repomap_profiles(), _tuple_from_args(args.repomap_profiles, ())),
        sandbox_profiles=_ask_many(questionary, "Sandbox profiles", list_sandbox_profiles(), _tuple_from_args(args.sandbox_profiles, ())),
        secrets_profiles=_ask_many(questionary, "Secrets profiles", list_secrets_profiles(), _tuple_from_args(args.secrets_profiles, ("dotenv-local", "kvenv-azure-keyvault"))),
        design_profiles=_ask_many(questionary, "Design profiles", list_design_profiles(), _tuple_from_args(args.design_profiles, ())),
        worktree_profiles=_ask_many(questionary, "Worktree profiles", list_worktree_profiles(), _tuple_from_args(args.worktree_profiles, ())),
        public_interest_profiles=_ask_many(questionary, "Public interest profiles", list_public_interest_profiles(), _tuple_from_args(args.public_interest_profiles, ())),
        skills=_ask_many(questionary, "Skills", list_skills(), _tuple_from_args(args.skills, ("grill-with-docs",))),
        reference_type=args.reference_type,
        reference_url=args.reference_url,
        reference_ref=args.reference_ref,
        generated_at=args.generated_at,
        sops_age_recipients=_tuple_from_args(args.sops_age_recipients, ()),
        force=args.force or _ask_confirm(questionary, "Overwrite existing generated files if needed?", default=False),
        dry_run=args.dry_run or _ask_confirm(questionary, "Dry run only?", default=True),
    )
    return options


def prompt_existing_options(args) -> tuple[ExistingBootstrapOptions, bool]:
    questionary = _load_questionary()
    path = args.path or Path(_ask_text(questionary, "Existing repository path", default="."))
    name = args.name or _ask_text(questionary, "Project display name", default=Path(path).name)
    asset_groups = _ask_many(
        questionary,
        "Asset groups",
        ["agent", "config", "design", "docs", "memory", "metadata", "models", "plan", "privacy", "public-interest", "prompts", "repomap", "safety", "sandbox", "secrets", "skills", "tools", "worktrees"],
        _tuple_from_args(args.asset_groups, ("memory", "metadata", "skills")),
    )
    apply = args.apply or _ask_confirm(questionary, "Write missing assets now?", default=False)
    force = args.force or (apply and _ask_confirm(questionary, "Overwrite conflicting assets?", default=False))
    options = ExistingBootstrapOptions(
        path=Path(path),
        name=name,
        description=args.description or "Bootstrapped with repo-familiar.",
        template=args.template or "basic",
        docs=args.docs or "quarto",
        agent_harnesses=_ask_many(questionary, "Agent harnesses", list_agent_harnesses(), _tuple_from_args(args.agent_harnesses, ("opencode",))),
        model_profiles=_ask_many(questionary, "Model profiles", list_model_profiles(), _tuple_from_args(args.model_profiles, ("default-coding",))),
        tool_profiles=_ask_many(questionary, "Tool profiles", list_tool_profiles(), _tuple_from_args(args.tool_profiles, ("cq",))),
        memory_profiles=_ask_many(questionary, "Memory profiles", list_memory_profiles(), _tuple_from_args(args.memory_profiles, ("memory-local",))),
        prompt_profiles=_ask_many(questionary, "Prompt profiles", list_prompt_profiles(), _tuple_from_args(args.prompt_profiles, ())),
        safety_profiles=_ask_many(questionary, "Safety profiles", list_safety_profiles(), _tuple_from_args(args.safety_profiles, ())),
        privacy_profiles=_ask_many(questionary, "Privacy profiles", list_privacy_profiles(), _tuple_from_args(args.privacy_profiles, ())),
        repomap_profiles=_ask_many(questionary, "Repo map profiles", list_repomap_profiles(), _tuple_from_args(args.repomap_profiles, ())),
        sandbox_profiles=_ask_many(questionary, "Sandbox profiles", list_sandbox_profiles(), _tuple_from_args(args.sandbox_profiles, ())),
        secrets_profiles=_ask_many(questionary, "Secrets profiles", list_secrets_profiles(), _tuple_from_args(args.secrets_profiles, ("dotenv-local", "kvenv-azure-keyvault"))),
        design_profiles=_ask_many(questionary, "Design profiles", list_design_profiles(), _tuple_from_args(args.design_profiles, ())),
        worktree_profiles=_ask_many(questionary, "Worktree profiles", list_worktree_profiles(), _tuple_from_args(args.worktree_profiles, ())),
        public_interest_profiles=_ask_many(questionary, "Public interest profiles", list_public_interest_profiles(), _tuple_from_args(args.public_interest_profiles, ())),
        skills=_ask_many(questionary, "Skills", list_skills(), _tuple_from_args(args.skills, ("grill-with-docs",))),
        reference_type=args.reference_type,
        reference_url=args.reference_url,
        reference_ref=args.reference_ref,
        generated_at=args.generated_at,
        sops_age_recipients=_tuple_from_args(args.sops_age_recipients, ()),
        asset_groups=asset_groups,
        force=force,
    )
    return options, apply


def _load_questionary():
    try:
        import questionary
    except ImportError as error:
        raise InteractiveUnavailable("Interactive mode requires questionary. Install project dependencies with `uv sync` or use flag-based commands.") from error
    return questionary


def _ask_text(questionary, message: str, *, default: str) -> str:
    answer = questionary.text(message, default=default).ask()
    if answer is None:
        raise InteractiveCancelled("Interactive prompt cancelled")
    return answer


def _ask_select(questionary, message: str, *, choices: list[str], default: str) -> str:
    answer = questionary.select(message, choices=choices, default=default).ask()
    if answer is None:
        raise InteractiveCancelled("Interactive prompt cancelled")
    return answer


def _ask_confirm(questionary, message: str, *, default: bool) -> bool:
    answer = questionary.confirm(message, default=default).ask()
    if answer is None:
        raise InteractiveCancelled("Interactive prompt cancelled")
    return bool(answer)


def _ask_many(questionary, message: str, choices: list[str], defaults: tuple[str, ...]) -> tuple[str, ...]:
    rendered_choices = [questionary.Choice(choice, checked=choice in defaults) for choice in choices]
    answer = questionary.checkbox(message, choices=rendered_choices).ask()
    if answer is None:
        raise InteractiveCancelled("Interactive prompt cancelled")
    return tuple(answer)


def _tuple_from_args(value, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    return tuple(value)


def _default_output(name: str) -> str:
    slug = "-".join(part for part in name.lower().split() if part)
    return slug or "generated-project"
