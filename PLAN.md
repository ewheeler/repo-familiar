# repo-familiar Plan

`repo-familiar` is a project generator for downstream repositories, with this repository serving as the canonical reference source for reusable agentic engineering defaults.

## Current Status

- The product boundary is defined: generate downstream repositories, not workstation dotfiles.
- Generated repositories receive vendored assets by default.
- Generator provenance is recorded in `.repo-familiar/bootstrap.yml`.
- Agent-facing model profiles live in `.agents/models.yml`.
- The Quarto documentation site is scaffolded and renders with `/usr/local/bin/quarto render docs` from the repository root, or `/usr/local/bin/quarto render .` from `docs/`.
- A minimal Python generator exists under `src/repo_familiar`, with `questionary` for optional interaction and `string.Template` for rendering.
- Python package management and documented CLI invocation are uv-first: run `uv sync` and `uv run python -m repo_familiar ...`.
- The generator supports list commands for templates, profiles, and skills; `generate --dry-run`; `generate --interactive`; non-empty output directory protection; `advise`; `audit`; `check`; `bootstrap-existing --interactive`; and targeted existing-repo add commands.
- The `basic` template generates `.gitignore`, `.env.example`, `README.md`, `AGENTS.md`, `.agents/*.yml` advisory/runtime files, selected skills, Quarto docs, `plan.md`, and `.repo-familiar/bootstrap.yml`.
- Existing repository bootstrap can audit, dry-run, and apply missing selected assets without overwriting conflicts by default.
- Existing repository metadata records `bootstrap_mode: existing_repository` and only assets written by that operation.
- Targeted add commands reuse the bootstrap engine with narrow asset groups and are table-driven in the CLI.
- `audit` and `bootstrap-existing` support `--asset-group` for scoped adoption.
- `add-model` and `add-docs` provide targeted existing repository adoption flows.
- Generated asset metadata includes `content_sha256` for non-metadata assets.
- `check` detects missing and modified generated assets from `.repo-familiar/bootstrap.yml`.
- Advisory profile families exist for memory, sandboxing, design, and worktree orchestration.
- Secrets profiles exist for dotenv, kvenv/Azure Key Vault, and 1Password-style local secret injection guidance.
- Accessibility scanning support exists through `a11y-scanner`, `design-a11y`, and `a11y-web-scan`.
- Browser automation support exists through the `browser-automation` tool profile plus `playwright-cli` and `rodney-browser` skills.
- API documentation lookup support exists through the vendored `get-api-docs` skill.
- OpenCode/Homebrew PATH setup guidance exists through the `opencode-homebrew-path` tool profile.
- Prompt migration/eval profiles exist for GPT-5.5 prompt migrations and prompt DAG eval design.
- Safety and privacy profiles exist for prompt/output safety and data/privacy review.
- Repo map profiles exist with `hamilton-dag` as the preferred graph approach.
- Advisory profile files are generated under `.agents/` and selected profile names are recorded in bootstrap metadata.
- `advise` recommends stage, profile families, asset groups, next commands, and memory usage for an existing repository.
- `advise` decision logic lives in `src/repo_familiar/advice_dag.py` as Hamilton-compatible nodes; command formatting helpers remain outside the DAG module.
- Core generator seams have been deepened: Bootstrap Metadata, profile registry, asset planning, repository advice orchestration, and targeted CLI add commands now live behind dedicated Modules or descriptor tables.
- `examples/basic-agentic-project` is a deterministic generated snapshot and regression fixture.
- Existing repository bootstrap is implemented as a second bootstrap mode: advise/audit first, dry-run by default, and additive unless explicit replacement is selected.

## Goals

- Make it easy to bootstrap a new repository with agent instructions, selected skills, model/provider profiles, planning artifacts, and Quarto documentation.
- Make it possible to add selected tools, skills, model profiles, docs, and metadata to existing repositories safely.
- Keep generated repositories self-contained and stable after creation.
- Preserve enough bootstrap metadata for future explicit upgrades without turning metadata into a dependency lockfile.
- Keep agent runtime assets separate from generator-owned metadata.
- Maintain documentation in parallel with implementation so humans and agents can inspect plans, decisions, research, and usage.

