# Pilot Agent Plugins as an optional export format

## Status

Accepted. The skills-only `repository-map` exporter is implemented; compatible-client installation validation remains pending.

## Context

Agent Plugins 1.0.0 defines a portable directory layout for Agent Skills and MCP server configuration. It does not define installation, activation, updates, permissions, provenance, signatures, or client-specific user experience. It also cannot represent most Agentic Engineering Defaults, including `AGENTS.md`, profiles, project documentation, plans, or Bootstrap Metadata.

The existing Project Generator and Vendored Generated Assets model remains broader and provides repository ownership, provenance, checksums, and preview-first refresh behavior that the plugin specification does not replace.

## Decision

Treat Agent Plugins as an optional derived export format, not the primary downstream delivery model.

The first pilot adds `export-plugin`, which renders the canonical `repository-map` skill into this fixed package:

```text
plugin.json
skills/
  repository-map/
    SKILL.md
```

The export targets the pinned Agent Plugins 1.0.0 manifest schema. It contains no MCP configuration, client extension, Bootstrap Metadata, or duplicate canonical skill source. The canonical input remains `src/repo_familiar/templates/skills/repository-map/`.

Compatible clients still own installation and activation. The exporter creates a package directory only; it does not mutate a Downstream Repository or machine-level client configuration.

## Consequences

- New repository generation and Existing Repository Bootstrap continue writing selected skills under `.agents/skills/`.
- Agent Plugin exports do not participate in `.repo-familiar/bootstrap.yml`, `check`, or `upgrade`.
- Additional skills require Agent Skills conformance and redistribution review before becoming exportable.
- Portable MCP export remains deferred until non-secret profiles can be mapped without relying on client-specific fields or credential interpolation.
- Broader adoption should follow successful installation tests in at least two compatible clients and stable conformance tooling.

## References

- [Agent Plugins Specification](https://agent-plugins.org/specification)
- [Build an Agent Plugin](https://agent-plugins.org/plugin-authors)
- [Agent Skills Specification](https://agentskills.io/specification)
