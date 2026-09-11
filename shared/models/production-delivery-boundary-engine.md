# Production Delivery Boundary Engine v1

## Purpose

The Production Delivery Boundary Engine is the fail-closed engine that converts a validated Article Package v1 into a deterministic Production Delivery Boundary v1 record.

It is the implementation of the accepted Production Delivery Boundary contract. It does not perform WordPress HTTP I/O and does not replace the delivery adapter.

## Inputs

The engine accepts:

- one Article Package v1;
- `publisher_id`;
- `adapter_id`;
- `execution_mode` (`dry_run` or `live`).

The Article Package must already be `delivery_ready`, schema `1.0`, audit `validated`, and carry immutable WordPress draft-only publication intent.

## Outputs

The engine returns a validated boundary containing:

- deterministic `delivery_id` derived from package, adapter, target and contract version;
- exact package binding;
- immutable draft-only publication policy;
- complete request representation for content, tables, media, links, optimization and taxonomy;
- validated lifecycle/status state;
- boundary audit state.

The initial engine state is `delivery_ready` / `ready`. The engine never claims that a platform write occurred. `request_ready`, `delivering`, `delivered_as_draft`, `human_review`, and `failed` are operational states for subsequent adapter/delivery work.

## Invariants enforced

- Article Package is the only source of production content.
- Package must be delivery-ready and validated.
- Source package identity must match boundary package identity.
- Delivery identity is deterministic.
- Publication is immutable `wordpress_draft` with `publish=false` and human approval required.
- Request status is always `draft`.
- All required media must be materialized and carry `asset_ref` and non-empty alt text.
- Media platform identity is not fabricated by the engine.
- Tables are preserved as structured content and required for comparison/buyer-guide packages.
- Links are explicit, HTTP(S), typed internal/external, and never discovered.
- Final SEO values are copied from the package; they are not regenerated.
- Taxonomy names are copied from the package; platform IDs are not invented.
- Claim grounding must already be complete.
- Inputs are deep-copied; the engine does not mutate the source package.
- Schema validation and cross-domain validation both run before success.
- No network calls, image generation, taxonomy mutation, publication, retry orchestration, or auto-repair occur here.

## Failure model

Failures use stable machine-readable codes and fail closed. The engine must never return a successful boundary when a required package domain or invariant is missing or invalid.

## Boundary with the adapter

```text
Article Package v1
       |
       v
Production Delivery Boundary Engine v1
       |
       v
validated Delivery Boundary
       |
       v
WordPress Delivery Adapter
       |
       v
WordPress REST Transport
```

The adapter remains responsible for platform-specific resolution and serialization details that require WordPress capabilities. The engine is not an HTTP client and must not be expanded into one.