## Non-Goals

- Do not build a general workstation installer.
- Do not live-sync generated repositories back to this reference source.
- Do not store provider secrets in `.agents/models.yml` or `.repo-familiar/bootstrap.yml`.
- Do not over-normalize model/provider metadata before real templates need it.
- Do not make Quarto docs depend on rendering arbitrary root-level Markdown files.
- Do not force-migrate or take ownership of existing repository files during bootstrap.

## Resolved Decisions

- Primary product: project generator for downstream repositories.
- Reference source: this repository records canonical defaults, templates, skills, and documentation patterns.
- Delivery model: generated repositories receive vendored generated assets.
- Metadata path: `.repo-familiar/bootstrap.yml`.
- Bootstrap schema: `schema_version`, `reference_source`, `generated_at`, `generator`, `selected_options`, and structured `generated_assets`.
- Generated asset records: `path`, `kind`, and `source`.
- Initial generated asset kinds: `agent_instructions`, `skill`, `documentation`, `template_config`, `project_plan`, and `metadata`.
- Model profiles: `.agents/models.yml` contains non-secret runtime defaults; `.repo-familiar/bootstrap.yml` records selected profile names.
- Tool profiles: `.agents/tools.yml` contains non-secret tool guidance; `.repo-familiar/bootstrap.yml` records selected tool profile names.
- OpenCode/Homebrew setup remains Tool Profile guidance for agent shells only; it must not become workstation mutation or an installer.
- Skills: selected skills are vendored under `.agents/skills/` and recorded as `skill` assets.
- Renderer: keep `string.Template` until the template contract needs Banks, Cookiecutter, or another dedicated engine.
- Example policy: commit deterministic generated snapshots and compare them in tests.
- Existing repository bootstrap: support it as a distinct audit-first, additive workflow rather than overloading new repository generation.
- Existing bootstrap metadata ownership: record only assets actually written, not conflicts skipped for safety.
- Targeted adoption: support narrow asset groups so a skill or tool can be adopted without also adding full project scaffolding.
- Granular adoption: expose asset groups directly for audit and bootstrap workflows.
- Drift detection: record content checksums for generated non-metadata assets and expose a read-only `check` command.
- Advisory profile boundary: generate non-secret guidance files and selected profile names, not installers or machine-specific configuration.
- Secret profile boundary: generate `.agents/secrets.yml` and `.env.example`, but never generate or store secret values.
- Accessibility boundary: generate scanning guidance and skills, but treat automated scans as a baseline rather than full compliance proof.
- Accessibility reporting: prefer compact ADT-style summaries with rule deltas, top issues, and manual-review queues over raw scanner dumps.
- Prompt migration boundary: require fixtures or golden examples before prompt rewrites in existing prompt DAGs.
- Repo map boundary: prefer Hamilton DAG artifacts where Hamilton is already used, and avoid changing DAG fingerprints with helper functions.
- Safety/privacy boundary: provide review guidance and fixtures, not policy enforcement or secret-bearing config.
- Advice before bootstrap: run a read-only recommendation step before modifying existing repositories.
- Interaction: use `questionary` first for prompt-based flows; keep CLI flags fully supported.
- Template rendering: keep `string.Template` for now and introduce Banks later only when prompt or project templates outgrow it.
- Advice architecture: keep Hamilton DAG node logic separate from non-DAG helpers to protect future graph fingerprints.

## Best-Fit Additions

These are the suggested tool/component categories to dogfood in this Reference Source and offer to Downstream Repositories through generation, advice, or targeted existing-repo adoption.

