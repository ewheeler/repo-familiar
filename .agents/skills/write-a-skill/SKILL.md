---
name: write-a-skill
description: Reference for writing and editing skills well — the vocabulary and principles that make a skill predictable. Use when user wants to create, write, or build a new skill.
disable-model-invocation: true
---

A skill exists to wrangle determinism out of a stochastic system. **Predictability** — the agent taking the same _process_ every run, not producing the same output — is the root virtue; every lever below serves it.

## Invocation

Two choices, trading different costs:

- A **model-invoked** skill keeps a **description**, so the agent can fire it autonomously _and_ other skills can reach it (you can still type its name too). It contributes to **context load** — the description sits in the window every turn.
- A **user-invoked** skill strips the description from the agent's reach: only you, typing its name, can invoke it — and no other skill can. Zero context load, but it spends **cognitive load**: _you_ are the index that must remember it exists.

Pick model-invocation only when the agent must reach the skill on its own, or another skill must. If it only ever fires by hand, make it user-invoked and pay no context load.

## Writing the description

A model-invoked **description** does two jobs — state what the skill is, and list the **branches** that should trigger it. Every word increases **context load**, so a description earns even harder pruning than the body:

- **Front-load the skill's leading word** — the description is where it does its invocation work.
- **One trigger per branch.** Synonyms that rename a single branch are **duplication** — collapse them.
- **Cut identity that's already in the body.** Keep the description to triggers, plus any "when another skill needs…" reach clause.

## Information hierarchy

A skill is built from two content types — **steps** and **reference** — that mix freely. The core decision is which to use and where each sits on the **information hierarchy**, a ladder ranked by how immediately the agent needs the material:

1. **In-skill step** — an ordered action in `SKILL.md`, the primary tier: what the agent does, in order. Each step ends on a **completion criterion**, the condition that tells the agent the work is done.
2. **In-skill reference** — a definition, rule, or fact in `SKILL.md`, consulted on demand.
3. **External reference** — reference pushed out of `SKILL.md` into a separate file, reached by a **context pointer**, loaded only when the pointer fires.

**Progressive disclosure** is the move down the ladder — out of `SKILL.md` into a linked file — so the top stays legible. Some skills are used in more than one way, and each distinct way is a **branch** — different runs taking different paths through the skill.

## When to split

**Granularity** is how finely you divide skills, and each cut spends one of the two loads, so split only when the cut earns it. Two cuts:

- **By invocation** — split off a **model-invoked** skill when you have a distinct **leading word** that should trigger it on its own, or another skill must reach it.
- **By sequence** — split a run of **steps** when the steps still ahead tempt the agent to rush the one in front of it (**premature completion**).

## Pruning

Keep each meaning in a **single source of truth**: one authoritative place, so changing the behaviour is a one-place edit.

Check every line for **relevance**: does it still bear on what the skill does?

Then hunt **no-ops** sentence by sentence: run the no-op test on each sentence in isolation, and when one fails, delete the whole sentence rather than trim words from it.

## Leading words

A **leading word** is a compact concept already living in the model's pretraining that the agent thinks with while running the skill. Repeated throughout the text, it accumulates a distributed definition and anchors a whole region of behaviour in the fewest tokens, by recruiting priors the model already holds.

## Failure modes

- **Premature completion** — ending a step before it's genuinely done, attention slipping to _being done_.
- **Duplication** — the same meaning in more than one place.
- **Sediment** — stale layers that settle because adding feels safe and removing feels risky.
- **Sprawl** — a skill simply too long, even when every line is live and unique.
- **No-op** — a line the model already obeys by default, so you pay load to say nothing.
