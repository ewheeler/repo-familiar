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
        "setup": [
            "Install and configure the cq MCP/server outside the repository following https://github.com/mozilla-ai/cq",
            "Enable cq tools in the agent harness before relying on the cq skill",
        ],
        "verify": [
            "Confirm cq MCP tools are available in the agent harness",
            "Run cq status when the local setup exposes a cq CLI/server status command",
        ],
        "notes": [
            "Use before implementation tasks where tool, version, or integration gotchas may matter",
            "Record useful discoveries back into the knowledge commons",
        ],
    },
    "a11y-scanner": {
        "purpose": "scan user-facing web outputs for automatically detectable accessibility issues",
        "config": "Use project-appropriate tools such as pa11y, axe-core, @axe-core/playwright, Lighthouse, or Playwright MCP/browser automation",
        "setup": [
            "Use existing project accessibility tooling when present",
            "For Node projects, prefer project-local dev dependencies such as pa11y, @axe-core/playwright, or Lighthouse",
        ],
        "verify": [
            "npx pa11y --help",
            "npx lighthouse --help",
        ],
        "notes": [
            "Run automated scans during design iteration and before production handoff",
            "Treat automated results as a floor, not a complete accessibility review",
            "Pair scans with keyboard navigation, screen reader, focus management, and responsive checks",
        ],
    },
    "browser-automation": {
        "purpose": "let agents inspect rendered pages, interact with web apps, capture screenshots, check console errors, and run browser smoke checks",
        "config": "Use the project-appropriate browser driver: Playwright CLI for agent-friendly snapshots and screenshots, or Rodney for persistent Chrome sessions and shell-scriptable checks",
        "setup": [
            "Install Playwright CLI with npm install -g @playwright/cli@latest or use npx playwright-cli when available project-locally",
            "Install or build Rodney from https://github.com/simonw/rodney when persistent Chrome sessions or accessibility tree queries are needed",
        ],
        "verify": [
            "playwright-cli --help or npx playwright-cli --help",
            "rodney --help",
        ],
        "notes": [
            "Prefer rendered pages or local preview servers over static source inspection for layout and interaction checks",
            "Use Playwright CLI when the agent needs snapshots, screenshots, console inspection, and interactive page exploration",
            "Use Rodney when persistent Chrome state, shell scripting, JavaScript assertions, accessibility tree queries, or directory-scoped sessions are useful",
            "Keep browser session directories such as .rodney/ out of version control",
            "Record tested URLs, viewport sizes, screenshots, console errors, and remaining manual-review items in the task summary",
        ],
    },
    "headroom-context-compression": {
        "purpose": "reduce agent context/token usage with local-first reversible compression, proxy, wrapper, and MCP workflows",
        "config": "Use Headroom as an explicit opt-in context compression layer for large repos, long agent sessions, verbose logs, RAG chunks, or multi-agent memory workflows",
        "setup": [
            "Install Headroom outside repo-familiar, for example `pip install \"headroom-ai[all]\"` or `npm install headroom-ai`",
            "For MCP workflows, install the relevant Headroom extra and run the project-appropriate MCP setup command from Headroom docs",
            "Use `headroom wrap <agent>` only when the team explicitly wants a wrapped agent process",
        ],
        "verify": [
            "headroom --help",
            "headroom stats",
            "headroom mcp --help",
        ],
        "notes": [
            "Headroom should stay opt-in because it changes the agent runtime/context path",
            "Keep originals retrievable and avoid using compression as a substitute for project documentation",
            "Prefer read-only/proxy/MCP trials before making Headroom part of a production-maintenance workflow",
        ],
    },
    "opencode-homebrew-path": {
        "purpose": "document how macOS Homebrew users can expose CLIs such as node, npm, npx, pnpm, uv, and quarto to OpenCode agent shells",
        "config": "Agent-shell guidance only: if OpenCode uses /bin/zsh, put /opt/homebrew/bin and /usr/local/bin on PATH via ~/.zshenv so non-interactive tool calls can find Homebrew CLIs",
        "setup": [
            "For zsh, put export PATH=\"/opt/homebrew/bin:/usr/local/bin:$PATH\" in ~/.zshenv",
            "Set OpenCode global config shell to /bin/zsh in ~/.config/opencode/opencode.json when needed",
        ],
        "verify": [
            "node --version",
            "npm --version",
            "npx --version",
            "pnpm --version",
            "uv --version",
            "quarto --version",
        ],
        "notes": [
            "This profile does not install Homebrew, mutate shell files, or configure a workstation automatically",
            "OpenCode tool calls may run in non-interactive shells that do not read ~/.zshrc",
            "If pnpm is still unavailable after PATH is fixed, run corepack enable outside the repository",
        ],
    },
    "opencode-playwright-mcp": {
        "purpose": "configure project-local OpenCode access to the Playwright MCP server",
        "config": "Adds a non-secret local MCP server entry to opencode.json using npx -y @playwright/mcp",
        "setup": [
            "Select this profile only when OpenCode should launch Playwright MCP for this project",
            "Ensure Node and npx are visible to OpenCode's shell before relying on this MCP server",
        ],
        "verify": [
            "npx -y @playwright/mcp --help",
            "Restart OpenCode after opencode.json changes",
        ],
        "notes": [
            "This profile does not install browsers or Node dependencies by itself",
            "Use with browser-automation, playwright-cli, or a11y-web-scan when browser MCP tooling is useful",
        ],
    },
    "opencode-cq-mcp": {
        "purpose": "configure project-local OpenCode access to the cq MCP server",
        "config": "Adds a non-secret local MCP server entry to opencode.json using cq mcp on PATH",
        "setup": [
            "Install and configure cq outside the repository before selecting this profile",
            "Ensure the cq executable is on PATH for OpenCode's shell",
        ],
        "verify": [
            "cq --help",
            "Restart OpenCode after opencode.json changes",
        ],
        "notes": [
            "Do not copy machine-specific absolute cq runtime paths into generated project config",
            "Use global OpenCode config for machine-local cq paths when cq is not on PATH",
        ],
    },
    "opencode-context7-mcp": {
        "purpose": "configure project-local OpenCode access to Context7 MCP with an environment-provided API key",
        "config": "Adds a remote MCP server entry to opencode.json using https://mcp.context7.com/mcp and ${CONTEXT7_API_KEY}",
        "setup": [
            "Set CONTEXT7_API_KEY outside the repository before using this MCP server",
            "Never commit literal Context7 API keys in opencode.json or .agents files",
        ],
        "verify": [
            "Confirm CONTEXT7_API_KEY is set in the OpenCode shell environment",
            "Restart OpenCode after opencode.json changes",
        ],
        "notes": [
            "Project config should reference ${CONTEXT7_API_KEY}, not a literal token",
            "Use only when current package/library documentation lookup through Context7 is needed",
        ],
    }
}

