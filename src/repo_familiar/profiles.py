from __future__ import annotations

import json


MODEL_PROFILES = {
    "default-coding": {
        "provider": "openai",
        "model": "gpt-5.5",
        "use": "general coding and repository maintenance",
        "harnesses": ["opencode"],
        "notes": {
            "latency": "medium",
            "cost": "high",
            "strengths": ["codebase editing", "documentation"],
        },
    },
    "budget-review": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "use": "cheaper review and planning passes",
        "harnesses": ["opencode"],
        "notes": {
            "latency": "medium",
            "cost": "medium",
        },
    },
}

TOOL_PROFILES = {
    "cq": {
        "purpose": "query shared agent knowledge before implementation and before fixing errors",
        "config": "MCP/server setup remains machine-specific and is not generated as a secret",
        "notes": [
            "Use before implementation tasks where tool, version, or integration gotchas may matter",
            "Record useful discoveries back into the knowledge commons",
        ],
    },
    "a11y-scanner": {
        "purpose": "scan user-facing web outputs for automatically detectable accessibility issues",
        "config": "Use project-appropriate tools such as pa11y, axe-core, @axe-core/playwright, Lighthouse, or Playwright MCP/browser automation",
        "notes": [
            "Run automated scans during design iteration and before production handoff",
            "Treat automated results as a floor, not a complete accessibility review",
            "Pair scans with keyboard navigation, screen reader, focus management, and responsive checks",
        ],
    },
    "browser-automation": {
        "purpose": "let agents inspect rendered pages, interact with web apps, capture screenshots, check console errors, and run browser smoke checks",
        "config": "Use the project-appropriate browser driver: Playwright CLI for agent-friendly snapshots and screenshots, or Rodney for persistent Chrome sessions and shell-scriptable checks",
        "notes": [
            "Prefer rendered pages or local preview servers over static source inspection for layout and interaction checks",
            "Use Playwright CLI when the agent needs snapshots, screenshots, console inspection, and interactive page exploration",
            "Use Rodney when persistent Chrome state, shell scripting, JavaScript assertions, accessibility tree queries, or directory-scoped sessions are useful",
            "Keep browser session directories such as .rodney/ out of version control",
            "Record tested URLs, viewport sizes, screenshots, console errors, and remaining manual-review items in the task summary",
        ],
    },
    "opencode-homebrew-path": {
        "purpose": "document how macOS Homebrew users can expose CLIs such as node, npm, npx, pnpm, uv, and quarto to OpenCode agent shells",
        "config": "Agent-shell guidance only: if OpenCode uses /bin/zsh, put /opt/homebrew/bin and /usr/local/bin on PATH via ~/.zshenv so non-interactive tool calls can find Homebrew CLIs",
        "notes": [
            "This profile does not install Homebrew, mutate shell files, or configure a workstation automatically",
            "OpenCode tool calls may run in non-interactive shells that do not read ~/.zshrc",
            "For zsh, put export PATH=\"/opt/homebrew/bin:/usr/local/bin:$PATH\" in ~/.zshenv",
            "Set OpenCode global config shell to /bin/zsh in ~/.config/opencode/opencode.json when needed",
            "Verify inside the agent with node --version, npm --version, npx --version, pnpm --version, uv --version, and quarto --version",
            "If pnpm is still unavailable after PATH is fixed, run corepack enable outside the repository",
        ],
    }
}

MEMORY_PROFILES = {
    "memory-local": {
        "tool": "omega-memory or cq",
        "purpose": "local-first cross-session decisions, lessons, and repeated error patterns",
        "guidance": [
            "Prefer local-first memory stores for project-specific decisions and lessons",
            "Keep credentials and private personal data out of repository memory profiles",
            "Record selected memory profile names in bootstrap metadata only",
        ],
    }
}

PROMPT_PROFILES = {
    "prompt-migration-gpt55": {
        "tool": "eval fixtures, prompt inventory, GPT-5.5 prompt guidance, and optional OpenAI prompt optimizer",
        "purpose": "migrate older prompt DAGs toward GPT-5.5 behavior without changing outputs blindly",
        "guidance": [
            "Inventory prompts and classify each prompt's role in the DAG before editing",
            "Preserve baseline behavior with fixtures or golden examples before rewriting prompts",
            "Look for contradictory instructions, excessive context-gathering pressure, and unclear stop conditions",
            "Prefer minimal prompt diffs with measurable acceptance criteria over broad rewrites",
        ],
    },
    "prompt-evals-dag": {
        "tool": "prompt fixtures, DAG node outputs, regression snapshots, and task-aware evaluation metadata",
        "purpose": "evaluate prompt DAG behavior across model versions and prompt revisions",
        "guidance": [
            "Create fixtures at meaningful DAG boundaries, not only final outputs",
            "Track model, prompt version, input fixture, output schema, and acceptance criteria",
            "Use metadata to define expected response features instead of relying only on prompt wording",
            "Run evals before and after prompt migration and record deltas",
        ],
    },
}

