# repo-familiar

`repo-familiar` is a project generator for reusable agentic engineering defaults. This repository is the canonical **Reference Source** for templates, skills, profiles, documentation practices, and guarded bootstrap behavior delivered to **Downstream Repositories**.

## Goals

- Generate self-contained repositories with agent instructions, selected skills, explicit model/tool guidance, planning artifacts, and Quarto documentation.
- Add selected defaults to existing repositories through audit-first, preview-first workflows.
- Keep generated ownership explicit through Bootstrap Metadata without turning the project into a workstation installer or live synchronization service.
- Preserve project goals, decisions, implementation status, and routing in inspectable files that humans and agents can share.

## Quick Start

```bash
uv sync
uv run python -m repo_familiar list-templates
uv run python -m repo_familiar generate --interactive
```

Preview a non-interactive generation before writing it:

```bash
uv run python -m repo_familiar generate \
  --name "Demo Project" \
  --description "A generated demo." \
  --output /tmp/demo-project \
  --template basic \
  --agent-harness opencode \
  --dry-run
```

For an existing repository, start with read-only advice and audit:

```bash
uv run python -m repo_familiar advise --path /path/to/repo
uv run python -m repo_familiar audit --path /path/to/repo
```

Existing-repository writes require an explicit `--apply`. Conflicting user-owned files are preserved by default, and broad replacement or synchronization is not automatic.

## Documentation

- [Documentation home](docs/index.qmd): routes readers by learning, task, lookup, rationale, and project-record needs.
- [Getting started](docs/tutorials/generate-first-repository.qmd): completes and verifies one generated repository.
- [CLI reference](docs/reference/cli-and-metadata.qmd): commands and Bootstrap Metadata contract.
- [Architecture](docs/explanation/architecture.qmd): product boundaries, ownership, and stable engineering opinions.
- [Decisions](docs/project-record/decisions.qmd): accepted ADRs and their status.

## Repository Authorities

- [`CONTEXT.md`](CONTEXT.md) defines product boundaries and canonical domain language.
- [`PLAN.md`](PLAN.md) records current status, priorities, and planned work.
- [`docs/project-record/adr/`](docs/project-record/adr/) records durable decisions and rationale.
- [`docs/project-record/repository-map.md`](docs/project-record/repository-map.md) routes implementation work to owners and focused tests.
- Source and tests establish implemented behavior when plans and prose differ.

## Validation

```bash
PYTHONPATH=src uv run pytest tests/test_docs.py
/usr/local/bin/quarto render docs
PYTHONPATH=src uv run pytest
git diff --check
```
