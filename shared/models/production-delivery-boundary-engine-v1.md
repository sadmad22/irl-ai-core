# Production Delivery Boundary Engine v1

The engine implements the accepted Production Delivery Boundary v1 contract as a fail-closed, deterministic boundary builder.

## Scope

It consumes one validated Article Package v1 plus `publisher_id`, `adapter_id`, and `execution_mode` and returns a validated Production Delivery Boundary v1 record.

It enforces:

- Article Package `delivery_ready`, schema `1.0`, audit `validated`;
- exact package source binding;
- deterministic `delivery_id`;
- immutable WordPress draft-only publication intent;
- complete content, table, media, link, optimization, and taxonomy domains;
- materialized required media and non-empty alt text;
- grounded claims;
- explicit HTTP(S) links only;
- JSON Schema plus cross-domain validation;
- input immutability.

The engine performs no network I/O, media upload, taxonomy mutation, publication, discovery, generation, retry orchestration, or auto-repair.

## Lifecycle boundary

The engine produces the initial `delivery_ready` / `ready` state. It never claims a platform write. Adapter and delivery layers own subsequent `request_ready`, `delivering`, `delivered_as_draft`, `human_review`, and `failed` operational states.

## Architecture

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
