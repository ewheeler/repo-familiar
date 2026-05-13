---
name: grill-with-docs
description: Stress-test plans against project language, documented decisions, and existing code before implementation.
---

# Grill With Docs

Use this skill when a project plan needs to be challenged against repository language, decisions, and implementation reality.

## Workflow

1. Read `CONTEXT.md`, `plan.md`, and relevant docs.
2. Ask one precise question at a time.
3. Recommend an answer with tradeoffs.
4. Update project documentation as decisions crystallize.
5. Offer ADRs only for decisions that are hard to reverse, surprising without context, and the result of a real tradeoff.

## Rules

- Prefer existing project terminology over new terms.
- Call out ambiguity immediately.
- Do not overwrite user-owned docs without explicit approval.
- Keep decisions close to the documents that explain them.