| Category | Best-fit addition | repo-familiar representation | Adopt when |
|---|---|---|---|
| Python package management | `uv` | Project dependency workflow and documented command runner | Any Python repo generated or bootstrapped by this Reference Source. |
| Interactive CLI | `questionary` first; InquirerPy remains an alternative | Runtime dependency and `--interactive` flows | Users need prompt-based generation or existing repo bootstrap. |
| Advice decision graph | Hamilton-compatible node module | `src/repo_familiar/advice_dag.py` and `hamilton-dag` repomap profile | Advice rules need graphing, reviewability, or future visual artifacts. |
| Future template rendering | Banks later; keep `string.Template` for now | Deferred renderer decision | Prompt or project templates outgrow simple substitution. |
| Current API docs | `get-api-docs` skill with `chub` when available | Vendored skill and selectable skill template | Work touches third-party APIs, SDKs, CLIs, package managers, or fast-moving docs. |
| External skill source | `mattpocock/skills` | Vendored local skills plus documented install path | Engineering workflows need diagnose, TDD, triage, PRD, issue, architecture, or zoom-out support. |
| Agent knowledge commons | `cq` | Tool profile and agent instruction | Before implementation tasks or error fixes where stale/version-specific gotchas matter. |
| Browser automation | `browser-automation`, `playwright-cli`, `rodney-browser` | Tool profile plus selectable skills | Repos have frontend routes, Quarto/published docs, user-facing web outputs, browser smoke checks, screenshots, console-error checks, or accessibility tree checks. |
| OpenCode shell setup | `opencode-homebrew-path` | Tool profile | macOS Homebrew users need `node`, `npm`, `npx`, `pnpm`, `uv`, or `quarto` visible in OpenCode agent shells. |
| Memory | `memory-local` | `.agents/memory.yml` advisory profile | Any repo with recurring decisions, conventions, stage changes, or non-obvious debugging lessons. |
| Model defaults | `default-coding`, `budget-review` | `.agents/models.yml` model profiles | Repos need explicit model/provider defaults without storing credentials. |
| Prompt migration and evals | `prompt-migration-gpt55`, `prompt-evals-dag`, `prompt-migration`, `prompt-eval-design` | Prompt profiles and skills | Prompt DAGs, model migrations, or prompt-heavy pipelines exist. |
| Repo map and graphing | `hamilton-dag` | `.agents/repomap.yml` advisory profile | Python pipelines, prompt DAGs, dataflow, or graph fingerprints matter. |
| Safety review | `prompt-output-safety` profile and skill | `.agents/safety.yml` plus skill | User-facing AI, policy-sensitive, education, child-related, or high-impact outputs exist. |
| Privacy review | `data-privacy-review` profile and `privacy-review` skill | `.agents/privacy.yml` plus skill | Repos handle PII, child data, logs, analytics, memory, prompts, or exported artifacts. |
| Accessibility and design | `a11y-scanner`, `design-a11y`, `design-impeccable`, `a11y-web-scan` | Tool, design profiles, and skill | Frontend code, Quarto sites, design docs, or user-facing web outputs exist. Browser automation can support the manual/browser recheck portion. |
| Sandboxing | `sandbox-light`, optionally `sandbox-agent-runtime` | `.agents/sandbox.yml` advisory profile | Agents run generated code, package installs, unknown scripts, risky tests, or long autonomous sessions. |
| Secret handling | `dotenv-local`, `kvenv-azure-keyvault`, `onepassword-op` | `.agents/secrets.yml` and commented `.env.example` | Any repo needs local env guidance without committing real secret values. |
| Parallel work | `parallel-worktrees` | `.agents/worktrees.yml` advisory profile | Multiple agents, prototypes, or isolated services may run concurrently. |
| Documentation and planning | Quarto docs, `CONTEXT.md`, ADRs, `plan.md`, `grill-with-docs` | Generated docs, planning asset, and skill | Repos need durable project memory, domain language, or decision records. |
| Upstream contribution loop | `diff-upstream-candidate`, `upstream-improvement`, and future PR helper | Read-only diff command, skill, plus bootstrap metadata source fields | Downstream repos improve generated assets, profiles, skills, docs, or advice heuristics in ways that should flow back to this Reference Source. |

Default first-pass adoption for existing repos should remain narrow: memory, `grill-with-docs`, `get-api-docs`, and `opencode-homebrew-path`. Add the other categories only when `advise` or repo inspection shows a concrete trigger.

## Pre-Usage Priorities For Existing Repos

