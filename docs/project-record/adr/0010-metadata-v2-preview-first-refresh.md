---
doc-type: explanation
---

# Plan Metadata v2 and preview-first refresh

## Status

Accepted. Use the root `PLAN.md` and current source/tests for implementation status.

## Context

Bootstrap Metadata v1 deliberately stays small. `schema_version`, `reference_source`, `generated_at`, `generator`, `selected_options`, and structured `generated_assets` records are enough to answer three current questions safely:

- What did `repo-familiar` generate or write?
- Which selected options and source paths produced those assets?
- Has a recorded asset drifted, gone missing, or become hard to compare?

That is enough for `check`, advisory `diff-upstream-candidate` output, and a narrow skills refresh because vendored skill files are deterministic copies with recorded checksums. It is not enough for broad write-capable refresh because v1 cannot reliably reconstruct the original render basis for every template asset or distinguish between assets that were generated, adopted, skipped, or left in conflict.

## Why Metadata V1 Is Enough For Read-Only Checks

Metadata v1 supports read-only reasoning because it records the minimum facts needed to compare the current working tree against the last known generated output:

- `selected_options` explains which profile names, skills, template, and docs mode were selected.
- `generated_assets[].source` explains which reference-source template or skill file produced the downstream copy.
- `generated_assets[].content_sha256` lets `check` tell whether a recorded generated asset still matches the last written content.
- Existing-repository bootstrap records only assets actually written, so preview commands do not falsely claim ownership of conflicts that were skipped for safety.

This is enough for check/preview commands because those commands can say "this asset drifted", "this asset is missing", or "the current Reference Source may have changed" without deciding how a write should happen.

## Why Metadata V1 Is Not Enough For Safe Refresh Writes

Write-capable refresh needs stronger evidence than read-only classification. Metadata v1 does not yet record:

- The original render inputs for template-driven assets, including conditional branches, prompt answers, or asset-group scoping details that may have affected the rendered file.
- Bootstrap history showing which command wrote, adopted, skipped, or deferred an asset over time.
- Conflict/adoption records for assets that were reviewed manually instead of written directly by the generator.
- An asset-specific refresh strategy that says whether a file is eligible for replace-in-place, merge-preview, or manual review only.
- A durable comparison basis for upstream skills, generated profile files, and template-heavy docs beyond a single post-render checksum.

Without those facts, a future apply step could mistake a user-edited file for a safe overwrite candidate, miss a previously adopted file that now needs manual review, or regenerate a template with the wrong inputs.

## Metadata V2 Concepts

Metadata v2 should stay repository-scoped and non-secret, but capture enough provenance for preview/apply refresh. The exact schema can evolve, but the concepts should include:

### Original render inputs

Record the render basis needed to reproduce or explain a generated asset without inferring it from the current repository state alone.

Possible fields:

```yaml
render_context:
  template: basic
  docs: quarto
  selected_options_fingerprint: <sha256>
  inputs:
    agent_harnesses:
      - opencode
    model_profiles:
      - default-coding
```

This is not a secret dump. It should record only the non-secret inputs already implied by bootstrap choices, enough to explain why a template branch rendered the way it did.

### Bootstrap history

Keep append-only operation history so future preview/apply logic can tell whether an asset came from new-repo generation, existing-repo bootstrap, targeted add, or later refresh preview.

Possible fields:

```yaml
history:
  - at: 2026-06-09T00:00:00Z
    command: bootstrap-existing
    mode: preview
    selected_asset_groups:
      - docs
      - metadata
  - at: 2026-06-09T00:05:00Z
    command: bootstrap-existing
    mode: apply
```

### Adopted, skipped, and conflict records

Generated asset ownership is not binary for existing repositories. Metadata v2 should distinguish:

- `written`: file was created or updated directly by `repo-familiar`
- `adopted`: existing file was accepted as the downstream baseline after review
- `skipped`: file was intentionally left user-owned or out of scope
- `conflict`: file needs manual handling before any write-capable refresh

That history matters because later refresh preview should not treat adopted or conflicted files like untouched generator output.

### Asset comparison basis

Each asset should record what comparison method future preview/apply logic can trust.

Examples:

- Exact rendered checksum for deterministic generated files such as `.agents/models.yml`
- Source provenance plus upstream URL/version for vendored skills and `.agents/skill-sources.yml`
- Template fingerprint plus render-context fingerprint for template-heavy docs
- Presence-only or manual-review markers for files whose content is expected to diverge

