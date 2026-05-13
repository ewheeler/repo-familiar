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


@dataclass(frozen=True)
class AdviceReport:
    path: Path
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
    recommended_skills: tuple[str, ...]
    rationale: tuple[str, ...]
    memory_guidance: tuple[str, ...]
    next_commands: tuple[str, ...]


def advise_existing_repository(path: Path) -> AdviceReport:
    if not path.exists() or not path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path}")
    signals = detect_repository_signals(path)
    stage = advice_dag.recommended_stage(signals)
    rationale = advice_dag.stage_rationale(signals, stage)
    has_user_facing_web = advice_dag.has_user_facing_web(signals)
    has_prompt_dag = advice_dag.has_prompt_dag(path)
    is_policy_or_education = advice_dag.is_policy_or_education(path)
    asset_groups = advice_dag.recommended_asset_groups(stage, signals, has_user_facing_web)
    sandbox_profiles = advice_dag.recommended_sandbox_profiles(stage, signals)
    tool_profiles = advice_dag.recommended_tool_profiles(has_user_facing_web)
    design_profiles = advice_dag.recommended_design_profiles(has_user_facing_web)
    prompt_profiles = advice_dag.recommended_prompt_profiles(has_prompt_dag)
    safety_profiles = advice_dag.recommended_safety_profiles(has_prompt_dag, has_user_facing_web, is_policy_or_education)
    privacy_profiles = advice_dag.recommended_privacy_profiles(is_policy_or_education, has_user_facing_web)
    repomap_profiles = advice_dag.recommended_repomap_profiles(has_prompt_dag, signals)
    worktree_profiles = advice_dag.recommended_worktree_profiles(stage, signals)
    secrets_profiles = advice_dag.recommended_secrets_profiles()
    skills = advice_dag.recommended_skills(has_user_facing_web, has_prompt_dag, safety_profiles, privacy_profiles)
    next_commands = recommended_commands(path, asset_groups, prompt_profiles, safety_profiles, privacy_profiles, repomap_profiles, sandbox_profiles, secrets_profiles, design_profiles, worktree_profiles)
    return AdviceReport(
        path=path,
        signals=signals,
        recommended_stage=stage,
        recommended_asset_groups=asset_groups,
        recommended_model_profiles=advice_dag.recommended_model_profiles(),
        recommended_tool_profiles=tool_profiles,
        recommended_memory_profiles=advice_dag.recommended_memory_profiles(),
        recommended_prompt_profiles=prompt_profiles,
        recommended_safety_profiles=safety_profiles,
        recommended_privacy_profiles=privacy_profiles,
        recommended_repomap_profiles=repomap_profiles,
        recommended_sandbox_profiles=sandbox_profiles,
        recommended_secrets_profiles=secrets_profiles,
        recommended_design_profiles=design_profiles,
        recommended_worktree_profiles=worktree_profiles,
        recommended_skills=skills,
        rationale=tuple(rationale),
        memory_guidance=advice_dag.memory_guidance(),
        next_commands=tuple(next_commands),
    )


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
    )


def recommended_commands(
    path: Path,
    asset_groups: tuple[str, ...],
    prompt_profiles: tuple[str, ...],
    safety_profiles: tuple[str, ...],
    privacy_profiles: tuple[str, ...],
    repomap_profiles: tuple[str, ...],
    sandbox_profiles: tuple[str, ...],
    secrets_profiles: tuple[str, ...],
    design_profiles: tuple[str, ...],
    worktree_profiles: tuple[str, ...],
) -> list[str]:
    quoted_path = json.dumps(str(path))
    group_args = " ".join(f"--asset-group {group}" for group in asset_groups)
    commands = [
        f"uv run python -m repo_familiar audit --path {quoted_path} {group_args}",
        f"uv run python -m repo_familiar bootstrap-existing --path {quoted_path} {group_args}",
        f"uv run python -m repo_familiar add-memory --path {quoted_path} --memory-profile memory-local",
    ]
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
    return commands
