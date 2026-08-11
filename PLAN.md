# repo-familiar Plan

`repo-familiar` is a Project Generator for Downstream Repositories. This repository is the canonical Reference Source for reusable Agentic Engineering Defaults.

Use `CONTEXT.md` for product boundaries and domain language, `docs/project-record/adr/` for durable decisions, and `docs/project-record/repository-map.md` for implementation and test routing. This file owns live status, priorities, milestones, and open questions.

## Current Status

- New repository generation defaults to `python-reproducible`; `basic` remains the generic template and conservative existing-repository fallback; `static-quarto-application` is opt-in.
- Generated repositories receive vendored instructions, selected profiles and skills, Divio documentation, a plan, and Bootstrap Metadata.
- Existing repositories have read-only advice, scoped audit, conflict previews, dry-run bootstrap, and explicit additive `--apply` paths.
- Bootstrap Metadata v2 records provenance, selected options, generated assets, render context, Managed Surfaces, and operation history. Metadata v1 remains readable and migrates losslessly.
- Metadata-only `attach`, atomic `promote-surface`, and dependency-ordered all-or-nothing `promote-template` are implemented.
- `upgrade` remains preview-first; its write-capable path is limited to checksum-clean vendored skills and missing skill support files. Other write strategies require separate evidence.
- Profile and skill registries generate downstream `.agents/` assets and are dogfooded in the Reference Source with parity tests.
- Deterministic generated examples cover `basic`, `python-reproducible`, and `static-quarto-application` contracts.
- The optional Agent Plugins pilot exports the canonical `repository-map` skill; compatible-client installation validation remains pending.
- Reference Source documentation now uses physical Divio directories, matching tested sidebar sections, explicit page classification, and single-source authority boundaries.
- Source provenance checking is implemented for vendored skills; automated skill security scanning remains planned.
- The full test suite, generated example parity, package-data validation, and Quarto render are current release evidence.

## Current Limitations

- No live or background synchronization exists between the Reference Source and Downstream Repositories.
- No command silently adopts application source or overwrites edited downstream assets.
- Non-skill `upgrade` groups remain preview-only; Managed Surface promotion uses separate explicit commands.
- Machine-level harness settings, global MCP configuration, shell setup, credentials, and secret stores remain user-owned.
- Advice is heuristic and must be tuned from representative repository evidence.
- Automated SkillSpector integration and a first-class upstream PR preparation command are not implemented.

## Current Priorities

1. Dogfood preferred Python, reproducible data science, and Static Quarto Application guidance on representative existing repositories.
2. Tune advice detection from real Quarto, Python, and Static Quarto Application repositories.
3. Keep all three generated examples, dependency pins, canonical locks, and executable contracts current.
4. Dogfood Metadata v2 migration, attach, surface promotion, and broad template promotion on independently implemented Downstream Repositories.
5. Exercise untouched, edited, partially adopted, and conflicting Managed Surfaces to refine boundaries and comparison strategies.
6. Decide whether dogfood evidence justifies any additional write strategies beyond missing-file creation and checksum-clean `replace_if_unchanged`.
7. Validate the Agent Plugins pilot with at least two compatible clients before expanding its scope.
8. Add vendored-skill security scanning only through a deterministic, pinned, read-only first slice.
9. Revisit deployment guidance only when a real Static Quarto Application requires it.

## Active Milestones

### Dogfood Managed Surface Workflows

Status: implemented in source; downstream evidence gathering remains active.

- Run migration, attach, surface promotion, and template promotion against independently implemented repositories.
- Capture where exact-file comparison, accepted-current baselines, dependencies, or surface boundaries are unclear.
- Preserve atomic rollback, no-deletion behavior, clean-checksum replacement, and final-only template transition.

Done when representative untouched, edited, partial, and conflicting cases produce actionable previews and no silent ownership expansion.

### Add Vendored Skill Security Scanning

Status: planned.

- Add a read-only `check-skill-security` command over whole vendored skill directories.
- Invoke a pinned external SkillSpector runner rather than adding it to the normal project dependencies.
- Default to static, credential-free `--no-llm` analysis with text and JSON output.
- Use fake runners in tests; require no network, provider credentials, or real scanner installation.
- Consider `add-skill --scan-security` only after the standalone command proves useful and reliable.

Done when deterministic tests cover success, unavailable scanner, malformed output, and actionable HIGH/CRITICAL findings.

### Validate Agent Plugins Export

Status: skills-only exporter implemented; client validation pending.

- Test the generated `plugin.json` and `repository-map` skill package with two compatible clients.
- Keep installation, activation, updates, and permissions client-owned.
- Do not replace `.agents/skills/`, Bootstrap Metadata, or normal Project Generator delivery.

Done when client evidence either validates the portable pilot or identifies a concrete adapter requirement.

### Improve Advice From Dogfood Evidence

Status: first Hamilton-compatible heuristic pass implemented.

- Compare recommendations against representative repositories and explicit user intent.
- Tune signals only when false positives or missing recommendations repeat.
- Keep filesystem inspection and formatting outside pure recommendation nodes.

Done when recommendations reliably distinguish research, prototyping, implementation planning, and production maintenance without broad default adoption.

### Expand Upgrade Writes Conservatively

Status: evidence gathering.

- Keep `README.md`, docs prose, project plans, and edited assets manual-review by default.
- Consider mapping merge, line union, heading merge, and JSON merge one asset family at a time.
- Require reconstructable render context, clean comparison bases, preview evidence, and rollback tests before enabling apply.

Done only when one additional strategy has a narrow ownership boundary and cannot silently overwrite local work.

## Completed Milestones

| Area | Result |
|---|---|
| Minimal generator | Deterministic planning, dry-run, overwrite protection, interaction, and guarded writes. |
| Template contracts | Generic, reproducible Python, and Static Quarto Application templates with explicit composition. |
| Existing-repository adoption | Advice, audit, conflict preview, targeted additions, scoped bootstrap, and metadata ownership. |
| Metadata and drift | Structured assets, checksums, v1/v2 parsing, Managed Surfaces, checks, migration, attach, and promotion. |
| Profiles and skills | Registry-backed profile families, selectable vendored skills, source provenance, and root dogfood parity. |
| Examples | Three deterministic generated snapshots with focused regression tests. |
| Documentation | Physical Divio directories, matching navigation, typed pages, authority routing, exact inventory/link tests, render validation, and accessibility labels. |
| Architecture seams | Dedicated CLI, metadata, asset planning, profile, advice, upgrade, Managed Surface, and promotion modules. |
| Upstream review | Read-only downstream candidate classification and the `upstream-improvement` skill. |

## Verification Commands

```bash
uv sync
PYTHONPATH=src uv run pytest tests/test_docs.py
PYTHONPATH=src uv run pytest
PYTHONPATH=src uv run python -m compileall src tests
/usr/local/bin/quarto render docs
git diff --check
```

Smoke generation:

```bash
uv run python -m repo_familiar generate \
  --name "Smoke Project" \
  --description "Smoke test project." \
  --output /tmp/repo-familiar-smoke \
  --template python-reproducible \
  --agent-harness opencode \
  --model-profile default-coding \
  --dry-run
```

## Open Questions

- Which additional prompts should `questionary` ask rather than infer from `advise` or template defaults?
- What repository-local conventions, if any, do Conductor, Hermes, and Pi require?
- What measured template complexity should trigger replacing `string.Template` with Banks or another renderer?
- Which additional write strategy has enough downstream evidence to implement safely first?
- Should repeated upstream contribution work remain skill-guided or justify a `prepare-upstream-pr` command?
- Which real deployment should define the first Static Quarto Application deployment guidance?