SAFETY_PROFILES = {
    "prompt-output-safety": {
        "tool": "guardrail evals, policy checks, red-team prompts, and output review rubrics",
        "purpose": "review AI prompts and outputs for unsafe, inappropriate, or policy-sensitive behavior",
        "guidance": [
            "Identify user-facing outputs, vulnerable audiences, and high-impact failure modes",
            "Create adversarial fixtures before changing safety-sensitive prompts",
            "Check refusals, uncertainty, escalation paths, and harmful instruction handling",
            "Keep raw sensitive examples out of committed fixtures unless sanitized",
        ],
    }
}

PRIVACY_PROFILES = {
    "data-privacy-review": {
        "tool": "PII inventory, data classification, retention review, and privacy threat modeling",
        "purpose": "review repositories for sensitive data handling and privacy risks",
        "guidance": [
            "Classify personal, sensitive, child-related, and operational data flows",
            "Check prompts, logs, caches, memory, analytics, and exported artifacts for data leakage",
            "Prefer data minimization and explicit retention boundaries",
            "Document privacy assumptions and unresolved risks before production-maintenance stage",
        ],
    }
}

REPOMAP_PROFILES = {
    "hamilton-dag": {
        "tool": "Hamilton DAG visualization and graph fingerprints",
        "purpose": "map dataflow, prompt chains, and pipeline abstractions using Hamilton DAGs",
        "guidance": [
            "Use Hamilton DAG images as architecture artifacts for prompt and data pipelines",
            "Keep non-DAG helper functions outside Hamilton modules when graph fingerprints matter",
            "Record node/edge counts and graph fingerprints when using DAGs for regression checks",
            "Use DAG boundaries to choose prompt eval fixtures and review abstraction seams",
        ],
    }
}

SANDBOX_PROFILES = {
    "sandbox-light": {
        "tool": "zerobox",
        "purpose": "run generated code, tests, installs, and unknown scripts with constrained writes and network",
        "guidance": [
            "Default to no network for generated or unknown code",
            "Allow writes only to explicit build, temp, or output directories",
            "Use snapshots or restore behavior for risky package or codegen commands",
        ],
    },
    "sandbox-agent-runtime": {
        "tool": "OpenShell",
        "purpose": "policy-governed runtime for longer autonomous agent sessions",
        "guidance": [
            "Use declarative filesystem, network, process, and inference policies",
            "Treat credential providers as runtime injection, not repository secrets",
            "Prefer for production-maintenance or high-autonomy workflows",
        ],
    },
}

SECRETS_PROFILES = {
    "dotenv-local": {
        "tool": "python-dotenv, dotenvx, framework-native dotenv loading, or shell export",
        "purpose": "local development environment variables with committed examples and ignored real values",
        "guidance": [
            "Commit .env.example with placeholder names and non-secret defaults only",
            "Ignore .env, .env.*, and local override files except .env.example",
            "Load dotenv files explicitly in development entrypoints or via framework-native dotenv support",
        ],
    },
    "kvenv-azure-keyvault": {
        "tool": "kvenv",
        "purpose": "use Azure Key Vault references in dotenv files so agents see references, not secret values",
        "guidance": [
            "Use kv:// references in .env files instead of literal secrets",
            "Authenticate with Azure CLI outside the repository",
            "Run commands through kvenv so real values are fetched at process start",
        ],
    },
    "onepassword-op": {
        "tool": "1Password CLI op run",
        "purpose": "inject local or team-managed secrets into process environments without writing them to repo files",
        "guidance": [
            "Store secrets in 1Password and commit only reference placeholders or .env.example",
            "Run local commands through op run or op inject when secret values are needed",
            "Keep 1Password item names and vault naming conventions documented without exposing secret values",
        ],
    },
}

DESIGN_PROFILES = {
    "design-impeccable": {
        "tool": "impeccable",
        "purpose": "shared design vocabulary and anti-pattern checks for frontend or published docs work",
        "guidance": [
            "Use design critique before polishing UI or documentation sites",
            "Avoid generic AI frontend defaults and overused visual patterns",
            "Keep project design guidance in repository docs such as DESIGN.md when adopted",
        ],
    },
    "design-a11y": {
        "tool": "axe-core, pa11y, Lighthouse, Playwright, or equivalent accessibility scanners",
        "purpose": "accessibility-first design checks for user-facing web outputs",
        "guidance": [
            "Scan rendered pages or app routes for WCAG A/AA issues before design polish is considered complete",
            "Include keyboard navigation, focus order, labels, headings, landmarks, contrast, alt text, and form semantics in review",
            "Document known issues and suppressions explicitly instead of silently excluding broad selectors or rules",
        ],
    }
}

