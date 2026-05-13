---
name: rodney-browser
description: Use Rodney for persistent Chrome automation, shell-scripted web checks, screenshots, JavaScript assertions, and accessibility tree queries.
---

# Rodney Browser Automation

Use this skill when browser checks need persistent Chrome state, shell-scriptable assertions, screenshots, PDF capture, JavaScript evaluation, or accessibility tree inspection.

Rodney is a CLI that drives a persistent Chrome instance through the Chrome DevTools Protocol. Each command connects to the same running browser, does one operation, then disconnects.

## Install Or Build

Follow the current upstream instructions from `https://github.com/simonw/rodney`.

At time of writing, Rodney requires Go 1.21+ and Chrome or Chromium. If building from source:

```bash
go build -o rodney .
```

If Chrome is not in the default location, set `ROD_CHROME_BIN=/path/to/chrome`.

## Typical Flow

```bash
rodney start --local
rodney open "http://127.0.0.1:5360/"
rodney waitstable
rodney title
rodney screenshot -w 1440 -h 1000 screenshot.png
rodney stop
```

Use `--local` for project-scoped browser state in `./.rodney/`. Add `.rodney/` to `.gitignore`.

## Useful Checks

```bash
rodney exists "h1"
rodney visible "#main-content"
rodney assert 'document.title' 'Expected Title'
rodney js 'document.querySelectorAll("a").length'
rodney text "h1"
rodney html "main"
```

Rodney uses distinct exit codes:

- `0`: success
- `1`: check failed
- `2`: command error

This makes it useful for shell-scripted smoke tests.

## Accessibility Tree

```bash
rodney ax-tree --depth 3
rodney ax-find --role button --json
rodney ax-node "#submit" --json
```

Use accessibility tree queries to verify accessible names, roles, landmarks, and headings. Treat this as a browser-level check, not a complete accessibility audit.

## Rules

- Prefer `--local` sessions for repo-specific checks and keep `.rodney/` ignored.
- Record URL, viewport, command sequence, and failing assertion in task output.
- Stop browser sessions when done unless persistence is intentional.
- Do not commit screenshots, PDFs, or browser state unless the project explicitly treats them as artifacts.
- Do not use browser automation to bypass authentication, scrape private data, or persist secrets.
