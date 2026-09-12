# IRL AI Core — Orchestrator WordPress Adapter Integration v1

## 1. Purpose

O6 defines the final orchestration hand-off from the canonical Production Delivery Boundary v1 to the existing WordPress Delivery Adapter.

The Orchestrator coordinates the hand-off only. It does not implement WordPress transport or any WordPress-specific discovery or credential behavior.

## 2. Canonical hand-off

```text
Production Assembly
        ↓
Article Package
        ↓
Production Delivery Boundary
        ↓
WordPress Delivery Adapter
        ↓
WordPress Draft
        ↓
human_review
```

The Adapter MUST receive the canonical `ProductionDeliveryBoundaryResult` produced by the Delivery Boundary. The Orchestrator MUST NOT construct a parallel WordPress request.

## 3. Orchestrator responsibilities

The Orchestrator MUST:

1. execute the Delivery Boundary before WordPress delivery;
2. pass the complete canonical boundary result to `deliver_wordpress_delivery_boundary`;
3. pass the configured connection and transport dependencies through the adapter boundary without inspecting or handling credentials;
4. record the adapter result as the `wordpress` production checkpoint;
5. resolve successful controlled WordPress delivery to `human_review` only when the remote status is `draft` and the immutable publication policy is preserved.

## 4. Adapter ownership

The WordPress Delivery Adapter owns the WordPress-specific conversion and delivery boundary, including:

- conversion of the canonical boundary request to WordPress REST payload fields;
- validation of resolved taxonomy and media platform identities;
- explicit SEO metadata field mapping;
- invocation of the existing WordPress draft delivery client;
- verification that the remote result remains a draft.

The Orchestrator MUST NOT duplicate these responsibilities.

## 5. Forbidden Orchestrator behavior

The Orchestrator MUST NOT:

- call the WordPress HTTP client directly;
- handle usernames, application passwords, or credentials;
- resolve WordPress taxonomy IDs;
- upload or resolve WordPress media IDs;
- discover or repair links;
- perform Web, DataForSEO, LLM, or external discovery calls for delivery;
- set `publish=true`;
- convert `wordpress_draft` into another publication mode;
- bypass Production Assembly, Article Package, or Production Delivery Boundary.

## 6. Failure semantics

If the Adapter or WordPress delivery client fails, the Orchestrator MUST fail-stop at `wordpress_delivery`.

No publish transition is available in v1. A successful remote WordPress response must report `remote_status=draft` and preserve:

```json
{
  "publish": false,
  "human_approval_required": true
}
```

## 7. Traceability

A successful controlled hand-off must preserve:

- `orchestration_id`;
- `assembly_id`;
- `package_id`;
- `delivery_id`;
- required lineage;
- WordPress platform post identity;
- remote draft status.

The adapter integration is complete only when the resulting orchestration state can terminate in `human_review` with publication still prohibited.

## 8. O6 acceptance criteria

- The canonical Delivery Boundary result is passed unchanged to the WordPress Adapter boundary.
- The adapter is the only WordPress-specific delivery entry point used by the Orchestrator.
- Connection and transport dependencies are forwarded to the adapter and never consumed by Orchestrator logic.
- Adapter failure stops the run at `wordpress_delivery`.
- A successful live delivery resolves to `human_review` only for a remote draft.
- `publish=false` and `human_approval_required=true` remain immutable.
- No direct WordPress transport, credential handling, taxonomy lookup, media upload, or external discovery exists in the Orchestrator.
- Existing Adapter, Delivery Boundary, Article Package, and Assembly engines remain unchanged.
