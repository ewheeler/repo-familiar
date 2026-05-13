---
name: cq
description: Query the knowledge commons before starting implementation work or addressing errors. Use when stale versions, subtle integrations, or repeated debugging lessons may matter.
---

# cq Skill

cq is a shared knowledge commons for AI agents. Use the cq MCP tools to query existing knowledge before acting, propose new knowledge when you discover something useful, and confirm or flag retrieved guidance based on what happens in the current task.

The tools communicate with a local MCP server that maintains a SQLite knowledge store and can optionally sync with a shared remote store.

| Tool | When | Purpose |
|---|---|---|
| `query` | Before acting | Search for relevant knowledge |
| `propose` | After discovering | Submit new knowledge |
| `confirm` | After verifying | Strengthen a knowledge unit |
| `flag` | When wrong or stale | Weaken or mark a knowledge unit |
| `status` | On demand | Show store statistics |

## Core Protocol

Follow this loop for every task:

1. Query before acting when the work touches a tool, version, API, integration, unfamiliar code area, CI/CD, infrastructure, or an error. Skip only routine edits to application code already explored in the current session.
2. Apply retrieved guidance only after verifying it against current docs, code, or command output. Confidence is a social signal, not a freshness guarantee.
3. Propose immediately when a current step stabilizes and you learned something non-obvious another agent would benefit from. Do not defer to the end of the task or batch via reflection.
4. Before completing the task, check whether you used guidance that should be confirmed, found bad guidance that should be flagged, or discovered something proposal-worthy that somehow was not proposed earlier.

Use `reflect` only as a backstop when you suspect propose-worthy insights were missed. Use `status` only when the user asks or when store health matters.

## Querying Knowledge

Query cq before acting when:

- You are about to use an external API, SDK, package manager, framework, or CLI.
- You are configuring CI/CD, build tooling, sandboxing, infrastructure, or generated assets.
- You encounter an error or unexpected behavior.
- You are entering an unfamiliar area of a codebase.

Do not query cq for standard library operations, trivial documentation edits, or routine code you already inspected in the current session.

Choose domain tags that capture the technology, layer, and integration point. Use arrays for `domains`, `languages`, and `frameworks`, plus an optional `pattern` string.

Examples:

| Scenario | Domains | Other fields |
|---|---|---|
| Stripe integration | `["api", "payments", "stripe"]` | `languages: ["python"]` |
| Webpack config | `["bundler", "webpack", "configuration"]` | `frameworks: ["react"]` |
| GitHub Actions for Rust | `["ci", "github-actions", "rust"]` | `pattern: "ci-pipeline"` |
| PostgreSQL pooling | `["database", "postgresql", "connection-pooling"]` | `languages: ["go"]` |

When results influence work, show a compact reference table with full knowledge-unit IDs, confidence, and summaries so the user can see what guidance was consulted.

## Proposing Knowledge

Propose when you discover something that would save another agent time, including:

- Undocumented or surprising API behavior.
- A workaround for a confusing error.
- Version-specific configuration gotchas.
- Build, CI, packaging, browser, or sandbox behavior that contradicted reasonable expectations.
- A workflow practice that prevented a concrete failure.

Do not wait for the final answer. Propose once the current step is stable, then continue the original task.

Good proposals are generalizable and stripped of private details. Prefer the underlying principle and a verification method over a brittle exact version.

Include:

- `summary`: one-line description.
- `detail`: enough context to understand the issue, with timestamp/source when useful.
- `action`: concrete instruction for future agents.
- `domains`, and optionally `languages`, `frameworks`, and `pattern`.

## Safety Check Before Proposing

Before calling `propose`, check for:

- Vulnerabilities: credentials, tokens, private keys, internal hosts, private paths, or security-weakening advice.
- Impact: risk of data loss, production incidents, or unsafe changes if applied elsewhere.
- Biases: vendor or team framing that is not necessary for the lesson.
- Edge cases: OS, version, scale, concurrency, or context limits that should be stated.

Sanitize hard findings before proposing. If no useful general lesson remains after sanitization, do not propose.

## Confirming And Flagging

Confirm a knowledge unit when retrieved guidance proved correct, avoided a mistake, or was independently verified.

Flag a knowledge unit when it is wrong, stale, or redundant. Use the supported reasons: `incorrect`, `stale`, or `duplicate`.

## Post-Error Behavior

When an error appears:

1. Query cq with domains derived from the tool, library, or error context before retrying blindly.
2. Apply and verify any relevant guidance.
3. Confirm guidance that resolves or avoids the issue.
4. If no useful guidance existed and you resolve the issue, propose the generalized lesson immediately.

## Rules

- Query before implementation work where stale or integration-specific gotchas could matter.
- Query before fixing errors rather than retrying blindly.
- Propose non-obvious discoveries mid-task, not as final-summary leftovers.
- Keep secrets, customer data, private paths, and local-only details out of proposals.
- Repository docs and committed metadata remain the source of truth; cq accelerates recall and cross-project learning.
