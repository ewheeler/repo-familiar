---
name: static-quarto-application
description: Preserve a static Quarto browser client and client-initiated FastAPI request/response boundary. Use when building or changing a Quarto-rendered product interface backed by a Python API.
---

# Static Quarto Application

## Architecture

- Keep the product interface under `app/` and Divio project documentation under `docs/`.
- Render the product to static HTML, CSS, and JavaScript.
- Let browser code initiate ordinary request/response calls to versioned FastAPI endpoints.
- Validate API requests and responses with Pydantic.
- Call the same deterministic application function from batch reproduction and the API.
- Prefer same-origin serving for local and exemplar operation.

## Workflow

1. Identify the rendered application, API route, shared application function, and documented exemplar.
2. Preserve the client-initiated request/response boundary.
3. Add or update API contract tests.
4. Render the Quarto application and test the served artifact, not only source files.
5. Exercise the visible browser interaction and check console errors.
6. Keep the tutorial's input, action, result, and provenance aligned with the browser test.

## Defaults

- No WebSockets, server-sent events, long polling, database, authentication, worker, or server-side rendering unless the product requires it.
- Do not enable permissive CORS. Document split hosting separately with explicit allowed origins.
- Keep generated `_site` output out of version control unless it is an intentional fixture.

## Existing Repositories

Treat existing application source, manifests, locks, CI, and docs as user-owned. Add guidance without claiming ownership or rewriting files unless an explicit adoption workflow records that decision.
