# Phase 10 — Exact Cost per Article

Design checkpoint for per-project DataForSEO cost accounting.

## Accounting model

For a production run, capture a DataForSEO account balance snapshot immediately before research and immediately after research. The exact project cost is the positive decrease in the account balance, rounded to six decimal places. If either snapshot is unavailable, the project cost remains `null` and must not be represented as exact.

The project record should retain both snapshots, the computed delta, the provider, and a timestamp so the calculation is auditable.

## Scope

- DataForSEO provider calls only.
- No fabricated estimates.
- No credentials persisted in project artifacts.
- Existing M7 and test-project working-tree changes remain unrelated.
