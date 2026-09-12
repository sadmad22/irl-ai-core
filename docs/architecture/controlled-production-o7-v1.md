# Controlled Production O7 v1

## Purpose

Controlled Production v1 is the execution boundary for a traceable, draft-only production run. O7 consumes the canonical Orchestrator production chain and must not reintroduce the legacy Article Production envelope or direct WordPress transport.

## Canonical flow

Dry-run:

`research → intelligence → configuration → structure → draft → editorial_cleanup → media → linking → optimization → qa → production_assembly → article_package → production_delivery_boundary → STOP`

Live controlled delivery:

`research → intelligence → configuration → structure → draft → editorial_cleanup → media → linking → optimization → qa → production_assembly → article_package → production_delivery_boundary → wordpress_delivery → human_review`

The existing O5 non-delivery Orchestrator semantics remain unchanged: `run_production_orchestrator(..., deliver=False)` may terminate at the QA checkpoint. O7 explicitly requests the canonical production chain when it needs Assembly, Package and Delivery Boundary checkpoints.

## Identity

- `orchestration_id` identifies the Orchestrator execution.
- `production_id` remains the existing Controlled Production identity derived compatibly from the validated draft/quality lineage. O7 does not create a legacy Article Production envelope merely to obtain this identifier.
- `run_id` identifies the Controlled Production Run.
- `assembly_id` identifies Production Assembly.
- `package_id` identifies Article Package v1.
- `delivery_id` identifies Production Delivery Boundary.

## Controlled production checkpoints

The Controlled Production Run records a `production_checkpoints` object:

- `assembly_id`: required before `ready_for_delivery`.
- `package_id`: required before `ready_for_delivery`.
- `delivery_id`: required before `ready_for_delivery` because the Delivery Boundary is the canonical hand-off to the adapter, even during dry-run.

The checkpoint object is traceability only. It does not replace the canonical artifacts and does not permit the Controlled Production layer to rebuild them.

## Dry-run invariants

1. No WordPress adapter invocation.
2. No HTTP transport.
3. No credentials.
4. No taxonomy lookup or media upload.
5. Production intent is immutable:
   `{target: wordpress, mode: wordpress_draft, publish: false, human_approval_required: true}`.
6. Assembly, Package and Delivery Boundary must be successfully built and recorded.
7. Run ends at `ready_for_delivery`.
8. `delivery.status` remains `not_started`; `post_id` and `remote_status` remain null.

## Live controlled delivery invariants

1. The exact canonical Production Delivery Boundary result is passed to the WordPress Adapter.
2. The Controlled Production layer does not perform WordPress transport itself.
3. Successful delivery must report a WordPress draft, never a published post.
4. `publish` remains false.
5. Human approval remains mandatory.
6. Run ends at `human_review`.

## Failure semantics

- Assembly failure stops at `production_assembly`.
- Package failure stops at `article_package`.
- Delivery Boundary failure stops at `production_delivery_boundary`.
- Adapter failure stops at `wordpress_delivery`.
- A failure never advances the run to a later stage.

## Legacy isolation

`build_article_production()` and `deliver_wordpress_draft_from_production()` are not part of the O7 execution path. Existing legacy contract tests remain isolated and are not used to construct the canonical Article Package.
