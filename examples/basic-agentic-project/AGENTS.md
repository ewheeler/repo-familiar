# Basic Agentic Project Agent Instructions

This repository was generated with `repo-familiar`.

## Working Defaults

- Treat documentation as part of the implementation.
- Preserve project-specific terminology in `CONTEXT.md` when present.
- Keep agent runtime configuration in `.agents/`.
- Keep generator provenance in `.repo-familiar/bootstrap.yml`.

## Agent Harnesses

- `opencode`
- `hermes`

## Model Profiles

Selected model profiles are defined in `.agents/models.yml`:

- `default-coding`
- `budget-review`

## Tool Profiles

Selected non-secret tool setup guidance is defined in `.agents/tools.yml`:

- `cq`

## Memory Profiles

Selected memory guidance is defined in `.agents/memory.yml`:

- `memory-local`

## Prompt Profiles

Selected prompt migration and evaluation guidance is defined in `.agents/prompts.yml`:



## Safety Profiles

Selected prompt/output safety guidance is defined in `.agents/safety.yml`:



## Privacy Profiles

Selected data and privacy review guidance is defined in `.agents/privacy.yml`:



## Repo Map Profiles

Selected repository map and codebase graph guidance is defined in `.agents/repomap.yml`:



## Sandbox Profiles

Selected sandbox guidance is defined in `.agents/sandbox.yml`:



## Secrets Profiles

Selected local environment and secret-loading guidance is defined in `.agents/secrets.yml`:

- `dotenv-local`
- `kvenv-azure-keyvault`

## Design Profiles

Selected design guidance is defined in `.agents/design.yml`:



## Worktree Profiles

Selected worktree guidance is defined in `.agents/worktrees.yml`:



## Skills

Selected skills are vendored under `.agents/skills/`:

- `grill-with-docs`
