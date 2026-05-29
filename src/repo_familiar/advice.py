from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from . import advice_dag


@dataclass(frozen=True)
class RepositorySignals:
    has_agent_instructions: bool
    has_bootstrap_metadata: bool
    has_context: bool
    has_docs: bool
    has_quarto: bool
    has_plan: bool
    has_tests: bool
    has_ci: bool
    has_python: bool
    has_frontend: bool
    has_container_config: bool
    has_design_docs: bool
    has_dotenv: bool
    has_sops_config: bool


@dataclass(frozen=True)
class AdviceReport:
    path: Path
    intended_work: tuple[str, ...]
    signals: RepositorySignals
    recommended_stage: str
    recommended_asset_groups: tuple[str, ...]
    recommended_model_profiles: tuple[str, ...]
    recommended_tool_profiles: tuple[str, ...]
    recommended_memory_profiles: tuple[str, ...]
    recommended_prompt_profiles: tuple[str, ...]
    recommended_safety_profiles: tuple[str, ...]
    recommended_privacy_profiles: tuple[str, ...]
    recommended_repomap_profiles: tuple[str, ...]
    recommended_sandbox_profiles: tuple[str, ...]
    recommended_secrets_profiles: tuple[str, ...]
    recommended_design_profiles: tuple[str, ...]
    recommended_worktree_profiles: tuple[str, ...]
    recommended_public_interest_profiles: tuple[str, ...]
    recommended_skills: tuple[str, ...]
    rationale: tuple[str, ...]
    memory_guidance: tuple[str, ...]
    next_commands: tuple[str, ...]


def advise_existing_repository(path: Path, intended_work: tuple[str, ...] = ()) -> AdviceReport:
    if not path.exists() or not path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path}")
    signals = detect_repository_signals(path)
    base_stage = advice_dag.recommended_stage(signals)
    stage = _stage_for_intent(base_stage, intended_work)
    rationale = [*advice_dag.stage_rationale(signals, stage)]
    if intended_work:
        rationale.append(f"User intent adjusts recommendations: {', '.join(intended_work)}.")
    has_user_facing_web = advice_dag.has_user_facing_web(signals)
    has_prompt_dag = advice_dag.has_prompt_dag(path)
    is_policy_or_education = advice_dag.is_policy_or_education(path)
    sandbox_profiles = _extend(advice_dag.recommended_sandbox_profiles(stage, signals), _intent_sandbox_profiles(intended_work))
    tool_profiles = advice_dag.recommended_tool_profiles(has_user_facing_web)
    design_profiles = advice_dag.recommended_design_profiles(has_user_facing_web)
    prompt_profiles = _extend(advice_dag.recommended_prompt_profiles(has_prompt_dag), _intent_prompt_profiles(intended_work))
    safety_profiles = _extend(advice_dag.recommended_safety_profiles(has_prompt_dag, has_user_facing_web, is_policy_or_education), _intent_safety_profiles(intended_work))
    privacy_profiles = _extend(advice_dag.recommended_privacy_profiles(is_policy_or_education, has_user_facing_web), _intent_privacy_profiles(intended_work))
    repomap_profiles = advice_dag.recommended_repomap_profiles(has_prompt_dag, signals)
    worktree_profiles = advice_dag.recommended_worktree_profiles(stage, signals)
    public_interest_profiles = _recommended_public_interest_profiles(is_policy_or_education)
    secrets_profiles = _extend(advice_dag.recommended_secrets_profiles(), _recommended_sops_profiles(signals))
    skills = _extend(advice_dag.recommended_skills(has_user_facing_web, has_prompt_dag, safety_profiles, privacy_profiles), _intent_skills(intended_work))
    model_profiles = advice_dag.recommended_model_profiles()
    memory_profiles = advice_dag.recommended_memory_profiles()
    asset_groups = _asset_groups_for_recommendations(
        advice_dag.recommended_asset_groups(stage, signals, has_user_facing_web),
        model_profiles,
        tool_profiles,
        memory_profiles,
        prompt_profiles,
        safety_profiles,
        privacy_profiles,
        repomap_profiles,
        sandbox_profiles,
        secrets_profiles,
        design_profiles,
        worktree_profiles,
        public_interest_profiles,
    )
    next_commands = recommended_commands(path, asset_groups, skills, prompt_profiles, safety_profiles, privacy_profiles, repomap_profiles, sandbox_profiles, secrets_profiles, design_profiles, worktree_profiles, public_interest_profiles)
    return AdviceReport(
        path=path,
        intended_work=intended_work,
        signals=signals,
        recommended_stage=stage,
        recommended_asset_groups=asset_groups,
        recommended_model_profiles=model_profiles,
        recommended_tool_profiles=tool_profiles,
        recommended_memory_profiles=memory_profiles,
        recommended_prompt_profiles=prompt_profiles,
        recommended_safety_profiles=safety_profiles,
        recommended_privacy_profiles=privacy_profiles,
        recommended_repomap_profiles=repomap_profiles,
        recommended_sandbox_profiles=sandbox_profiles,
        recommended_secrets_profiles=secrets_profiles,
        recommended_design_profiles=design_profiles,
        recommended_worktree_profiles=worktree_profiles,
        recommended_public_interest_profiles=public_interest_profiles,
        recommended_skills=skills,
        rationale=tuple(rationale),
        memory_guidance=advice_dag.memory_guidance(),
        next_commands=tuple(next_commands),
    )


