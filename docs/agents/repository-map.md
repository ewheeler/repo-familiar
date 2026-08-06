# Repository Map

This is the semantic routing map for the repo-familiar Reference Source. It identifies owning interfaces, implementation seams, adjacent tests, and generated boundaries. It is intentionally not an exhaustive filesystem tree.

Start at the narrowest owner below. Expand through imports and tests only when the documented seam crosses modules.

`AGENTS.md` is the concise repository entry point; this map carries the detailed routing it references.

## Authority Order

Use these sources according to the question being answered:

1. `CONTEXT.md` defines the product boundary and canonical domain language.
2. `docs/adr/` records durable architecture decisions and their status.
3. `PLAN.md` records current priorities, implementation status, and proposed work.
4. `docs/bootstrap-lifecycle.qmd` owns command safety, lifecycle routing, and profile-family selection guidance.
5. `docs/architecture.qmd` explains the current design and generated-asset model.
6. `src/repo_familiar/` and `tests/` establish implemented behavior.

Plans and accepted ADRs can describe work that is not implemented. Confirm behavior in source and tests before treating it as available.

## Architectural Shape

```text
CLI or interactive options
  -> validated generation or existing-repository options
  -> project and skill asset planning
  -> profile and template rendering
  -> audit, conflict classification, or guarded writes
  -> Bootstrap Metadata and integrity checks
```

Maintenance flows reuse those contracts for advice, targeted additions, upstream candidate review, and explicit preview-first upgrades.

## Core Modules

| Path | Responsibility |
|---|---|
| `src/repo_familiar/cli.py` | Command parser, command-family contracts, report formatting, and command dispatch. |
| `src/repo_familiar/generator.py` | Generation options, project planning orchestration, new project writes, existing-repository audit/bootstrap, and repository signal entry points. |
| `src/repo_familiar/asset_plan.py` | Planned asset model, template traversal, asset kinds, and asset-group filtering. |
| `src/repo_familiar/profiles.py` | Canonical agent harness, profile, skill, and provenance registries plus YAML and harness-config rendering. |
| `src/repo_familiar/metadata.py` | Bootstrap Metadata parsing, validation, and rendering. |
| `src/repo_familiar/interactive.py` | `questionary` adapters for generation and existing-repository options. |
| `src/repo_familiar/advice.py` | Repository signal detection and advice orchestration. |
| `src/repo_familiar/advice_dag.py` | Pure Hamilton-compatible recommendation nodes; formatting and filesystem orchestration stay outside this module. |
| `src/repo_familiar/upgrade.py` | Upgrade preview classification and the bounded transactional skill apply path. |
| `src/repo_familiar/upstream.py` | Read-only classification of downstream generated-asset changes for upstream review. |
| `src/repo_familiar/skill_sources.py` | External skill source parsing and provenance drift checks. |

`src/repo_familiar/__main__.py` is the module entry point. `pyproject.toml` owns packaging, the `repo-familiar` console script, dependencies, and packaged template paths.

## Generation And Bootstrap Routes

### New repositories

`GenerationOptions` flows through `plan_project()` in `src/repo_familiar/generator.py`. `src/repo_familiar/asset_plan.py` renders canonical project templates and selected skill templates, then `src/repo_familiar/metadata.py` records the selected options and generated assets before guarded writes occur.

### Existing repositories

`ExistingBootstrapOptions` reuses the generation plan. Audit classifies assets as missing, present, or conflicting; apply remains additive and non-destructive unless force is explicit. Targeted add commands select one profile or skill family plus metadata rather than taking ownership of unrelated files.

### Advice

`src/repo_familiar/advice.py` detects repository signals and combines user intent with recommendation nodes from `src/repo_familiar/advice_dag.py`. Keep decision rules pure enough for future graph inspection; keep command formatting and filesystem inspection in the orchestration module.

### Upgrade and upstream review

`src/repo_familiar/upgrade.py` owns explicit preview and apply behavior. `src/repo_familiar/upstream.py` is read-only and classifies downstream differences; it does not copy or publish changes automatically.

## Template, Profile, And Skill Boundaries