Priority 1: Use `advise` on representative repositories and compare recommendations against your intuition. Initial scans have already covered `project-review`, `model-decision-advice`, `ai-policy-kids-education`, `digital-playbook-quarto`, and `design.md`.

Priority 2: For the first real repo, apply only `add-memory`, `add-skill --skill grill-with-docs`, `add-skill --skill get-api-docs`, and `add-tool --tool opencode-homebrew-path` unless `advise` shows clear missing docs, prompt DAGs, model defaults, or user-facing web outputs.

Priority 3: Add docs with `add-docs` only after checking README/docs conflicts; avoid `--force` on first adoption.

Priority 4: For prompt DAG repos, add `prompt-migration-gpt55`, `prompt-evals-dag`, and `hamilton-dag` before rewriting prompts.

Priority 5: For policy, education, children, public-sector, or user-facing AI repos, add `prompt-output-safety` and `data-privacy-review` before production-maintenance work.

Priority 6: Add `sandbox-light` before letting agents run generated code, package installs, or unfamiliar scripts.

Priority 7: Run `check` after each bootstrap and capture any unexpected conflicts or drift as follow-up issues.

Priority 8: After the first 2-3 bootstraps, revisit whether stage progression needs `advance-stage` and bootstrap history fields.

First recommended real bootstrap sequence:

```bash
uv run python -m repo_familiar advise --path /path/to/repo
uv run python -m repo_familiar audit --path /path/to/repo
uv run python -m repo_familiar add-memory --path /path/to/repo --memory-profile memory-local --apply
uv run python -m repo_familiar add-skill --path /path/to/repo --skill grill-with-docs --apply
uv run python -m repo_familiar add-skill --path /path/to/repo --skill get-api-docs --apply
uv run python -m repo_familiar add-tool --path /path/to/repo --tool opencode-homebrew-path --apply
uv run python -m repo_familiar check --path /path/to/repo
```

## Implementation Milestones

### 1. Harden The Minimal Generator

Status: done for the current skeleton.

- Added CLI validation for existing non-empty output directories.
- Added `--dry-run` to preview generated files and metadata.
- Added `list-templates` and `list-model-profiles` commands.
- Added tests for overwrite behavior, unknown model profiles, dry runs, and multiple harness/profile selections.
- Chose path-sorted template traversal for deterministic generated asset ordering.

Acceptance criteria:

- `uv run python -m unittest discover -s tests` passes.
- A smoke-generated project contains all expected files and valid bootstrap metadata.
- The CLI gives actionable errors for invalid inputs.

### 2. Define The First Real Template Contract

Status: first interactive pass done with `questionary`; renderer remains `string.Template`.

- Keep the internal `string.Template` renderer until templates need Banks or a broader generator framework.
- Define the first interactive question set. Done for `generate --interactive` and `bootstrap-existing --interactive`.
- Split common assets from optional docs, model, and harness assets.
- Add a generated `.gitignore` template if needed. Done for `basic`.
- Add a generated project `README.md` template. Done for `basic`.

Acceptance criteria:

- The template contract can express optional Quarto docs, selected harnesses, selected model profiles, and selected skills.
- Generated metadata accurately records selected options and generated assets.
- Template files remain easy for agents to inspect and edit.

### 3. Expand Agentic Engineering Defaults

- Normalize local skill locations under `.agents/skills/` or another stable reference-source path.
- Add starter `AGENTS.md` content for downstream repositories.
- Add optional harness adapters for OpenCode, Conductor, Hermes, and Pi as their required conventions become clear.
- Add model profiles for coding, planning, review, low-cost passes, and high-context tasks.

Acceptance criteria:

- Generated agent instructions are agent-agnostic by default.
- Harness-specific files are generated only when selected.
- Model profile names are stable handles and contain no secrets.

### 4. Improve Documentation Site

- Add a generator usage page with end-to-end examples. Done.
- Add a templates page describing available templates and options. Done.
- Add a model profiles page documenting profile intent and harness compatibility. Done.
- Add an examples page describing generated snapshots. Done.
- Add an upgrade-design page once upgrade behavior becomes concrete.
- Keep Quarto render targets explicit in `docs/_quarto.yml`.

