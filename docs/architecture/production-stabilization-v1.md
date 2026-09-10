# IRL Production Stabilization Audit v1

## Purpose

Production Stabilization is a validation layer over the existing production contracts. It verifies that the Article Production Contract, Production Orchestrator, Production Job State, Controlled Production Run, and WordPress delivery result remain internally consistent after real production runs.

It does not replace or modify any of those components, does not execute production work, and does not publish to WordPress.

## Scope

Phase 7 is limited to:

- analyzing observed production failures and boundary mismatches;
- validating Article Package integrity;
- validating orchestration completion and lineage;
- validating Production Job State projection and lineage;
- validating Controlled Production delivery and human-review state;
- validating WordPress draft-only publication invariants;
- returning a deterministic stabilization audit result.

No new content engine, dashboard, scheduler, persistence layer, multi-site support, retry engine, or automatic publication is introduced.

## Audit inputs

The audit accepts the existing records:

- `article_package`
- `orchestration`
- `production_job`
- `controlled_production`

The audit is read-only with respect to those records.

## Required output fields

- `stabilization_id`
- `schema_version`
- `project_name`
- `production_id`
- `orchestration_id`
- `job_id`
- `run_id`
- `outcome`
- `checks`
- `audit`

## Enums

`outcome`:

- `passed`
- `blocked`

Each check status:

- `passed`
- `failed`

## Invariants

1. `schema_version` is exactly `1.0`.
2. All five input records must be dictionaries.
3. `article_package.lifecycle_stage` is exactly `production_ready`.
4. Article package publication is exactly `wordpress_draft`, with `publish=false` and `human_approval_required=true`.
5. `production_id` must match across Article Package and Controlled Production.
6. `orchestration_id` must match across Orchestrator and Controlled Production.
7. `job_id` must match Production Job State.
8. Production Job lineage must preserve the production and orchestration identifiers when present.
9. A completed orchestration must have an Article Package and no orchestration error.
10. A ready Production Job must correspond to an Article Package and `article_package` stage.
11. A Controlled Production run after `ready_for_delivery` must report `delivery.status=delivered`, `post_id>=1`, and `remote_status=draft`.
12. `human_review.required` is always `true`, and its status must match the Controlled Production lifecycle state.
13. Controlled Production publication remains draft-only regardless of human-review state.
14. `approved` means human review was satisfied; it does not authorize or execute WordPress publication.
15. Failed checks produce `outcome=blocked` and preserve the identifiers needed for diagnosis.
16. The stabilization result contains no credentials.
17. The audit does not mutate any input record.

## Determinism

`stabilization_id` is deterministic from the project and the four primary identifiers plus schema version.

## Boundary

The existing contracts remain authoritative. Phase 7 only observes and validates their outputs.

## Explicit non-goals

- changing the production orchestrator API;
- changing the Article Production Contract;
- changing WordPress publication authority;
- automatic retries;
- automatic publication;
- persistence/database implementation;
- dashboard implementation;
- multi-site support;
- new content-generation agents.
