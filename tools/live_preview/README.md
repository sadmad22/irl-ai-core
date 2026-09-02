# IRL AI Core Live Preview

Small, read-only Codespaces preview for inspecting the current research pipeline artifacts.

## Run

From the repository root:

```bash
python3 tools/live_preview/server.py --port 8080
```

Then use the Codespaces **Ports** panel to open port `8080` in the browser.

## Scope

- Standard-library Python only; no new dependencies.
- Read-only: it does not mutate research artifacts or invoke external services.
- Initial project view: `research/expat-health-insurance/`.
- Displays artifacts that are already materialized in the project.
- Article Configuration, Semantic SEO, and Article Structure are shown as not materialized until their contracts are persisted into the research artifact directory.
