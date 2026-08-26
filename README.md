# IRL AI Core

AI Operating System for Insurance Review Lab.

## Production entry point

Run from the repository root:

```bash
python3 scripts/run_pipeline.py m7-consultant-liability
```

The default mode is a **dry run**. It executes the Research/Content pipeline through the WordPress Draft contract and performs no network delivery.

For the already-verified live WordPress Draft path:

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

For a single project, use the dry run first, inspect the gate output, then use `--deliver` only when the resulting WordPress post is intended to remain a Draft for human review.
