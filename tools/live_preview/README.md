# IRL AI Core Live Preview

Small, read-only Codespaces preview for inspecting the current research pipeline and its real Core contracts.

## Run

From the repository root:

```bash
python3 tools/live_preview/server.py --port 8080
```

Then use the Codespaces **Ports** panel to open port `8080` in the browser.

## Scope

- Read-only Preview adapter; it is not part of the Core contract layer.
- Standard-library Python only; no new dependencies.
- Does not mutate research artifacts.
- Does not create or invoke network providers.
- Initial project view: `research/expat-health-insurance/`.
- Materialized artifacts remain the source of truth when present.
- Article Configuration and Semantic SEO can be resolved through their existing Core builders when their upstream inputs are sufficient; computed contracts are held in memory only.
- Article Structure remains blocked unless an explicit structure policy is supplied upstream because the Core builder requires that policy.
- SERP Analysis remains blocked in the Preview because the Core contract requires an injected SERP provider and the Preview must not create network access.

The Preview therefore reports the real contract state (`available`, `computed`, `blocked`, or `not_available`) instead of fabricating missing artifacts.
