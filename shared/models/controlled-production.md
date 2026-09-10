# IRL Controlled Production Run v1

## Purpose

Controlled Production Run is the operational envelope for a limited real-article production run during Phase 6.

It coordinates the existing Article Production Contract, Production Orchestrator, and WordPress Connector without replacing any of their contracts.

Phase 6 is draft-only and requires human approval before publication.

## Required fields

- `run_id`
- `schema_version`
- `project_name`
- `production_id`
- `orchestration_id`
- `status`
- `delivery`
- `human_review`
- `publication`
- `audit`

The Controlled Production Run does **not** accept an independent `topic` field. The article subject is owned by the upstream production artifacts and is not duplicated in this operational envelope.

## Article input authority

For the current v1 production flow, the article input originates from the project workspace:

`research/<project_name>/keyword.json` → `keyword`

That canonical input is consumed by the established research pipeline and propagates into downstream content artifacts, including `primary_keyword` in Content Strategy and Content Brief and the article draft.

`project_name` identifies the project/artifact namespace and is used to locate the project workspace. It is **not** the article topic.

There is currently no separate first-class Article Job Input object above `keyword.json`; this document therefore establishes the existing `keyword.json.keyword` field as the canonical article input for v1 without introducing a new runtime agent or duplicate source of truth.

## Status enum

`queued`, `running`, `ready_for_delivery`, `draft_delivered`, `human_review`, `approved`, `rejected`, or `failed`.

## Delivery

Required fields:

- `status`: `not_started`, `delivered`, or `failed`
- `delivery_id`: connector delivery identifier or `null`
- `post_id`: WordPress post identifier or `null`
- `edit_url`: WordPress edit URL or `null`
- `remote_status`: `draft` or `null`
- `error`: error object or `null`

A successful delivery has `status=delivered`, a positive `post_id`, and `remote_status=draft`.

## Human review

Required fields:

- `required`: always `true`
- `status`: `pending`, `approved`, or `rejected`

A run can become `approved` only after human review approval.

## Publication

Phase 6 is strictly draft-only:

- `mode`: `wordpress_draft`
- `publish`: `false`
- `human_approval_required`: `true`

## Identifiers

- `run_id` must match `^run_[a-f0-9]{16}$`.
- `production_id` must match `^production_[a-f0-9]{16}$`.
- `orchestration_id` must match `^orchestration_[a-f0-9]{16}$`.

## Invariants

1. `schema_version` is exactly `1.0`.
2. `production_id` references an existing Article Production Contract.
3. `orchestration_id` references the corresponding Production Orchestrator result.
4. The Controlled Production Run does not mutate the Article Production Contract.
5. The Controlled Production Run does not replace the Production Orchestrator.
6. The article subject is not duplicated as an independent Controlled Production input.
7. `project_name` remains project/artifact identity and is not treated as the article topic.
8. `publication.mode` is exactly `wordpress_draft`.
9. `publication.publish` is always `false`.
10. `publication.human_approval_required` is always `true`.
11. `draft_delivered`, `human_review`, and `approved` require a delivered WordPress draft.
12. A successful delivery has `delivery.remote_status=draft`.
13. `approved` requires `human_review.status=approved`.
14. `approved` does not authorize or execute WordPress publication.
15. `rejected` requires `human_review.status=rejected`.
16. `failed` records a non-empty failure error.
17. Failure does not erase production lineage.
18. The contract contains no WordPress credentials.
19. Phase 6 does not define scheduling, persistence, dashboard, multi-site support, automatic publication, or a new retry engine.

## Lifecycle

Primary lifecycle:

`queued → running → ready_for_delivery → draft_delivered → human_review → approved`

Alternative terminal paths:

- `human_review → rejected`
- any production state → `failed`

## Boundary

The Article Production Contract owns the validated article payload.

The Production Orchestrator owns production execution and stage checkpoints.

The WordPress Connector owns WordPress draft delivery.

Controlled Production Run owns the limited Phase 6 operational flow and human-review gate.

The project workspace's `keyword.json.keyword` is the canonical v1 article input; downstream artifacts own their propagated `primary_keyword` representation.

## Explicit non-goals

- treating `project_name` as an article topic
- maintaining a second independent topic source in Controlled Production
- automatic WordPress publication
- WordPress credentials
- dashboard implementation
- scheduling
- persistence/database implementation
- multi-site support
- replacement of existing production contracts
- replacement of the Production Orchestrator