MEMORY_PROFILES = {
    "memory-local": {
        "tool": "omega-memory or cq",
        "purpose": "local-first cross-session decisions, lessons, and repeated error patterns",
        "setup": [
            "Configure omega-memory or cq outside the repository; keep memory stores local-first unless a team explicitly opts into sync",
        ],
        "verify": [
            "Confirm the selected memory tool is available in the agent harness before relying on cross-session recall",
        ],
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
        "setup": [
            "Install Hamilton in the project environment when DAG visualization or fingerprints are needed",
        ],
        "verify": [
            "python -c \"import hamilton; print(hamilton.__version__)\"",
        ],
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
        "setup": [
            "Install or configure the chosen sandbox tool outside repo-familiar before running untrusted commands",
        ],
        "verify": [
            "Run the sandbox tool's help/status command before using it for package installs or generated code",
        ],
        "guidance": [
            "Default to no network for generated or unknown code",
            "Allow writes only to explicit build, temp, or output directories",
            "Use snapshots or restore behavior for risky package or codegen commands",
        ],
    },
    "sandbox-agent-runtime": {
        "tool": "OpenShell",
        "purpose": "policy-governed runtime for longer autonomous agent sessions",
        "setup": [
            "Configure OpenShell policies outside the repository before using this profile for autonomous sessions",
        ],
        "verify": [
            "Run the OpenShell policy validation or status command for the target workspace",
        ],
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
        "setup": [
            "Commit .env.example with placeholders and keep real .env files ignored",
            "Use the framework-native dotenv loader or add a development-only loader explicitly",
        ],
        "verify": [
            "Confirm .env is ignored and .env.example contains no real secret values",
        ],
        "guidance": [
            "Commit .env.example with placeholder names and non-secret defaults only",
            "Ignore .env, .env.*, and local override files except .env.example",
            "Load dotenv files explicitly in development entrypoints or via framework-native dotenv support",
        ],
    },
    "kvenv-azure-keyvault": {
        "tool": "kvenv",
        "purpose": "use Azure Key Vault references in dotenv files so agents see references, not secret values",
        "setup": [
            "Install kvenv outside the repository and authenticate with Azure CLI",
            "Use kv:// references in dotenv files instead of literal secrets",
        ],
        "verify": [
            "kvenv --help",
            "Run one non-production command through kvenv to confirm references resolve",
        ],
        "guidance": [
            "Use kv:// references in .env files instead of literal secrets",
            "Authenticate with Azure CLI outside the repository",
            "Run commands through kvenv so real values are fetched at process start",
        ],
    },
    "onepassword-op": {
        "tool": "1Password CLI op run",
        "purpose": "inject local or team-managed secrets into process environments without writing them to repo files",
        "setup": [
            "Install the 1Password CLI and sign in outside the repository",
            "Store secrets in 1Password and commit only references or placeholders",
        ],
        "verify": [
            "op --version",
            "op whoami",
        ],
        "guidance": [
            "Store secrets in 1Password and commit only reference placeholders or .env.example",
            "Run local commands through op run or op inject when secret values are needed",
            "Keep 1Password item names and vault naming conventions documented without exposing secret values",
        ],
    },
    "sops-age": {
        "tool": "sops with age",
        "purpose": "encrypt selected repository config or secret files while keeping plaintext out of git",
        "setup": [
            "Install sops and age outside the repository",
            "Create or obtain an age recipient outside the repository",
            "Commit .sops.yaml only with public recipients and path rules",
        ],
        "verify": [
            "sops --version",
            "age --version",
            "sops -d path/to/encrypted-file",
        ],
        "guidance": [
            "Use SOPS for files that must be committed encrypted, not for broad plaintext .env storage",
            "Prefer age recipients for simple local or team key management",
            "Keep age private keys outside the repository",
            "Never commit decrypted secret files or generated plaintext",
            "Keep .sops.yaml rules narrow so only intended files are encrypted",
        ],
    },
}