| Path | Classification |
|---|---|
| `src/repo_familiar/templates/basic/` | Canonical project scaffold inputs. |
| `src/repo_familiar/templates/skills/` | Canonical selectable skill inputs. |
| `src/repo_familiar/profiles.py` | Canonical profile values, skill names, and skill-source provenance. |
| `.agents/` | Reference Source dogfood copies; keep them aligned with canonical registries and templates. |
| `.agents/skill-sources.yml` | Dogfood skill provenance rendered from the canonical registry. |
| `examples/basic-agentic-project/` | Committed deterministic generator snapshot, not implementation authority. |

The `semantic-routing-map` profile standardizes the convention and the `repository-map` skill authors the map. The map itself remains project-owned rather than a Vendored Generated Asset because its content must evolve with downstream architecture.

## Test Routing

| Change | Start with |
|---|---|
| CLI, generation, bootstrap, targeted additions, or interaction | `tests/test_generator.py` |
| Asset kinds, traversal, or groups | `tests/test_asset_plan.py` |
| Profile rendering, skill registration, or dogfood parity | `tests/test_profiles.py` |
| Advice signals or recommendations | `tests/test_advice.py` |
| Bootstrap Metadata schema or rendering | `tests/test_metadata.py` |
| Upgrade safety or apply behavior | `tests/test_upgrade.py` |
| Upstream candidate classification | `tests/test_upstream.py` |
| External skill provenance | `tests/test_skill_sources.py` |
| Generated example parity | `tests/test_examples.py` |
| Documentation and CLI contract parity | `tests/test_docs.py` |

Prefer focused tests at the owning seam. Run the full suite when shared planning, metadata, profile, or template behavior changes.

## Durable Inputs And Generated Boundaries

- Source modules, tests, templates, profile registries, Quarto source, ADRs, `CONTEXT.md`, `PLAN.md`, `pyproject.toml`, and `uv.lock` are durable Reference Source inputs.
- Root `.agents/` files are dogfood copies. Update their canonical registry or skill template in the same change.
- `.repo-familiar/bootstrap.yml` records bootstrap provenance; it is metadata, not agent runtime configuration.
- `examples/basic-agentic-project/` is a generated snapshot and should be regenerated when default output changes.
- `docs/_site/`, `docs/.quarto/`, Python caches, and package build metadata are reproducible outputs, not implementation authority.

## Implemented Versus Proposed

- New generation, advice, audit, additive existing-repository bootstrap, targeted additions, checksums, profile catalogs, deterministic snapshots, and skill-source checks are implemented.
- Upgrade apply is intentionally limited to safe vendored-skill refreshes and missing skill support files. Other generated asset groups remain preview-only.
- Metadata v2 is accepted in `docs/adr/0010-metadata-v2-preview-first-refresh.md`, while runtime Bootstrap Metadata remains schema version 1.
- Advice rules are Hamilton-compatible but currently execute as direct Python calls; no Hamilton driver owns runtime advice execution.
- Banks or Cookiecutter rendering and automated skill-security scanning remain proposed. Current templates use `string.Template`.

## Change Locality

- Profile change: update `src/repo_familiar/profiles.py`, rendered root `.agents/` dogfood, profile tests, user-facing profile docs, and any baseline recorded in `.repo-familiar/bootstrap.yml`.
- Skill change: update the canonical template under `src/repo_familiar/templates/skills/`, its root dogfood copy, provenance registry, and parity tests.
- Template change: update the canonical template, generation tests, and `examples/basic-agentic-project/` when default output changes.
- CLI change: update parser/dispatch, lifecycle or usage documentation, and CLI/documentation contract tests together.
- Metadata or upgrade change: preserve preview-first and non-destructive defaults, then test failure and rollback paths.

## Maintenance Policy

- Add a path only when it changes where a contributor or agent should start.
- Update this map in the same change that moves ownership or adds a high-leverage interface.
- Keep routine routing at module level; do not copy function or filesystem inventories that source inspection can answer.
- Validate concrete paths and remove stale entries. Mark future architecture as proposed rather than linking nonexistent paths.
