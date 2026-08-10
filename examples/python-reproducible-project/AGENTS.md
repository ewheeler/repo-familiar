# Python Reproducible Project Agent Instructions

This is a Python Reproducible Project generated with `repo-familiar`.

## Required Validation

- Run focused tests while changing behavior.
- Before handoff, run `uv run pre-commit run --all-files`.
- Run `uv run reproduce --check` after changing data, configuration, or analysis code.
- Render `docs/` after changing documentation.
- Do not claim a workflow is verified unless its documented verification command passed.

## Reproducibility Contract

- Keep `pyproject.toml`, `uv.lock`, `.python-version`, configuration, input provenance, and exemplar inputs committed.
- Separate networked acquisition from offline reproduction.
- Treat raw inputs as immutable and identify external inputs by checksum.
- Make seeds, row ordering, time zones, and clocks explicit when they can affect results.
- Keep production transformations in importable modules; notebooks are exploratory.
- Keep `artifacts/`, `data/raw/`, and rendered Quarto output out of version control unless deliberately promoted as fixtures.

## Preferred Python Stack

- Use `uv` for environments, locking, and commands.
- Use Pydantic at configuration, API, and external-data boundaries.
- Use Polars expressions and lazy scans for tabular file pipelines.
- Use Hamilton for graph-shaped transformations and keep non-node helpers outside DAG modules.
- Use FastAPI and Structlog for service applications.
- Add Hydra/OmegaConf, fsspec/universal-pathlib, or Banks only when their documented threshold is met.

## Documentation As Evidence

- Keep the Quarto site organized as tutorials, how-to guides, reference, and explanation.
- Tutorials use known inputs and expected visible outputs.
- How-to guides include an explicit verification step.
- Reference pages describe tested commands, APIs, schemas, and limits.
- Explanation pages record architecture, tradeoffs, and reproducibility rationale.
- Observable behavior changes update the matching exemplar and regression test.

## Existing Repository Safety

- Treat manifests, locks, source, tests, CI, and docs as downstream-owned after generation.
- Never replace existing repository choices merely to match preferred defaults.
- Use `promote-surface` only for missing or checksum-clean eligible paths; manual-review differences block the whole surface.
- Use `promote-template` only after every dependency-ordered surface passes preview; no partial promotion or deletion is allowed.
- Keep generator provenance in `.repo-familiar/bootstrap.yml` and agent runtime guidance in `.agents/`.

## Selected Agent Defaults

Harnesses:

- `opencode`

Model profiles:

- `default-coding`

Tool profiles:

- `cq`
- `python-guardrails`
- `preferred-python-stack`

Skills:

- `grill-with-docs`
- `reproducible-data-science`
- `setup-python-guardrails`
