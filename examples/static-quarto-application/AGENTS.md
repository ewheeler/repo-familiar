# Static Quarto Application Agent Instructions

This is a Static Quarto Application generated with `repo-familiar`.

## Required Validation

- Run focused tests while changing behavior.
- Before handoff, run `uv run pre-commit run --all-files`.
- Run `uv run reproduce --check` after changing data, configuration, or analysis code.
- Render both `app/` and `docs/` after changing their source.
- For user-facing behavior, run the browser flow against the served rendered artifact.
- Do not claim a workflow is verified unless its documented verification command passed.

## Application Boundary

- Keep the product interface under `app/` and Divio project documentation under `docs/`.
- Keep the Quarto client static; browser code initiates ordinary request/response calls to versioned FastAPI routes.
- Validate requests and responses with Pydantic.
- Call the same deterministic `analyze()` function from batch reproduction and the API.
- Prefer same-origin serving. Use explicit allowed origins for split hosting; never default to permissive CORS.
- Do not add WebSockets, server-sent events, databases, authentication, workers, or server-side rendering without a product requirement.

## Reproducibility And Stack

- Use `uv` for environments, locking, and commands.
- Use Pydantic for boundaries, Polars for tabular transformations, Hamilton for the analysis graph, and Structlog for service events.
- Separate networked acquisition from offline reproduction and identify external inputs by checksum.
- Keep production transformations in importable modules and generated artifacts out of version control.
- Add Hydra/OmegaConf, fsspec/universal-pathlib, or Banks only when their documented threshold is met.

## Documentation As Evidence

- Keep tutorials, how-to guides, reference, and explanation purposes separate.
- Keep the tutorial's input, interaction, visible result, and provenance aligned with the browser test.
- Observable behavior changes update the exemplar, docs, API test, and browser test together.

## Existing Repository Safety

- Treat existing manifests, locks, source, tests, CI, application UI, and docs as user-owned.
- Never rewrite an existing Static Quarto Application merely to match this scaffold.
- Keep generator provenance in `.repo-familiar/bootstrap.yml` and runtime guidance in `.agents/`.

## Selected Agent Defaults

Harnesses:

- `opencode`

Tool profiles:

- `cq`
- `python-guardrails`
- `preferred-python-stack`
- `browser-automation`
- `a11y-scanner`

Skills:

- `grill-with-docs`
- `reproducible-data-science`
- `setup-python-guardrails`
- `static-quarto-application`
- `playwright-cli`
- `a11y-web-scan`
