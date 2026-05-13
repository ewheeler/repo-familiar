# repo-familiar

`repo-familiar` is a project generator for downstream repositories, with this repository serving as the canonical reference source for my agentic engineering defaults.

The name is deliberately a little occult and a little practical: a familiar is the small helper spirit that follows you around, remembers your habits, and quietly makes the workbench feel like yours. This one just happens to live in repos, carry agent instructions instead of candles, and refuse to overwrite your files unless explicitly asked.

The repo is inspired by traditional dotfiles collections where developers keep their preferred setups and configurations like `.bashrc`, `.vimrc`, and shell aliases, but "dotfiles" is the metaphor rather than the implementation boundary. The center of gravity is repeatable project bootstrap: repository instructions, skills, project templates, model/provider preferences, documentation conventions, and setup flows for new work.

The generator should support both brand-new downstream repositories and existing repositories that want to adopt selected defaults. Existing repository bootstrap should be audit-first, dry-run friendly, and non-destructive by default.

## Goals

- Capture reusable agent-facing context in one place instead of rediscovering preferences project by project.
- Bootstrap new repositories with a coherent `.agents/` directory, `AGENTS.md`, starter skills, documentation, and project planning structure.
- Bootstrap existing repositories by adding selected tools, skills, model profiles, docs, and metadata without overwriting user-owned files by default.
- Make model and provider choices explicit so projects can be optimized for different harnesses, budgets, latency profiles, and coding styles.
- Keep human-readable and machine-readable project memory side by side through a Quarto documentation site.
- Encourage clean implementation architecture through opinionated defaults for Python packaging, configuration, logging, data modeling, DAGs, prompt templating, and file I/O.
- Avoid drifting into general workstation setup unless that setup directly supports downstream project generation.

## Repository Shape

This repository is expected to grow into four related layers:

- `skills/` or `.agents/skills/`: reusable agent skills copied into or installed for downstream projects.
- `templates/`: the primary product surface: project scaffolds, likely powered by Cookiecutter or a comparable templating tool.
- `docs/`: the Quarto documentation site for usage notes, architecture, design decisions, research notes, and user stories.
- `examples/`: reference projects that demonstrate complete setups for common stacks or model-provider choices.

The current checked-in skills are early seed material. The structure will be tightened as the bootstrap flow becomes concrete.

## Inspiration

This project draws from agentic engineering writing, skill ecosystems, and repository-instruction conventions:

