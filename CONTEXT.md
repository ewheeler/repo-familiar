# repo-familiar

`repo-familiar` defines a project-generation context for bootstrapping downstream repositories with reusable agentic engineering defaults.

## Language

**Project Generator**:
The primary product that creates downstream repositories with selected agent, model, template, and documentation defaults.
_Avoid_: Workstation installer, dotfiles installer

**Reference Source**:
The canonical repository that records the defaults, templates, skills, and documentation patterns used by generated projects.
_Avoid_: Backup copy, scratch notes

**Agentic Engineering Defaults**:
Reusable preferences for agent instructions, skills, model/provider profiles, documentation, and implementation architecture.
_Avoid_: Personal shell setup, machine configuration

**Model Profile**:
An agent-facing model/provider default recorded in `.agents/models.yml`, describing model IDs, intended uses, harness compatibility, and cost or latency notes.
_Avoid_: Provider secret, API credential

Profile names are stable handles used by **Bootstrap Metadata**; profile records should stay pragmatic rather than fully normalized until templates need more structure.

**Downstream Repository**:
A generated or manually prepared project that consumes conventions from the **Reference Source**.
_Avoid_: Target folder, local checkout

**Vendored Generated Assets**:
Copies of selected templates, skills, instructions, and documentation files written into a **Downstream Repository** during bootstrap.
_Avoid_: Live dependency, synced files

**Agent Plugin Export**:
An optional derived Agent Plugins package containing portable skills or MCP configuration for installation by compatible clients. It is not a **Downstream Repository** and does not replace **Vendored Generated Assets**.
_Avoid_: Project bootstrap, universal installer

**Existing Repository Bootstrap**:
A non-destructive workflow that audits an existing **Downstream Repository** and adds selected **Agentic Engineering Defaults** without overwriting user-owned files by default.
_Avoid_: Migration script, repository takeover

**Tool Profile**:
A reusable non-secret tool or MCP setup recommendation that may be selected during generation or existing repository bootstrap.
_Avoid_: Credential, workstation package install

**Advisory Profile**:
A non-secret recommendation record for optional repository capabilities such as memory, sandboxing, design guidance, or worktree orchestration.
_Avoid_: Installer, secret-bearing config, runtime dependency

Secrets guidance is an **Advisory Profile** family. It may describe dotenv loading, secret references, or local secret injection tools, but it must not contain secret values.

**Bootstrap Metadata**:
A `.repo-familiar/bootstrap.yml` record of the **Reference Source** version, source location, selected options, and generated asset set used to create a **Downstream Repository**.
_Avoid_: Lockfile, install log

Minimum fields: `schema_version`, `reference_source`, `generated_at`, `generator`, `selected_options`, and `generated_assets`.
`generated_assets` uses structured records with `path`, `kind`, `source`, and optional `content_sha256` fields.
Initial `kind` values are `agent_instructions`, `skill`, `documentation`, `template_config`, `project_plan`, and `metadata`.

**Repo Familiar Metadata Directory**:
The `.repo-familiar/` namespace for generator-owned metadata in a **Downstream Repository**.
_Avoid_: Root metadata files, hidden agent directory

**Upgrade Command**:
A future explicit workflow that updates a **Downstream Repository** from a newer **Reference Source** version.
_Avoid_: Automatic sync, background update

**Dotfiles Metaphor**:
The framing that these conventions should be portable and personal, without making workstation configuration the main product boundary.
_Avoid_: Dotfiles implementation, home-directory sync

## Relationships

- The **Reference Source** defines one or more **Project Generators**.
- A **Project Generator** creates a **Downstream Repository**.
- A **Downstream Repository** receives selected **Agentic Engineering Defaults**.
- **Existing Repository Bootstrap** applies selected **Agentic Engineering Defaults** to a **Downstream Repository** that already has user-owned files.
- **Model Profiles** live in `.agents/models.yml`; **Bootstrap Metadata** records selected profile names only.
- **Tool Profiles** may be selected like **Model Profiles**, but secrets and machine-specific installation remain out of scope.
- **Advisory Profiles** live in `.agents/*.yml` files and record recommended tools or practices without installing them.
- **Advisory Profiles** for secrets generate `.agents/secrets.yml` and `.env.example`; real `.env` files remain ignored and user-owned.
- **Vendored Generated Assets** are the default delivery model for **Agentic Engineering Defaults**.
- An **Agent Plugin Export** is an optional portable subset derived from the **Reference Source**; client-specific installation and activation remain outside the **Project Generator**.
- **Bootstrap Metadata** lives in the **Repo Familiar Metadata Directory** and records which **Reference Source** produced a **Downstream Repository**.
- An **Upgrade Command** may later refresh **Vendored Generated Assets**, but updates are explicit rather than live-synced.
- The **Dotfiles Metaphor** explains portability, not the product scope.

## Example Dialogue

> **Dev:** "Are we building a personal dotfiles installer?"
> **Domain expert:** "No. This is a **Project Generator** for downstream repositories; dotfiles are only the metaphor for portable, personal defaults."
>
> **Dev:** "Should generated projects keep referencing this repo at runtime?"
> **Domain expert:** "No. They receive **Vendored Generated Assets** plus **Bootstrap Metadata** in `.repo-familiar/bootstrap.yml`; any refresh should happen through an explicit **Upgrade Command**."
>
> **Dev:** "Where do selected model defaults belong?"
> **Domain expert:** "The runtime defaults live as **Model Profiles** in `.agents/models.yml`; `.repo-familiar/bootstrap.yml` records which profiles were selected during generation."
>
> **Dev:** "Can we apply these defaults to a repository that already exists?"
> **Domain expert:** "Yes, through **Existing Repository Bootstrap**: audit first, preview changes, then add selected assets without overwriting user-owned files unless explicitly requested."

## Flagged Ambiguities

- "dotfiles repo" could mean workstation setup or project bootstrap. Resolved: this repo is primarily a **Project Generator** and **Reference Source**, not a general workstation installer.
- "sync" could mean live background updates or an explicit upgrade. Resolved: generated repositories are stable and self-contained by default; update flows must be explicit.
- "bootstrap metadata" could live at the root, under `.agents/`, or under a generator namespace. Resolved: use `.repo-familiar/bootstrap.yml` so generator metadata is namespaced and separate from agent runtime instructions.
- "model profile" could mean runtime defaults or generation provenance. Resolved: `.agents/models.yml` stores agent-facing defaults; `.repo-familiar/bootstrap.yml` stores selected profile names.
- "bootstrap existing repo" could mean force-migrating or taking ownership of current files. Resolved: **Existing Repository Bootstrap** is additive and non-destructive by default.
