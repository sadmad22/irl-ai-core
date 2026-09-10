# IRL Controlled Production Run v1

## Purpose

Controlled Production Run is the operational envelope for a limited real-article production run during Phase 6.

It coordinates the existing Article Production Contract, Production Orchestrator, and WordPress Connector without replacing any of their contracts.

Phase 6 is draft-only and requires human approval before publication.

## Required fields

- `run_id`
- `schema_version`
- `project_name`
- `topic`
- `production_id`
- `orchestration_id`
- `status`
- `delivery`
- `human_review`
- `publication`
- `audit`

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
6. `publication.mode` is exactly `wordpress_draft`.
7. `publication.publish` is always `false`.
8. `publication.human_approval_required` is always `true`.
9. `draft_delivered`, `human_review`, and `approved` require a delivered WordPress draft.
10. A successful delivery has `delivery.remote_status=draft`.
11. `approved` requires `human_review.status=approved`.
12. `approved` does not authorize or execute WordPress publication.
13. `rejected` requires `human_review.status=rejected`.
14. `failed` records a non-empty failure error.
15. Failure does not erase production lineage.
16. The contract contains no WordPress credentials.
17. Phase 6 does not define scheduling, persistence, dashboard, multi-site support, automatic publication, or a new retry engine.

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

## Explicit non-goals

- automatic WordPress publication
- WordPress credentials
- dashboard implementation
- scheduling
- persistence/database implementation
- multi-site support
- replacement of existing production contracts
- replacement of the Production Orchestrator