- [Agentic engineering patterns](https://simonwillison.net/guides/agentic-engineering-patterns/)
- [How I use Claude Code](https://boristane.com/blog/how-i-use-claude-code/)
- [AI agent coding](https://minimaxir.com/2026/02/ai-agent-coding/)
- [How I write software with LLMs](https://www.stavros.io/posts/how-i-write-software-with-llms/)
- [Agent-Agnostic Repository Guide](https://gist.github.com/davidgibsonp/337be9b80b3f03eccd188235c287bb05)
- [How to write good AGENTS.md files](https://www.augmentcode.com/blog/how-to-write-good-agents-dot-md-files)
- [mattpocock/skills](https://github.com/mattpocock/skills)
- [superpowers](https://github.com/obra/superpowers)
- [unicef/design.md](https://github.com/unicef/design.md)
- [impeccable.style](https://impeccable.style/)

## New Project Bootstrap

The intended workflow for starting a new repository is:

1. Create a project from a template.
2. Answer `questionary` interactive setup prompts or pass equivalent CLI flags for project type, agent harnesses, model providers, documentation depth, and preferred libraries.
3. Generate repository instructions and starter agent assets.
4. Generate a project plan and Quarto documentation skeleton.
5. Run a docs-review skill to challenge the plan before implementation begins.

The current generator can be run from this checkout with:

```bash
uv sync
uv run python -m repo_familiar list-templates
uv run python -m repo_familiar list-model-profiles
uv run python -m repo_familiar list-tool-profiles
uv run python -m repo_familiar list-memory-profiles
uv run python -m repo_familiar list-sandbox-profiles
uv run python -m repo_familiar list-secrets-profiles
uv run python -m repo_familiar list-design-profiles
uv run python -m repo_familiar list-worktree-profiles
uv run python -m repo_familiar list-skills
uv run python -m repo_familiar advise --path /path/to/existing-repo
uv run python -m repo_familiar check --path /path/to/generated-project
```

Preview generated assets without writing files:

```bash
uv run python -m repo_familiar generate \
  --name "Demo Project" \
  --description "A generated demo." \
  --output /path/to/demo-project \
  --agent-harness opencode \
  --model-profile default-coding \
  --tool-profile cq \
  --memory-profile memory-local \
  --secrets-profile dotenv-local \
  --secrets-profile kvenv-azure-keyvault \
  --sandbox-profile sandbox-light \
  --design-profile design-impeccable \
  --worktree-profile parallel-worktrees \
  --skill cq \
  --skill grill-with-docs \
  --dry-run
```

Generate a downstream repository:

```bash
uv run python -m repo_familiar generate \
  --name "Demo Project" \
  --description "A generated demo." \
  --output /path/to/demo-project \
  --agent-harness opencode \
  --model-profile default-coding \
  --tool-profile cq \
  --memory-profile memory-local \
  --skill cq \
  --skill grill-with-docs
```

Generate a downstream repository interactively:

```bash
uv sync
uv run python -m repo_familiar generate --interactive
```

`questionary` is imported lazily for interactive commands and installed by `uv sync`.

This first skeleton uses `questionary` for optional interaction and keeps template rendering on `string.Template`. It writes `.gitignore`, `.env.example`, `README.md`, `AGENTS.md`, `.agents/models.yml`, `.agents/tools.yml`, `.agents/memory.yml`, `.agents/sandbox.yml`, `.agents/secrets.yml`, `.agents/design.yml`, `.agents/worktrees.yml`, `.agents/skill-sources.yml`, selected skills, a Quarto docs scaffold, `plan.md`, and `.repo-familiar/bootstrap.yml`. Banks should be introduced later when prompt or project templates outgrow `string.Template`; Cookiecutter can remain a future option if the project-generation contract needs it.

Generated repositories should receive vendored copies of the selected assets by default. Each generated repository should also include `.repo-familiar/bootstrap.yml`, recording the `repo-familiar` source and version used to create it. Live synchronization can come later as an explicit upgrade command, but initial bootstraps should be stable and self-contained.

The first bootstrap metadata schema should stay small:

```yaml
schema_version: 1
reference_source:
  type: git
  url: https://github.com/<owner>/repo-familiar
  ref: <tag-or-commit>
generated_at: <iso-8601 timestamp>
generator:
  name: repo-familiar
  version: <version-or-commit>
selected_options:
  template: <template-name>
  agent_harnesses: []
  model_profiles: []
  tool_profiles: []
  memory_profiles: []
  sandbox_profiles: []
  secrets_profiles: []
  design_profiles: []
  worktree_profiles: []
  skills: []
  docs: quarto
generated_assets:
  - path: .gitignore
    kind: template_config
    source: templates/basic/.gitignore.tmpl
  - path: README.md
    kind: documentation
    source: templates/basic/README.md.tmpl
  - path: AGENTS.md
    kind: agent_instructions
    source: templates/basic/AGENTS.md.tmpl
  - path: .agents/models.yml
    kind: template_config
    source: templates/basic/.agents/models.yml.tmpl
  - path: .agents/tools.yml
    kind: template_config
    source: templates/basic/.agents/tools.yml.tmpl
  - path: .agents/skills/grill-with-docs/SKILL.md
    kind: skill
    source: templates/skills/grill-with-docs/SKILL.md.tmpl
    content_sha256: <sha256>
  - path: .agents/skill-sources.yml
    kind: template_config
    source: templates/basic/.agents/skill-sources.yml.tmpl
    content_sha256: <sha256>
  - path: docs/_quarto.yml
    kind: documentation
    source: templates/basic/docs/_quarto.yml.tmpl
    content_sha256: <sha256>
```

`content_sha256` is omitted for `.repo-familiar/bootstrap.yml` itself to avoid self-referential hashing.

The initial `generated_assets[].kind` vocabulary is intentionally small: `agent_instructions`, `skill`, `documentation`, `template_config`, `project_plan`, and `metadata`.

Model/provider profiles should be generated into `.agents/models.yml` for agent-facing runtime defaults. `.repo-familiar/bootstrap.yml` should record only the selected profile names under `selected_options.model_profiles`. Do not store provider secrets in either file.

Tool profiles should be generated into `.agents/tools.yml` as non-secret repository guidance. `.repo-familiar/bootstrap.yml` records selected tool profile names under `selected_options.tool_profiles`.

Memory, sandbox, design, and worktree profiles are advisory profile families. They generate `.agents/memory.yml`, `.agents/sandbox.yml`, `.agents/design.yml`, and `.agents/worktrees.yml` and record selected names in `.repo-familiar/bootstrap.yml`.

Secrets profiles are also advisory. They generate `.agents/secrets.yml` and `.env.example`, ignore real local env files, and record selected profile names without storing secret values.

The first `.agents/models.yml` schema should use profile names as stable handles and avoid over-normalizing provider metadata:

```yaml
profiles:
  default-coding:
    provider: openai
    model: gpt-5.5
    use: general coding and repository maintenance
    harnesses:
      - opencode
    notes:
      latency: medium
      cost: high
      strengths:
        - codebase editing
        - documentation
```

The first template should probably ask for:

- Project name, description, license, and visibility.
- Primary language and runtime.
- Agent harnesses to support: OpenCode, Conductor, Hermes, Pi, or others.
- Model/provider targets and defaults to include in `.agents/models.yml`.
- Documentation mode: lightweight notes, full Quarto site, or publishable site.
- Python stack preferences: `uv`, Hamilton, Banks, Hydra/OmegaConf, Structlog, fsspec/universal-pathlib, Polars, and Pydantic.
- Whether to include design-system guidance such as `DESIGN.md` conventions or additional visual tooling.

## Existing Project Bootstrap

Existing repositories should be handled through a separate audit-first flow:

1. Run `advise` to recommend stage, profiles, tools, and memory usage.
2. Inspect the repository for existing agent instructions, skills, docs, model profiles, and bootstrap metadata.
3. Report missing assets, compatible existing assets, and conflicts.
4. Preview additive changes with a dry run.
5. Apply selected tools, skills, model profiles, docs, and metadata only when requested.
6. Avoid overwriting user-owned files unless an explicit replacement mode is selected.

Candidate future commands:

```bash
uv run python -m repo_familiar advise --path /path/to/repo
uv run python -m repo_familiar advise --path /path/to/repo --format json
uv run python -m repo_familiar audit --path /path/to/repo
uv run python -m repo_familiar audit --path /path/to/repo --format json
uv run python -m repo_familiar audit --path /path/to/repo --asset-group docs
uv run python -m repo_familiar bootstrap-existing --path /path/to/repo
uv run python -m repo_familiar bootstrap-existing --path /path/to/repo --apply
uv run python -m repo_familiar diff-upstream-candidate --path /path/to/repo
uv run python -m repo_familiar upgrade --path /path/to/repo
uv run python -m repo_familiar add-model --path /path/to/repo --model-profile default-coding --apply
uv run python -m repo_familiar add-docs --path /path/to/repo --apply
uv run python -m repo_familiar add-skill --path /path/to/repo --skill cq --apply
uv run python -m repo_familiar add-skill --path /path/to/repo --skill grill-with-docs --apply
uv run python -m repo_familiar add-skill --path /path/to/repo --skill get-api-docs --apply
uv run python -m repo_familiar add-skill --path /path/to/repo --skill upstream-improvement --apply
uv run python -m repo_familiar add-tool --path /path/to/repo --tool cq --apply
uv run python -m repo_familiar add-tool --path /path/to/repo --tool opencode-homebrew-path --apply
uv run python -m repo_familiar add-memory --path /path/to/repo --memory-profile memory-local --apply
uv run python -m repo_familiar add-sandbox --path /path/to/repo --sandbox-profile sandbox-light --apply
uv run python -m repo_familiar add-secrets --path /path/to/repo --secrets-profile kvenv-azure-keyvault --apply
uv run python -m repo_familiar add-design --path /path/to/repo --design-profile design-impeccable --apply
uv run python -m repo_familiar add-worktree --path /path/to/repo --worktree-profile parallel-worktrees --apply
```

Existing bootstrap metadata uses `bootstrap_mode: existing_repository` and records only assets written by the operation. Conflicts skipped for safety are reported but not claimed as generated assets.

Granular bootstrap can use `--asset-group` with `agent`, `config`, `docs`, `metadata`, `models`, `plan`, `skills`, or `tools`. The `skills` group includes selected skill files and `.agents/skill-sources.yml` provenance for future upstream drift checks.

Use `check` to detect missing or modified generated assets from checksum metadata:

```bash
uv run python -m repo_familiar check --path /path/to/repo --format json
```

Use `diff-upstream-candidate` to classify generated asset changes before proposing reusable improvements back to this Reference Source. Pair it with the `upstream-improvement` skill so private details and local-only changes are filtered before any upstream PR is drafted.

Use `upgrade` as a read-only readiness preview before any future write-capable upgrade. It reports user-review items, blockers, and unavailable update candidates without changing files.

Memory should be used at session start to recall project decisions and repeated issues, after resolving non-obvious problems, after accepting ADRs, and when advancing stages. Repository docs and bootstrap metadata remain the canonical record; memory accelerates recall rather than replacing committed context.

For local secrets, prefer one of these approaches:

- `kvenv-azure-keyvault`: commit `.env` files with `kv://` references only, then run commands through `kvenv` so real values are fetched from Azure Key Vault.
- `onepassword-op`: store values in 1Password and run commands with `op run` or `op inject`.
- `dotenv-local`: keep `.env.example` committed and `.env` ignored; use this only for non-shared local development values or when paired with a secure local secret store.

For user-facing web outputs, include browser automation and accessibility scanning in the design loop. Use the `browser-automation` tool profile to allow rendered-page inspection, screenshots, console checks, and interaction smoke tests. Use `playwright-cli` for agent-friendly browser sessions, or `rodney-browser` when persistent Chrome state, shell-scripted assertions, or accessibility tree queries are useful.

Use the `a11y-scanner` tool profile and `a11y-web-scan` skill to run Pa11y, axe-core, Lighthouse, Playwright, or Rodney accessibility checks against rendered pages before design polish or release.

ADT Studio's accessibility tooling is a good reporting model: summarize selected pages, rule deltas, top violations, and the browser recheck split between confirmed issues, resolved incomplete items, and residual manual-review items.

For prompt-heavy repositories, especially Hamilton or prompt DAGs authored against an earlier model, use `prompt-migration-gpt55` and `prompt-evals-dag` before rewriting prompts. Capture fixtures at meaningful DAG node boundaries, then migrate prompts with minimal diffs and measurable behavior deltas. Use `hamilton-dag` as the preferred repo-map profile where Hamilton is already part of the project.

For policy, education, children, or other sensitive user-facing AI outputs, add `prompt-output-safety` and `data-privacy-review` before production-maintenance work.

For broad agent discipline, add `session-focus` before long multi-step work, `qa-test-design` before designing test coverage, and `security-audit` before shipping code that touches auth, secrets, dependencies, or user-facing surfaces.

Skill provenance for selected skills is recorded in `.agents/skill-sources.yml`. It distinguishes local skills, adapted local skills, imported-local skills with unknown upstreams, and external skills such as `cq`, `mattpocock/skills`, Context Hub, and selected `omega-memory/omega-skills` imports. Any skill dogfooded in this Reference Source is also a selectable downstream skill, so future upgrade or drift commands can compare all vendored skills against upstream sources from one manifest.

## Agent-Agnostic Defaults

Downstream repositories should be able to use these assets without binding themselves to a single coding agent. A generated project should include:

- `.agents/` for shared agent instructions and skills.
- `.agents/skill-sources.yml` for selected skill provenance and future upstream drift checks.
- `AGENTS.md` for repository-level working rules.
- `.agents/tools.yml` for non-secret tool profile guidance.
- Optional harness-specific adapters when a tool requires a different file location or naming convention.
- A project plan that records technical preferences, boundaries, and first implementation milestones.
- `.repo-familiar/bootstrap.yml` metadata that records the `repo-familiar` reference source and version used for generation.

Useful reference: [Agent-Agnostic Repository Guide](https://gist.github.com/davidgibsonp/337be9b80b3f03eccd188235c287bb05).

## Documentation Philosophy

Each serious project should maintain documentation in parallel with implementation. The documentation should record:

- Usage instructions.
- Architecture and design decisions.
- Research notes and external references.
- User stories and acceptance criteria.
- Implementation plans and review notes.
- Model/provider assumptions and tradeoffs.

Quarto is the default documentation engine because it keeps prose, diagrams, executable notes, and static publishing close together. It also gives agents a consistent place to inspect intent before changing code.

## Preferred Engineering Stack

For Python-heavy projects, this repository will encode these defaults unless a project has a better reason not to use them:

- `uv` for Python package and environment management.
- Hamilton for explicit dataflow/DAG definitions and reviewable execution graphs.
- Banks for prompt templating.
- Hydra and OmegaConf for structured configuration.
- Structlog for structured logs.
- fsspec and universal-pathlib for flexible file I/O.
- Polars for dataframe work.
- Pydantic for typed data structures and validation.

Hamilton is especially important because DAG visualizations make abstraction boundaries, data dependencies, and execution flow inspectable without reading every line of code.

## Skill Sources

Candidate skill sources and adjacent tooling:

- `npx skills@latest add mattpocock/skills`
- [superpowers](https://github.com/obra/superpowers)
- [unicef/design.md](https://github.com/unicef/design.md)
- [impeccable.style](https://impeccable.style/)

Planned local setup work includes installing and enabling MCPs such as `cq`, then documenting which projects should inherit them.

## Near-Term Roadmap

- Expand the `questionary` interactive setup flow based on real bootstraps.
- Keep `string.Template` until prompt or project templates need Banks or a broader generator framework.
- Add more model profiles and harness-specific adapters.
- Add selected skill vendoring.
- Design explicit upgrade behavior.