Acceptance criteria:

- `/usr/local/bin/quarto render .` passes from `docs/`.
- The site explains how to generate a downstream repository from this checkout.
- ADRs remain linked from the decisions page.

### 5. Add Example Generated Repositories

Status: done for the first snapshot.

- Generated a minimal example repository into `examples/basic-agentic-project`.
- Included Quarto docs and the default coding profile.
- Included multiple harnesses and multiple model profiles.
- Added a regression test that regenerates the example and compares file contents.

Acceptance criteria:

- Examples can be regenerated deterministically or clearly documented as snapshots.
- Example bootstrap metadata demonstrates the schema.
- Examples are useful as regression fixtures for the generator.

### 6. Design Explicit Upgrade Behavior

Status: read-only preview implemented; write-capable upgrades remain future work.

- Define what an upgrade command may update. Started with read-only readiness categories: `safe_to_auto_apply`, `needs_user_review`, `blocked`, and `unavailable`.
- Decide whether to add checksums or content fingerprints to `generated_assets`. Done with `content_sha256` for non-metadata assets.
- Decide how user-edited generated files are detected and handled. Started with checksum drift plus `modified` and `missing` blockers.
- Decide whether `.repo-familiar/manifest.yml` or `.repo-familiar/overrides.yml` is needed.

Acceptance criteria:

- Upgrade behavior is explicit and opt-in.
- User edits are never overwritten silently.
- Bootstrap metadata remains sufficient to reason about old generated repositories.
- Current `upgrade` command is read-only and writes no files.
- No safe auto-apply path is exposed until Bootstrap Metadata records enough template context for exact rendered comparisons.

### 8. Add Drift Detection

Status: done for current generated metadata.

- Add `content_sha256` to non-metadata generated asset records.
- Add `check` command to report `ok`, `modified`, `missing`, and `unchecked` assets.
- Add JSON output for scripted checks.

Acceptance criteria:

- `check` returns success when generated assets match recorded checksums.
- `check` returns non-zero when generated assets are missing or modified.
- Bootstrap metadata is not self-hashed.

### 9. Add Advisory Profile Families

Status: done for first profile set.

- Add `memory_profiles` and `.agents/memory.yml`.
- Add `sandbox_profiles` and `.agents/sandbox.yml`.
- Add `design_profiles` and `.agents/design.yml`.
- Add `worktree_profiles` and `.agents/worktrees.yml`.
- Add `secrets_profiles`, `.agents/secrets.yml`, and `.env.example`.
- Add list and targeted add commands for each profile family.

Acceptance criteria:

- Selected advisory profile names are recorded in `.repo-familiar/bootstrap.yml`.
- Advisory files contain no secrets and do not install tools.
- Existing repository bootstrap can add each advisory profile family independently.

### 10. Add Repository Advice

Status: done for first Hamilton-compatible heuristic pass; orchestration is extracted to `advice.py` while `advice_dag.py` stays pure.

- Add `advise` command for existing repositories.
- Detect coarse repository signals such as docs, tests, CI, Quarto, frontend files, container config, agent instructions, and bootstrap metadata.
- Recommend stage, asset groups, model/tool/advisory profiles, skills, next commands, and memory use.
- Move decision nodes to `advice_dag.py` so the logic can be run or visualized as a Hamilton graph later.

Acceptance criteria:

- Advice is read-only and supports JSON output.
- Advice includes when/how to use memory tools.
- Advice gives a clear first command to run before bootstrap.

### 11. Add Accessibility Scanning Support

Status: done for first advisory pass.

- Add `a11y-scanner` tool profile.
- Add `design-a11y` advisory design profile.
- Add `a11y-web-scan` skill.
- Update `advise` so frontend, Quarto, and design-doc repositories recommend accessibility scanning.
- Adapt the ADT Studio reporting pattern: selected targets, rule count deltas, top violations, browser recheck, and residual manual-review queue.

Acceptance criteria:

