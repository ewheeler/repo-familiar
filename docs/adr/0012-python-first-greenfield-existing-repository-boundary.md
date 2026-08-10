# Separate Python-first greenfield defaults from existing-repository adoption

## Status

Accepted and implemented for the current safe boundary. Greenfield templates, split defaults, guidance, examples, Metadata v2 Managed Surfaces, metadata-only attach, and promotion preview are implemented; broad content apply remains deferred.

## Context

The current `basic` template provides agent instructions, advisory profiles, planning assets, and Divio-shaped Quarto documentation. It does not encode the preferred Python stack as an executable project, or prove reproducible data-product behavior through a working exemplar.

New repositories can safely receive a more opinionated scaffold. Existing repositories are different: Bootstrap Metadata v1 records one selected template and per-file generated provenance, but it cannot represent layered template history, original render context, adopted or skipped files, or a coherent multi-file application surface. Changing one shared default would also cause existing-repository audit and bootstrap flows to compare arbitrary repositories against Python application assets.

## Decision

- Add `python-reproducible` as the planned default for new repository generation.
- Keep `basic` as an explicit generic template and the fallback for unbootstrapped existing-repository workflows.
- Add `static-quarto-application` as an opt-in concrete greenfield template.
- Resolve new-generation defaults separately from existing-repository fallbacks.
- Reconstruct already bootstrapped repositories from their recorded template and fail closed when that template is unavailable.
- Permit internal linear template composition, but record only the concrete effective template and per-file sources in Metadata v1.
- Deliver preferred-stack, reproducibility, and Static Quarto Application guidance additively to existing repositories without claiming ownership of their source, docs, CI, manifests, or lockfiles.
- Keep template promotion and application-source adoption preview-only until Metadata v2 records render context, history, comparison basis, strategy, and per-surface ownership state.
- Keep skills as the only write-capable upgrade slice under Metadata v1.

The detailed product, lifecycle, and implementation plan is recorded in [Python-First Project Plan](../python-first-project-plan.qmd).

## Consequences

- New generation becomes intentionally Python-first without silently changing historical downstream intent.
- Existing-repository commands remain conservative and non-destructive.
- Guidance can ship before Metadata v2 because it does not require source ownership.
- Greenfield manifests, lockfiles, source, tests, CI, and exemplar docs may be generated and recorded, but their normal downstream evolution is not automatically repairable generator drift.
- Plain Quarto documentation is not enough to infer a Static Quarto Application; advice requires evidence of Quarto, FastAPI, and a browser/API interaction boundary.
- Metadata v2 becomes a prerequisite for attach, adoption, template promotion, and broad refresh apply rather than an optional follow-up.

## Rejected Alternatives

### Change the shared `basic` default everywhere

Rejected because it would cause existing-repository audit and bootstrap behavior to inherit greenfield Python assumptions.

### Model the application only as profiles or skills

Rejected because guidance cannot provide executable manifests, application source, tests, CI, or a working documentation exemplar.

### Promote untouched `basic` repositories under Metadata v1

Rejected for write-capable behavior. Checksums can show that recorded files are untouched, but v1 cannot reconstruct the complete render basis or represent adoption of a coherent new surface.

### Add one broad `project_scaffold` asset kind

Rejected because it would not distinguish dependency locks, source, tests, or fixtures whose downstream ownership and refresh behavior differ.

## Safety Boundaries

- No implicit template migration for existing repositories.
- No fallback from an unknown recorded template to a new default.
- No ownership claim based only on matching file content.
- No automatic replacement of existing manifests, lockfiles, CI, docs, or application source.
- No broad non-skill upgrade apply under Metadata v1.

## Cross References

- [Python-First Project Plan](../python-first-project-plan.qmd)
- [Plan Metadata v2 and preview-first refresh](./0010-metadata-v2-preview-first-refresh.md)
- [Existing Repositories](../existing-repos.qmd)
- [Architecture](../architecture.qmd)