WORKTREE_PROFILES = {
    "parallel-worktrees": {
        "tool": "coasts or git worktrees",
        "purpose": "parallel agent/prototype workflows with isolated services and ports",
        "guidance": [
            "Use worktrees for parallel prototypes or agent tasks",
            "Avoid sharing mutable service state across concurrent agent runs",
            "Prefer explicit checkout/cleanup flows for production-maintenance work",
        ],
    }
}

SKILLS = {
    "grill-with-docs": "Stress-test plans against project language and documented decisions",
    "get-api-docs": "Fetch current third-party API, SDK, and library documentation before integration work",
    "playwright-cli": "Use Playwright CLI for browser inspection, screenshots, console errors, and web interaction checks",
    "rodney-browser": "Use Rodney for persistent Chrome automation, shell-scripted web checks, and accessibility tree queries",
    "upstream-improvement": "Prepare safe upstream improvement proposals from downstream generated asset changes",
    "a11y-web-scan": "Plan and run accessibility scans for user-facing web outputs",
    "prompt-migration": "Migrate prompt DAGs across model versions safely",
    "prompt-eval-design": "Design lightweight evals for prompt DAGs and model-version migrations",
    "prompt-output-safety": "Review prompts and outputs for unsafe or policy-sensitive behavior",
    "privacy-review": "Review data flows, prompts, logs, memory, and outputs for privacy risks",
}


def list_names(registry: dict) -> list[str]:
    return sorted(registry)


def validate_profile_selections(selections: dict[str, tuple[str, ...]]) -> None:
    _validate("model profile", selections.get("model_profiles", ()), MODEL_PROFILES)
    _validate("tool profile", selections.get("tool_profiles", ()), TOOL_PROFILES)
    _validate("memory profile", selections.get("memory_profiles", ()), MEMORY_PROFILES)
    _validate("prompt profile", selections.get("prompt_profiles", ()), PROMPT_PROFILES)
    _validate("safety profile", selections.get("safety_profiles", ()), SAFETY_PROFILES)
    _validate("privacy profile", selections.get("privacy_profiles", ()), PRIVACY_PROFILES)
    _validate("repomap profile", selections.get("repomap_profiles", ()), REPOMAP_PROFILES)
    _validate("sandbox profile", selections.get("sandbox_profiles", ()), SANDBOX_PROFILES)
    _validate("secrets profile", selections.get("secrets_profiles", ()), SECRETS_PROFILES)
    _validate("design profile", selections.get("design_profiles", ()), DESIGN_PROFILES)
    _validate("worktree profile", selections.get("worktree_profiles", ()), WORKTREE_PROFILES)
    _validate("skill", selections.get("skills", ()), SKILLS)


def render_model_profiles(profile_names: tuple[str, ...]) -> str:
    lines: list[str] = []
    for name in profile_names:
        profile = MODEL_PROFILES[name]
        lines.append(f"  {name}:")
        lines.append(f"    provider: {_yaml_scalar(profile['provider'])}")
        lines.append(f"    model: {_yaml_scalar(profile['model'])}")
        lines.append(f"    use: {_yaml_scalar(profile['use'])}")
        lines.append("    harnesses:")
        lines.extend(_yaml_list(profile["harnesses"], indent="      "))
        notes = profile.get("notes", {})
        if notes:
            lines.append("    notes:")
            for key, value in notes.items():
                if isinstance(value, list):
                    lines.append(f"      {key}:")
                    lines.extend(_yaml_list(value, indent="        "))
                else:
                    lines.append(f"      {key}: {_yaml_scalar(value)}")
    return "\n".join(lines)


def render_tool_profiles(profile_names: tuple[str, ...]) -> str:
    lines: list[str] = []
    for name in profile_names:
        profile = TOOL_PROFILES[name]
        lines.append(f"  {name}:")
        lines.append(f"    purpose: {_yaml_scalar(profile['purpose'])}")
        lines.append(f"    config: {_yaml_scalar(profile['config'])}")
        notes = profile.get("notes", [])
        if notes:
            lines.append("    notes:")
            lines.extend(_yaml_list(notes, indent="      "))
    return "\n".join(lines)


def render_advisory_profiles(registry: dict, profile_names: tuple[str, ...]) -> str:
    lines: list[str] = []
    for name in profile_names:
        profile = registry[name]
        lines.append(f"  {name}:")
        lines.append(f"    tool: {_yaml_scalar(profile['tool'])}")
        lines.append(f"    purpose: {_yaml_scalar(profile['purpose'])}")
        guidance = profile.get("guidance", [])
        if guidance:
            lines.append("    guidance:")
            lines.extend(_yaml_list(guidance, indent="      "))
    return "\n".join(lines) if lines else "  {}"


def _validate(label: str, values: tuple[str, ...], registry: dict) -> None:
    unknown = sorted(set(values) - set(registry))
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"Unknown {label}(s): {joined}")


def _yaml_list(values, *, indent: str) -> list[str]:
    return [f"{indent}- {_yaml_scalar(value)}" for value in values]


def _yaml_scalar(value) -> str:
    return json.dumps(str(value))