- Accessibility support is opt-in and advisory.
- Generated guidance recommends automated and manual checks.
- No Node dependencies are installed by default.
- Accessibility reports should lead with concrete remediation priorities.

### 12. Add Prompt Migration, Safety, Privacy, And Repo Maps

Status: done for first advisory pass.

- Add `prompt_profiles` and `.agents/prompts.yml`.
- Add `safety_profiles` and `.agents/safety.yml`.
- Add `privacy_profiles` and `.agents/privacy.yml`.
- Add `repomap_profiles` and `.agents/repomap.yml`.
- Add `prompt-migration`, `prompt-eval-design`, `prompt-output-safety`, and `privacy-review` skills.
- Recommend prompt/safety/privacy/repomap profiles from `advise` when prompt DAGs, policy/education repos, frontend outputs, or Python projects are detected.

Acceptance criteria:

- Prompt migrations start with inventory and eval fixtures before rewrites.
- Prompt DAG review can use Hamilton DAGs and fingerprints where appropriate.
- Safety and privacy reviews include prompt, output, logging, memory, cache, and export exposure points.

### 7. Add Existing Repository Bootstrap

Status: done for the current additive bootstrap model.

- Add `audit` command to inspect existing agent instructions, docs, model profiles, skills, tool profiles, and `.repo-familiar/bootstrap.yml`. Done.
- Add `bootstrap-existing` dry-run behavior to preview proposed additive changes. Done.
- Add `bootstrap-existing --apply` to write missing assets without overwriting conflicts. Done.
- Add conflict reporting for files such as `AGENTS.md`, `.agents/models.yml`, `docs/_quarto.yml`, and `plan.md`. Done.
- Add selected `add-skill` and `add-tool` flows that can vendor chosen assets into an existing repository. Done.
- Add selected `add-model` and `add-docs` flows. Done.
- Add targeted advisory profile add commands for memory, prompts, safety, privacy, repomap, sandbox, secrets, design, and worktrees. Done.
- Add `--asset-group` to audit and bootstrap existing repositories. Done.
- Decide later whether bootstrap metadata needs `adopted_assets` and `conflicts` fields.
- Add JSON output for scripted audits. Done for `audit` and bootstrap results.

Acceptance criteria:

- Existing repository bootstrap does not overwrite user-owned files by default.
- Dry-run output clearly separates assets to add, assets already present, and conflicts requiring user action.
- Added tools and skills are represented in `.repo-familiar/bootstrap.yml` using structured asset records.
- Tool profiles contain non-secret setup guidance only.
- Targeted add flows do not create unrelated defaults.

### 13. Add Upstream Improvement Loop

Status: partially done. The read-only `diff-upstream-candidate` command and `upstream-improvement` skill exist; `prepare-upstream-pr` remains future work.

Downstream Repositories should be able to propose improvements back to this Reference Source when generated assets, advisory profiles, skills, docs, or advice heuristics improve through real use.

Candidate shape:

- Add an `upstream-improvement` skill that helps an agent identify whether a local change is generally useful, strips project-specific details, and drafts a focused upstream PR. Done.
- Use `.repo-familiar/bootstrap.yml` as the provenance source for which assets came from this Reference Source.
- Add a read-only `diff-upstream-candidate` command to compare generated assets against Bootstrap Metadata and classify changes as unchanged, modified, missing, unchecked, or unsafe/private. Current Reference Source comparison is advisory until richer template context is recorded. Done.
- Add a `prepare-upstream-pr` command later only if repeated manual PR prep becomes tedious.
- Keep real secrets, private data, customer specifics, and machine-local paths out of upstream proposals.
- Prefer small upstream PRs: one generated asset improvement, one skill improvement, one profile addition, or one advice heuristic change at a time.

Acceptance criteria:

- A Downstream Repository can identify which local generated assets have changed from recorded checksums. Done.
- The skill can guide the user through deciding whether a change is local-only or reusable upstream. Done.
- The workflow produces a concise PR summary with source context, affected generated assets, and verification commands.
- The workflow never pushes or opens a PR without explicit user approval.
- The workflow includes a privacy/safety checklist before copying downstream content into this Reference Source.

