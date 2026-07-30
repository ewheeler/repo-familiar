from __future__ import annotations

from pathlib import Path


def recommended_stage(signals) -> str:
    if not signals.has_context or not signals.has_plan:
        return "research-heavy"
    if signals.has_tests and (signals.has_ci or signals.has_container_config):
        return "production-maintenance"
    return "prototype-fast"


def stage_rationale(signals, recommended_stage: str) -> tuple[str, ...]:
    if recommended_stage == "research-heavy":
        return ("Missing project context or plan; start by making intent and terminology explicit.",)
    if recommended_stage == "production-maintenance":
        return ("Tests plus CI/container signals suggest maintenance discipline is already relevant.",)
    return ("Project has enough structure to iterate, but production guardrails are not fully signaled.",)


def has_user_facing_web(signals) -> bool:
    return signals.has_frontend or signals.has_design_docs or signals.has_quarto


def has_prompt_dag(path: Path) -> bool:
    return (path / "prompts").exists() or any(path.glob("**/*prompt*")) or any(path.glob("**/*stage*"))


def is_policy_or_education(path: Path) -> bool:
    return any(part in path.name.lower() for part in ("policy", "education", "kids", "child"))


def recommended_asset_groups(recommended_stage: str, signals, has_user_facing_web: bool) -> tuple[str, ...]:
    groups = ["agent", "memory", "metadata", "secrets", "skills"]
    if recommended_stage == "research-heavy":
        groups.extend(["docs", "plan"])
    elif recommended_stage == "prototype-fast":
        groups.extend(["docs", "models", "tools", "plan", "sandbox"])
    else:
        groups.extend(["config", "models", "tools", "sandbox", "worktrees"])
    if has_user_facing_web:
        groups.append("design")
    if signals.has_container_config or recommended_stage != "research-heavy":
        groups.append("worktrees")
    return tuple(dict.fromkeys(groups))


def recommended_model_profiles() -> tuple[str, ...]:
    return ("default-coding",)


def recommended_tool_profiles(has_user_facing_web: bool) -> tuple[str, ...]:
    if has_user_facing_web:
        return ("cq", "browser-automation", "a11y-scanner")
    return ("cq",)


def recommended_memory_profiles() -> tuple[str, ...]:
    return ("memory-local",)


def recommended_prompt_profiles(has_prompt_dag: bool) -> tuple[str, ...]:
    if has_prompt_dag:
        return ("prompt-migration-gpt55", "prompt-evals-dag")
    return ()


def recommended_safety_profiles(has_prompt_dag: bool, has_user_facing_web: bool, is_policy_or_education: bool) -> tuple[str, ...]:
    if has_prompt_dag or has_user_facing_web or is_policy_or_education:
        return ("prompt-output-safety",)
    return ()


def recommended_privacy_profiles(is_policy_or_education: bool, has_user_facing_web: bool) -> tuple[str, ...]:
    if is_policy_or_education or has_user_facing_web:
        return ("data-privacy-review",)
    return ()


def recommended_repomap_profiles(has_prompt_dag: bool, signals) -> tuple[str, ...]:
    profiles = []
    if signals.has_docs and signals.has_tests:
        profiles.append("semantic-routing-map")
    if has_prompt_dag or signals.has_python:
        profiles.append("hamilton-dag")
    return tuple(profiles)


def recommended_sandbox_profiles(recommended_stage: str, signals) -> tuple[str, ...]:
    if recommended_stage == "production-maintenance":
        return ("sandbox-light", "sandbox-agent-runtime")
    if signals.has_tests or signals.has_python or signals.has_frontend or signals.has_container_config:
        return ("sandbox-light",)
    return ()


def recommended_secrets_profiles() -> tuple[str, ...]:
    return ("dotenv-local", "kvenv-azure-keyvault")


def recommended_design_profiles(has_user_facing_web: bool) -> tuple[str, ...]:
    if has_user_facing_web:
        return ("design-impeccable", "design-a11y")
    return ()


def recommended_worktree_profiles(recommended_stage: str, signals) -> tuple[str, ...]:
    if recommended_stage != "research-heavy" or signals.has_container_config:
        return ("parallel-worktrees",)
    return ()


def recommended_skills(has_user_facing_web: bool, has_prompt_dag: bool, recommended_safety_profiles: tuple[str, ...], recommended_privacy_profiles: tuple[str, ...]) -> tuple[str, ...]:
    skills = ["grill-with-docs"]
    if has_user_facing_web:
        skills.extend(["playwright-cli", "a11y-web-scan"])
    if has_prompt_dag:
        skills.extend(["prompt-migration", "prompt-eval-design"])
    if recommended_safety_profiles:
        skills.append("prompt-output-safety")
    if recommended_privacy_profiles:
        skills.append("privacy-review")
    return tuple(dict.fromkeys(skills))


def memory_guidance() -> tuple[str, ...]:
    return (
        "At session start, query memory for project decisions, conventions, recurring errors, and current stage.",
        "Store accepted architectural decisions, resolved ambiguities, and non-obvious debugging lessons immediately after they stabilize.",
        "Store stage transitions with the reason for the transition and the profiles/tools selected at that point.",
        "Do not store secrets, credentials, private personal data, or machine-specific paths in memory.",
        "Use repository docs and bootstrap metadata as the canonical record; memory should accelerate recall, not replace committed context.",
    )
