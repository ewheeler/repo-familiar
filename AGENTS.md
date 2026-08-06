# repo-familiar Agent Instructions

## Repository Routing

- Read `docs/agents/repository-map.md` before broad code search or architectural work.
- Preserve the Project Generator, Reference Source, Downstream Repository, and Vendored Generated Assets language in `CONTEXT.md`.
- Treat `src/repo_familiar/templates/` and `src/repo_familiar/profiles.py` as canonical inputs; root `.agents/` files and `examples/basic-agentic-project/` are dogfood or snapshot copies.
- Keep the repository map selective and update it when ownership moves or a high-leverage interface is added.

## Change Locality

- Generator or bootstrap behavior: start in `src/repo_familiar/generator.py`, then update the nearest focused tests.
- Asset kinds or grouping: start in `src/repo_familiar/asset_plan.py`.
- Profiles or skills: update the registry, canonical template, dogfood copy, provenance, profile tests, and any recorded dogfood checksum together.
- CLI contracts: keep `src/repo_familiar/cli.py`, lifecycle documentation, and CLI/documentation tests aligned.

## Validation

- Run focused tests first, then `PYTHONPATH=src uv run pytest` for shared generator behavior.
- Run `git diff --check` before handoff.