### 14. Deepen Core Generator Modules

Status: done for the planned seam extraction pass. Bootstrap Metadata, profile registry, asset planning, repository advice orchestration, and table-driven targeted CLI command seams are extracted.

Architecture review found that `generator.py` is carrying too many responsibilities: profile registries, asset planning, filesystem writes, bootstrap metadata rendering/parsing, check behavior, repository signal detection, advice orchestration, and command suggestion formatting.

Refactor sequence:

1. Extract a Bootstrap Metadata Module. Done.
2. Extract a profile registry Module for profile data, validation, listing, and profile rendering. Done.
3. Extract an asset planning Module for template assets, skill assets, asset kinds, and asset-group filtering. Done.
4. Extract repository advice orchestration from `generator.py` while keeping `advice_dag.py` pure and Hamilton-compatible. Done.
5. Make targeted CLI add commands table-driven so new profile families do not require repeated branch edits. Done.

Acceptance criteria:

- Bootstrap Metadata can be loaded and rendered through one interface.
- `check` reads generated asset records through the metadata Module.
- Future commands can access reference source, selected options, bootstrap mode, generator version, and generated assets without parsing YAML inline.
- Metadata tests cover full schema-v1 fields needed by `upgrade`, including reference source, selected options, generator identity, and metadata self-hash omission.
- Asset planning tests cover checksums and asset-group filtering needed by `diff-upstream-candidate`.
- `opencode-homebrew-path` remains framed as agent-shell guidance only, not workstation installation or machine configuration.
- Existing tests and generated snapshots continue to pass without user-facing CLI changes.
- No new broad compatibility layer is added unless a real Downstream Repository requires it.

## Next Highest Priority Slices

Priority 1: Dogfood on one low-risk existing repository using the renamed command and narrow adoption set. Use `advise`, `audit`, then add only memory, `grill-with-docs`, `get-api-docs`, and `opencode-homebrew-path` unless the repo clearly triggers more.

Priority 2: Dogfood `diff-upstream-candidate` plus `upstream-improvement` on this Reference Source and one generated/bootstrapped Downstream Repository before adding PR automation. Capture whether Bootstrap Metadata needs project name/description or rendered-context fields to make current Reference Source comparison exact.

Priority 3: Dogfood the read-only `upgrade` command on this Reference Source and one Downstream Repository. Capture which metadata fields are needed before a write-capable updater can safely exist.

Priority 4: Decide whether Existing Repository Bootstrap needs schema v2 fields such as `adopted_assets`, `conflicts`, `bootstrap_history`, or stage progression metadata after two or three real bootstraps.

Priority 5: Re-run `improve-codebase-architecture` after dogfooding `diff-upstream-candidate` and before implementing write-capable upgrade behavior.

Priority 6: Consider `prepare-upstream-pr` only after two or three manual upstream improvement proposals expose repeated steps.

## Verification Commands

```bash
uv sync
uv run python -m unittest discover -s tests
uv run python -m compileall src tests
/usr/local/bin/quarto render docs
```

Smoke generation:

```bash
uv run python -m repo_familiar generate \
  --name "Smoke Project" \
  --description "Smoke test project." \
  --output /tmp/repo-familiar-smoke \
  --agent-harness opencode \
  --agent-harness hermes \
  --model-profile default-coding \
  --model-profile budget-review \
  --generated-at "2026-05-10T00:00:00Z" \
  --force
```

## Open Questions

- Which additional prompts should `questionary` ask versus infer from `advise`?
- What exact file conventions do Conductor, Hermes, and Pi need?
- Should selected skills be vendored from this repository only, installed from external sources, or both?
- Which optional asset groups should the `basic` template split out first?
- What concrete template complexity should trigger Banks adoption?
- Should existing repository bootstrap update schema v1 or introduce schema v2 once adopted/conflicted assets are tracked?
- Should future upgrade behavior use checksum drift, three-way merge, or explicit user prompts for each changed generated asset?
- Should upstream-improvement start as a skill only, or should it also get a first-class CLI command once two or three real upstream PRs expose the repeated steps?
