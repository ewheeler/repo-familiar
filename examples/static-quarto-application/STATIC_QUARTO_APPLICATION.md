# Static Quarto Application Contract

- `app/` is the static product client; `docs/` is the Divio project documentation site.
- Browser interactions initiate ordinary request/response calls to versioned FastAPI routes.
- Pydantic validates request and response boundaries.
- Batch reproduction and the API call the same `analyze()` function.
- Same-origin serving is the default. Split hosting requires an explicit CORS allow-list.

The initial template intentionally excludes authentication, databases, workers, WebSockets, server-sent events, long polling, and server-side rendering.

## Run Locally

```bash
uv sync --frozen
quarto render app
uv run uvicorn static_quarto_application.api:app --reload
```

Open `http://127.0.0.1:8000` and submit the form.