### Asset-specific refresh strategies

Refresh preview should be driven by explicit strategy records, not one global overwrite rule.

Possible strategies:

- `replace_if_unchanged`: safe only when downstream content still matches the last generated baseline
- `line_union`: for append-like files such as `.gitignore`
- `merge_preview_only`: for heading-aware `AGENTS.md` or similar structured prose
- `manual_review`: default for `README.md`, `plan.md`, and other intentionally user-edited surfaces
- `unavailable`: preview can explain why an apply path does not exist yet

### Managed surfaces

Template promotion and application adoption need a boundary above individual paths. A Managed Surface groups a coherent capability such as `python-runtime`, `quality-and-ci`, `reproducible-analysis`, `divio-documentation`, `quarto-static-client`, or `fastapi-api` while preserving per-file provenance.

A surface records its identity, version, template, render-context fingerprint, associated paths, comparison basis, refresh strategy, operation history, and states such as `written`, `adopted`, `edited`, `skipped`, or `conflict`. Matching files make a surface eligible for exact metadata-only attach but do not establish adoption until the user applies `attach` explicitly.

A Metadata v1 migration may create records only from assets already recorded as generated. It must not infer ownership of unrecorded application source, docs, CI, manifests, or lockfiles.

## Preview First, Apply Later

Future refresh stays a two-step workflow:

1. `upgrade --preview`, `attach`, or `migrate-template` computes candidate changes, blockers, and per-asset strategies.
2. A later explicit apply command may reuse that design, but only for assets that preview classified as eligible for a safe strategy.

Preview output should show, for each asset:

- current downstream state
- comparison basis used
- current Reference Source state
- proposed refresh strategy
- whether apply is available, blocked, or manual-review only

Apply must remain narrower than preview. It should require explicit user intent, stay scoped by asset or asset group, and refuse to silently escalate from "manual review" or "conflict" into overwrite behavior.

Any skills write slice must additionally require a clean downstream Git worktree by default, record the current Reference Source commit/version, block removed-reference assets instead of deleting them, and stage the write set with rollback on apply failure. `--allow-dirty` and `--reference-ref` are explicit overrides rather than inferred behavior.

## Safety Boundaries

Metadata v2 and future refresh work must preserve the existing product boundary:

- No live sync, daemon, watcher, or background refresh loop.
- No machine-level config writes, installer behavior, or harness-global shortcuts.
- No secret capture in metadata; record only non-secret render inputs and provenance.
- No write-capable refresh shortcut that skips preview.
- No broad repository takeover; user-owned files remain user-owned unless an explicit adoption or apply workflow records otherwise.
- No promotion shortcut may delete paths or escalate manual review. `attach --apply` writes Metadata v2 only. `promote-surface --apply` handles one eligible surface. `promote-template --apply` composes every target surface in dependency order and blocks the entire transaction when any surface is edited, conflicting, extra, omitted by the target, or manual-review only.
- README files, plans, documentation prose, application source, lockfiles, and edited files default to `manual_review` even when they belong to a Managed Surface.

## Consequences

- `check`, `diff-upstream-candidate`, and legacy `migrate-template` stay read-only. `upgrade`, `promote-surface`, and `promote-template` may write only within explicitly supported strategies.
- Metadata v2 must record render context, Managed Surfaces, per-surface assets, and append-only operation history so preview and attach can reconstruct ownership and comparison state.
- Existing Metadata v1 repositories migrate losslessly: only recorded generated assets become `written`; unrecorded files remain user-owned.
- Lifecycle and upgrade docs should point maintainers to this ADR instead of re-explaining the full design in every command page.

## Cross References

- [Bootstrap Lifecycle](../../reference/bootstrap-lifecycle.qmd)
- [Generator](../../reference/cli-and-metadata.qmd)
- [Existing Repositories](../../how-to/bootstrap-existing-repository.qmd)
- [Minimal bootstrap metadata schema](./0004-minimal-bootstrap-metadata-schema.md)
- [Structured generated asset records](./0005-structured-generated-assets.md)
- [Python-First Project Plan](../python-first-project-plan.qmd)
- [Separate Python-first greenfield defaults from existing-repository adoption](./0012-python-first-greenfield-existing-repository-boundary.md)