def _stage_for_intent(base_stage: str, intended_work: tuple[str, ...]) -> str:
    if any(intent in intended_work for intent in ("significant-refactor", "prompt-migration", "docs-setup")):
        return "implementation-planning"
    if "production-maintenance" in intended_work:
        return "production-maintenance"
    return base_stage


def _intent_skills(intended_work: tuple[str, ...]) -> tuple[str, ...]:
    skills: list[str] = ["cq", "session-focus"]
    if "significant-refactor" in intended_work:
        skills.extend(["improve-codebase-architecture", "tdd", "qa-test-design"])
    if "prompt-migration" in intended_work:
        skills.extend(["prompt-migration", "prompt-eval-design"])
    if "security-review" in intended_work:
        skills.append("security-audit")
    if "production-maintenance" in intended_work:
        skills.extend(["diagnose", "security-audit"])
    if "docs-setup" in intended_work:
        skills.extend(["grill-with-docs", "to-prd", "to-issues"])
    return tuple(skills)


def _intent_prompt_profiles(intended_work: tuple[str, ...]) -> tuple[str, ...]:
    if "prompt-migration" in intended_work:
        return ("prompt-migration-gpt55", "prompt-evals-dag")
    return ()


def _intent_safety_profiles(intended_work: tuple[str, ...]) -> tuple[str, ...]:
    if any(intent in intended_work for intent in ("security-review", "production-maintenance")):
        return ("prompt-output-safety",)
    return ()


def _intent_privacy_profiles(intended_work: tuple[str, ...]) -> tuple[str, ...]:
    if "security-review" in intended_work:
        return ("data-privacy-review",)
    return ()


def _intent_sandbox_profiles(intended_work: tuple[str, ...]) -> tuple[str, ...]:
    if any(intent in intended_work for intent in ("significant-refactor", "production-maintenance")):
        return ("sandbox-light",)
    return ()


def _recommended_public_interest_profiles(is_policy_or_education: bool) -> tuple[str, ...]:
    if is_policy_or_education:
        return ("child-rights-digital", "public-interest-digital")
    return ()


def _recommended_sops_profiles(signals: RepositorySignals) -> tuple[str, ...]:
    if signals.has_dotenv and not signals.has_sops_config:
        return ("sops-age",)
    return ()


def _extend(base: tuple[str, ...], additions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*base, *additions)))


def _asset_groups_for_recommendations(
    base_groups: tuple[str, ...],
    model_profiles: tuple[str, ...],
    tool_profiles: tuple[str, ...],
    memory_profiles: tuple[str, ...],
    prompt_profiles: tuple[str, ...],
    safety_profiles: tuple[str, ...],
    privacy_profiles: tuple[str, ...],
    repomap_profiles: tuple[str, ...],
    sandbox_profiles: tuple[str, ...],
    secrets_profiles: tuple[str, ...],
    design_profiles: tuple[str, ...],
    worktree_profiles: tuple[str, ...],
    public_interest_profiles: tuple[str, ...],
) -> tuple[str, ...]:
    groups = list(base_groups)
    for has_profiles, group in (
        (model_profiles, "models"),
        (tool_profiles, "tools"),
        (memory_profiles, "memory"),
        (prompt_profiles, "prompts"),
        (safety_profiles, "safety"),
        (privacy_profiles, "privacy"),
        (repomap_profiles, "repomap"),
        (sandbox_profiles, "sandbox"),
        (secrets_profiles, "secrets"),
        (design_profiles, "design"),
        (worktree_profiles, "worktrees"),
        (public_interest_profiles, "public-interest"),
    ):
        if has_profiles:
            groups.append(group)
    return tuple(dict.fromkeys(groups))


