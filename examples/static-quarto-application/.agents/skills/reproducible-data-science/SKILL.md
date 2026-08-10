---
name: reproducible-data-science
description: Build reproducible data workflows with locked environments, input provenance, deterministic execution, and executable evidence. Use when creating or changing Python data pipelines, analytical products, datasets, or result-producing documentation.
---

# Reproducible Data Science

## Contract

Given committed code, configuration, a locked environment, and checksum-identified inputs, one documented command should reproduce validated derived artifacts without network access.

## Workflow

1. Separate networked acquisition from offline reproduction.
2. Commit the project manifest, lockfile, Python version, configuration, source records, and small exemplar inputs.
3. Record source, license, retrieval date, media type, local path, and expected SHA-256 for external inputs.
4. Keep raw inputs immutable and identify them by checksum.
5. Put production transformations in importable modules; notebooks may explore but are not the source of truth.
6. Make seeds, ordering, time zones, and clocks explicit wherever they can affect results.
7. Validate schemas, nullability, uniqueness, ranges, categories, row counts, and output hashes.
8. Run the exemplar twice in separate temporary directories and compare deterministic outputs.
9. Update the matching tutorial or how-to whenever observable behavior changes.

## Preferred Stack

- Use `uv` for environments, locking, and commands.
- Use Pydantic at configuration and external-data boundaries.
- Use Polars for tabular transformations.
- Use Hamilton when the workflow is meaningfully graph-shaped.
- Add Hydra/OmegaConf, fsspec/universal-pathlib, or Banks only when their documented threshold is met.

## Evidence

Tutorials use known inputs and expected outputs. How-to guides include verification. Reference pages describe tested commands and schemas. Never claim a workflow is verified unless its verification command ran successfully.

## Boundaries

- Do not fetch data during the reproduction command.
- Do not include wall-clock timestamps in deterministic result payloads.
- Do not commit secrets, private source data, or large generated artifacts.
- Do not replace an existing project's stack solely to match these preferences.