DESIGN_PROFILES = {
    "design-impeccable": {
        "tool": "impeccable",
        "purpose": "shared design vocabulary and anti-pattern checks for frontend or published docs work",
        "setup": [
            "Install the optional Impeccable skill with `npx skills add pbakaus/impeccable` when the agent harness supports skills",
            "Install the optional CLI with npm/npx when deterministic checks are useful",
            "If Impeccable is installed, periodically run `npx impeccable skills update` to refresh the local skill bundle",
        ],
        "verify": [
            "npx impeccable --help",
            "Confirm the Impeccable skill appears in the target agent harness when installed",
        ],
        "guidance": [
            "Use design critique before polishing UI or documentation sites",
            "Use `npx impeccable detect <path-or-url>` when deterministic design anti-pattern checks are useful",
            "Avoid generic AI frontend defaults and overused visual patterns",
            "Keep project design guidance in repository docs such as DESIGN.md when adopted",
        ],
    },
    "design-a11y": {
        "tool": "axe-core, pa11y, Lighthouse, Playwright, or equivalent accessibility scanners",
        "purpose": "accessibility-first design checks for user-facing web outputs",
        "setup": [
            "Use existing project accessibility tooling when present",
            "For Node projects, install @axe-core/playwright, pa11y, or Lighthouse as project-local dev dependencies when needed",
        ],
        "verify": [
            "Run one accessibility scan against a local rendered page before release handoff",
        ],
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

PUBLIC_INTEREST_PROFILES = {
    "child-rights-digital": {
        "tool": "child rights, safeguarding, inclusive design, and public-interest technology review",
        "purpose": "guide child-facing digital work toward safety, dignity, inclusion, accountability, and maintainability",
        "setup": [
            "Identify applicable child-safeguarding, privacy, accessibility, and localization review requirements before implementation",
        ],
        "verify": [
            "Document child-rights, safeguarding, privacy, and escalation assumptions before production maintenance",
        ],
        "guidance": [
            "Treat child safety, dignity, agency, and safeguarding as first-order design constraints",
            "Prefer data minimization, clear consent, limited retention, and safe escalation paths",
            "Design for low-connectivity, low-end devices, shared devices, assistive technology, and varied literacy or language contexts",
            "Avoid dark patterns, manipulative engagement mechanics, unnecessary profiling, and surveillance-like defaults",
            "Plan for localization, right-to-left layouts, culturally appropriate content, and handover to local partners or public institutions",
        ],
    },
    "public-interest-digital": {
        "tool": "public-interest digital delivery review",
        "purpose": "keep civic, humanitarian, education, and public-sector digital services transparent, inclusive, resilient, and maintainable",
        "setup": [
            "Identify public-sector, partner-handover, localization, accessibility, and low-connectivity constraints before implementation",
        ],
        "verify": [
            "Document operational ownership, handover assumptions, and support paths before production maintenance",
        ],
        "guidance": [
            "Prefer boring, well-supported technology that local teams can inherit and operate",
            "Make data collection, automation, AI use, and recommendation logic legible to users where relevant",
            "Treat poor connectivity, old devices, shared access, translation, accessibility, and support pathways as normal operating conditions",
            "Document operational assumptions, ownership, monitoring, and handover paths before production maintenance",
        ],
    },
}

SKILLS = {
    "a11y-web-scan": "Plan and run accessibility scans for user-facing web outputs",
    "caveman": "Use ultra-compressed communication when brevity is explicitly requested",
    "cq": "Query the knowledge commons before implementation work and error fixes",
    "diagnose": "Diagnose hard bugs and performance regressions with a disciplined loop",
    "get-api-docs": "Fetch current third-party API, SDK, and library documentation before integration work",
    "git-guardrails-claude-code": "Set up Claude Code hooks to block dangerous git commands",
    "grill-me": "Stress-test a plan or design through focused questioning",
    "grill-with-docs": "Stress-test plans against project language and documented decisions",
    "improve-codebase-architecture": "Find architecture refactoring opportunities informed by domain docs",
    "liteparse": "Parse local unstructured documents with LiteParse",
    "migrate-to-shoehorn": "Migrate tests from type assertions to @total-typescript/shoehorn",
    "playwright-cli": "Use Playwright CLI for browser inspection, screenshots, console errors, and web interaction checks",
    "privacy-review": "Review data flows, prompts, logs, memory, and outputs for privacy risks",
    "prompt-migration": "Migrate prompt DAGs across model versions safely",
    "prompt-eval-design": "Design lightweight evals for prompt DAGs and model-version migrations",
    "prompt-output-safety": "Review prompts and outputs for unsafe or policy-sensitive behavior",
    "prototype": "Build throwaway prototypes to flush out design questions",
    "qa-test-design": "Design meaningful tests before writing implementation or test code",
    "rodney-browser": "Use Rodney for persistent Chrome automation, shell-scripted web checks, and accessibility tree queries",
    "scaffold-exercises": "Create exercise directory structures and stubs",
    "security-audit": "Review code, dependencies, secrets, and auth patterns for security risks",
    "session-focus": "Prevent goal drift during multi-step agent tasks",
    "setup-matt-pocock-skills": "Set up agent skill context and issue-tracker documentation",
    "setup-pre-commit": "Set up Husky pre-commit hooks with formatting, type checks, and tests",
    "tdd": "Use red-green-refactor test-driven development",
    "to-issues": "Break a plan into independently grabbable implementation issues",
    "to-prd": "Turn conversation context into a product requirements document",
    "triage": "Triage issues through a role-driven state machine",
    "upstream-improvement": "Prepare safe upstream improvement proposals from downstream generated asset changes",
    "write-a-skill": "Create new agent skills with proper structure and progressive disclosure",
    "zoom-out": "Give broader context and explain how a code area fits the system",
}

SKILL_SOURCES = {
    "a11y-web-scan": {
        "source_type": "local",
        "source_url": "local:repo-familiar",
        "notes": "Authored for repo-familiar accessibility scanning guidance.",
    },
    "caveman": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/productivity/caveman/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "cq": {
        "source_type": "external",
        "source_url": "https://github.com/mozilla-ai/cq/blob/main/plugins/cq/skills/cq/SKILL.md",
        "notes": "Adapted for repo-familiar selectable skill guidance.",
    },
    "diagnose": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "get-api-docs": {
        "source_type": "external",
        "source_url": "https://github.com/andrewyng/context-hub/blob/main/cli/skills/get-api-docs/SKILL.md",
        "notes": "Adapted from Context Hub get-api-docs skill for repo-familiar selectable skill guidance.",
    },
    "git-guardrails-claude-code": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "grill-me": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "grill-with-docs": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md",
        "notes": "Adapted from mattpocock/skills for repo-familiar documentation and planning workflows.",
    },
    "improve-codebase-architecture": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "liteparse": {
        "source_type": "external",
        "source_url": "https://github.com/run-llama/llamaparse-agent-skills/blob/main/skills/liteparse/SKILL.md",
        "notes": "Adapted from run-llama/llamaparse-agent-skills for local document parsing guidance.",
        "setup": [
            "Install the upstream skill with `npx skills add run-llama/llamaparse-agent-skills --skill liteparse` when the agent harness supports skills",
            "Install the LiteParse CLI with `npm i -g @llamaindex/liteparse` when local parsing is needed",
            "Install LibreOffice for Office documents and ImageMagick for image parsing when those formats are needed",
        ],
        "verify": [
            "lit --version",
            "Confirm `.agents/skills/liteparse/SKILL.md` exists after generation or bootstrap",
        ],
    },
    "migrate-to-shoehorn": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/misc/migrate-to-shoehorn/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "playwright-cli": {
        "source_type": "external",
        "source_url": "https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/SKILL.md",
        "notes": "Adapted from Microsoft playwright-cli skill for repo-familiar browser automation guidance.",
    },
    "privacy-review": {
        "source_type": "local",
        "source_url": "local:repo-familiar",
        "notes": "Authored for repo-familiar privacy review workflows.",
    },
    "prompt-migration": {
        "source_type": "local",
        "source_url": "local:repo-familiar",
        "notes": "Authored for repo-familiar prompt migration workflows.",
    },
    "prompt-eval-design": {
        "source_type": "local",
        "source_url": "local:repo-familiar",
        "notes": "Authored for repo-familiar prompt evaluation design workflows.",
    },
    "prompt-output-safety": {
        "source_type": "local",
        "source_url": "local:repo-familiar",
        "notes": "Authored for repo-familiar prompt and output safety reviews.",
    },
    "prototype": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "qa-test-design": {
        "source_type": "external",
        "source_url": "https://github.com/omega-memory/omega-skills/blob/main/skills/qa-test-design/SKILL.md",
        "notes": "Adapted from omega-memory/omega-skills.",
    },
    "rodney-browser": {
        "source_type": "local-adapted",
        "source_url": "https://github.com/simonw/rodney",
        "notes": "Authored in repo-familiar around Rodney browser automation guidance.",
    },
    "scaffold-exercises": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "security-audit": {
        "source_type": "external",
        "source_url": "https://github.com/omega-memory/omega-skills/blob/main/skills/security-audit/SKILL.md",
        "notes": "Adapted from omega-memory/omega-skills.",
    },
    "session-focus": {
        "source_type": "external",
        "source_url": "https://github.com/omega-memory/omega-skills/blob/main/skills/session-focus/SKILL.md",
        "notes": "Adapted from omega-memory/omega-skills.",
    },
    "setup-matt-pocock-skills": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "setup-pre-commit": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/misc/setup-pre-commit/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "tdd": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "to-issues": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "to-prd": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "triage": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "upstream-improvement": {
        "source_type": "local",
        "source_url": "local:repo-familiar",
        "notes": "Authored for repo-familiar upstream contribution workflows.",
    },
    "write-a-skill": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/productivity/write-a-skill/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
    "zoom-out": {
        "source_type": "external",
        "source_url": "https://github.com/mattpocock/skills/blob/main/skills/engineering/zoom-out/SKILL.md",
        "notes": "Adapted from mattpocock/skills.",
    },
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
    _validate("public interest profile", selections.get("public_interest_profiles", ()), PUBLIC_INTEREST_PROFILES)
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
        _append_optional_list(lines, profile, "setup", indent="    ")
        _append_optional_list(lines, profile, "verify", indent="    ")
    return "\n".join(lines)


def render_opencode_config(tool_profile_names: tuple[str, ...]) -> str:
    config = {
        "$schema": "https://opencode.ai/config.json",
        "skills": {"paths": [".agents/skills"]},
    }
    mcp: dict[str, dict] = {}
    if "opencode-playwright-mcp" in tool_profile_names:
        mcp["playwright"] = {
            "type": "local",
            "command": ["npx", "-y", "@playwright/mcp"],
            "enabled": True,
        }
    if "opencode-cq-mcp" in tool_profile_names:
        mcp["cq"] = {
            "type": "local",
            "command": ["cq", "mcp"],
            "enabled": True,
        }
    if "opencode-context7-mcp" in tool_profile_names:
        mcp["context7"] = {
            "type": "remote",
            "url": "https://mcp.context7.com/mcp",
            "enabled": True,
            "headers": {"CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"},
        }
    if mcp:
        config["mcp"] = mcp
    return json.dumps(config, indent=2) + "\n"


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
        _append_optional_list(lines, profile, "setup", indent="    ")
        _append_optional_list(lines, profile, "verify", indent="    ")
    return "\n".join(lines) if lines else "  {}"


def render_skill_sources(skill_names: tuple[str, ...]) -> str:
    lines: list[str] = []
    for name in skill_names:
        source = SKILL_SOURCES[name]
        lines.append(f"  {name}:")
        lines.append(f"    source_type: {_yaml_scalar(source['source_type'])}")
        lines.append(f"    source_url: {_yaml_scalar(source['source_url'])}")
        notes = source.get("notes")
        if notes:
            lines.append(f"    notes: {_yaml_scalar(notes)}")
        _append_optional_list(lines, {"setup": _skill_setup(name, source)}, "setup", indent="    ")
        _append_optional_list(lines, {"verify": _skill_verify(name, source)}, "verify", indent="    ")
    return "\n".join(lines) if lines else "  {}"


def _skill_setup(name: str, source: dict) -> list[str]:
    if "setup" in source:
        return source["setup"]
    source_url = source.get("source_url", "")
    if "mattpocock/skills" in source_url:
        return [
            f"Select with repo-familiar using `--skill {name}` when generating or bootstrapping a repository",
            "For source installs outside repo-familiar, run `npx skills@latest add mattpocock/skills`",
        ]
    if "omega-memory/omega-skills" in source_url:
        return [
            f"Select with repo-familiar using `--skill {name}` when generating or bootstrapping a repository",
            "For source installs outside repo-familiar, copy the matching skill from omega-memory/omega-skills",
        ]
    if "microsoft/playwright-cli" in source_url:
        return [
            "Install Playwright CLI with `npm install -g @playwright/cli@latest` or use `npx playwright-cli`",
        ]
    if "context-hub" in source_url:
        return [
            "Install chub with `npm install -g @aisuite/chub` if `chub --help` is unavailable",
        ]
    if "mozilla-ai/cq" in source_url:
        return [
            "Install and configure the cq MCP/server outside the repository following https://github.com/mozilla-ai/cq",
        ]
    if "simonw/rodney" in source_url:
        return [
            "Install or build Rodney from https://github.com/simonw/rodney when browser automation needs persistent Chrome state",
        ]
    return [f"Select with repo-familiar using `--skill {name}` when generating or bootstrapping a repository"]


def _skill_verify(name: str, source: dict) -> list[str]:
    if "verify" in source:
        return source["verify"]
    source_url = source.get("source_url", "")
    if "microsoft/playwright-cli" in source_url:
        return ["playwright-cli --help or npx playwright-cli --help"]
    if "context-hub" in source_url:
        return ["chub --help"]
    if "mozilla-ai/cq" in source_url:
        return ["Confirm cq MCP tools are available in the agent harness"]
    if "simonw/rodney" in source_url:
        return ["rodney --help"]
    return [f"Confirm `.agents/skills/{name}/SKILL.md` exists after generation or bootstrap"]


def _validate(label: str, values: tuple[str, ...], registry: dict) -> None:
    unknown = sorted(set(values) - set(registry))
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"Unknown {label}(s): {joined}")


def _yaml_list(values, *, indent: str) -> list[str]:
    return [f"{indent}- {_yaml_scalar(value)}" for value in values]


def _append_optional_list(lines: list[str], profile: dict, key: str, *, indent: str) -> None:
    values = profile.get(key, [])
    if values:
        lines.append(f"{indent}{key}:")
        lines.extend(_yaml_list(values, indent=f"{indent}  "))


def _yaml_scalar(value) -> str:
    return json.dumps(str(value))