def detect_repository_signals(path: Path) -> RepositorySignals:
    return RepositorySignals(
        has_agent_instructions=(path / "AGENTS.md").exists() or (path / "CLAUDE.md").exists(),
        has_bootstrap_metadata=(path / ".repo-familiar/bootstrap.yml").exists(),
        has_context=(path / "CONTEXT.md").exists() or (path / "CONTEXT-MAP.md").exists(),
        has_docs=(path / "docs").exists() or (path / "README.md").exists(),
        has_quarto=(path / "docs/_quarto.yml").exists() or (path / "_quarto.yml").exists(),
        has_plan=(path / "plan.md").exists() or (path / "PLAN.md").exists(),
        has_tests=(path / "tests").exists() or any(path.glob("test_*.py")) or any(path.glob("**/*.test.*")),
        has_ci=(path / ".github/workflows").exists() or (path / ".gitlab-ci.yml").exists(),
        has_python=(path / "pyproject.toml").exists() or (path / "requirements.txt").exists(),
        has_frontend=(path / "package.json").exists() or (path / "src").joinpath("components").exists(),
        has_container_config=(path / "docker-compose.yml").exists() or (path / "compose.yml").exists() or (path / "Dockerfile").exists() or (path / "Coastfile").exists(),
        has_design_docs=(path / "DESIGN.md").exists() or (path / "STYLE.md").exists(),
        has_dotenv=(path / ".env").exists() or (path / ".env.example").exists() or any(path.glob(".env.*")),
        has_sops_config=(path / ".sops.yaml").exists() or (path / ".sops.yml").exists(),
    )


def recommended_commands(
    path: Path,
    asset_groups: tuple[str, ...],
    skills: tuple[str, ...],
    prompt_profiles: tuple[str, ...],
    safety_profiles: tuple[str, ...],
    privacy_profiles: tuple[str, ...],
    repomap_profiles: tuple[str, ...],
    sandbox_profiles: tuple[str, ...],
    secrets_profiles: tuple[str, ...],
    design_profiles: tuple[str, ...],
    worktree_profiles: tuple[str, ...],
    public_interest_profiles: tuple[str, ...],
) -> list[str]:
    quoted_path = json.dumps(str(path))
    group_args = " ".join(f"--asset-group {group}" for group in asset_groups)
    commands = [
        f"uv run python -m repo_familiar audit --path {quoted_path} {group_args}",
        f"uv run python -m repo_familiar bootstrap-existing --path {quoted_path} {group_args}",
        f"uv run python -m repo_familiar add-memory --path {quoted_path} --memory-profile memory-local",
    ]
    for skill in skills:
        commands.append(f"uv run python -m repo_familiar add-skill --path {quoted_path} --skill {skill}")
    for prompt_profile in prompt_profiles:
        commands.append(f"uv run python -m repo_familiar add-prompts --path {quoted_path} --prompt-profile {prompt_profile}")
    for safety_profile in safety_profiles:
        commands.append(f"uv run python -m repo_familiar add-safety --path {quoted_path} --safety-profile {safety_profile}")
    for privacy_profile in privacy_profiles:
        commands.append(f"uv run python -m repo_familiar add-privacy --path {quoted_path} --privacy-profile {privacy_profile}")
    for repomap_profile in repomap_profiles:
        commands.append(f"uv run python -m repo_familiar add-repomap --path {quoted_path} --repomap-profile {repomap_profile}")
    for sandbox_profile in sandbox_profiles:
        commands.append(f"uv run python -m repo_familiar add-sandbox --path {quoted_path} --sandbox-profile {sandbox_profile}")
    for secrets_profile in secrets_profiles:
        commands.append(f"uv run python -m repo_familiar add-secrets --path {quoted_path} --secrets-profile {secrets_profile}")
    for design_profile in design_profiles:
        commands.append(f"uv run python -m repo_familiar add-design --path {quoted_path} --design-profile {design_profile}")
    for worktree_profile in worktree_profiles:
        commands.append(f"uv run python -m repo_familiar add-worktree --path {quoted_path} --worktree-profile {worktree_profile}")
    for public_interest_profile in public_interest_profiles:
        commands.append(f"uv run python -m repo_familiar add-public-interest --path {quoted_path} --public-interest-profile {public_interest_profile}")
    return commands
