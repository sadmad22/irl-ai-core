# IRL AI Core

AI Operating System for Insurance Review Lab.

## Operator Web UI

The primary operator experience is the browser UI. It hides the internal JSON artifacts and pipeline commands behind a single project form and live gate dashboard.

Start it from the repository root:

```bash
python3 scripts/web_ui.py --host 0.0.0.0 --port 8080
```

Then open the Cloud Shell port preview for **8080**.

The UI lets you enter:

- Project name
- Primary keyword
- Language
- Country
- Research provider
- Delivery mode

**LIVE WordPress Draft is the default mode.** The UI calls the established production pipeline and only accepts a WordPress response whose status is `draft`. There is no Publish action or publish code path.

### Research provider control

The **Research Provider** panel controls the provider for keyword metrics and SERP collection for each run:

- **DataForSEO — LIVE research**: production research provider.
- **Mock — testing only**: local/test provider; it does not represent live research data.

DataForSEO credentials are never entered into the UI and never written to project artifacts. The production environment must provide:

```bash
export DATAFORSEO_LOGIN="<dataforseo-login>"
export DATAFORSEO_PASSWORD="<dataforseo-password>"
```

Optional base URL:

```bash
export DATAFORSEO_BASE_URL="https://api.dataforseo.com"
```

The UI shows whether DataForSEO is configured, but never displays the credential values. The provider can also be selected per run without changing project files.

The UI also creates the minimal `research/<project>/keyword.json` and `metadata.json` for a genuinely new project. Existing projects are reused when their keyword matches.

## CLI production entry point

The CLI remains available for diagnostics and automation:

```bash
python3 scripts/run_pipeline.py m7-consultant-liability
```

For the verified live WordPress Draft path:

```bash
export WORDPRESS_BASE_URL="https://insurancereviewlab.com"
export WORDPRESS_USERNAME="InsuranceReviewLab"
export WORDPRESS_APPLICATION_PASSWORD="<application-password>"
python3 scripts/run_pipeline.py m7-consultant-liability --deliver
```

`--deliver` is fail-closed: the required WordPress credentials must exist, and the generated request must have `status=draft`. The pipeline has no publish path.

## Validation

Run the full test suite before production delivery:

```bash
pytest -q
```

The operator UI is intended to be the normal human-facing workflow; the CLI is the lower-level production/diagnostic entry point.
