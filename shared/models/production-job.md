# IRL Production Job State Contract v1

## Audit

Phase 3 explicitly deferred persistent Production Job State to Phase 4. The repository has no existing Production Job State model or engine, so Phase 4 adds the missing state boundary without replacing the Production Orchestrator or Article Production Contract.

The production roadmap defines the required observable states: `queued`, `researching`, `building`, `drafting`, `editing`, `optimizing`, `qa`, `ready`, `published`, and `failed`.

## Purpose

Production Job State gives every article a trackable `Article Job ID`, records its current production status and stage, captures the primary failure when execution stops, and exposes whether the article is ready for publication.

## Final fields

- `job_id`
- `schema_version`
- `status`
- `current_stage`
- `lineage`
- `error`
- `ready_to_publish`
- `audit`

## Status enum

- `queued`
- `researching`
- `building`
- `drafting`
- `editing`
- `optimizing`
- `qa`
- `ready`
- `published`
- `failed`

## Stage mapping

- `queued` → no active stage (`null`)
- `researching` → `research`
- `building` → `intelligence`, `configuration`, or `structure`
- `drafting` → `draft`
- `editing` → `editorial_cleanup`
- `optimizing` → `media`, `linking`, or `optimization`
- `qa` → `qa`
- `ready` → `article_package`
- `published` → no active stage (`null`)
- `failed` → the stage where the failure occurred

## Invariants

1. `job_id` is a stable opaque identifier matching `^job_[a-f0-9]{16}$`.
2. `schema_version` is exactly `1.0`.
3. `lineage.project_name` is always present; `orchestration_id` and `production_id` are optional references to existing contracts.
4. `ready_to_publish` is `true` only for `ready`; every other status is `false`.
5. `queued` and `published` have no active production stage.
6. Every non-failed active status maps to an allowed production stage according to the fixed mapping above.
7. `failed` records the exact stage that failed and a non-empty error type/message.
8. A failed job preserves its lineage and does not imply that later stages completed.
9. `ready` represents readiness only; it does not publish anything.
10. `published` is a state record only. Actual WordPress publication remains outside Phase 4 and belongs to the later production/connector flow.
11. The Job State does not perform research, drafting, QA, WordPress transport, or publication.

## Boundary

Production Job State sits beside the Production Orchestrator. The orchestrator owns execution; the Job State owns the externally trackable status representation. The Article Production Contract remains the validated production payload handed to the future WordPress Connector.

## Explicit non-goals

- WordPress API integration
- authentication or credentials
- automatic publishing
- dashboard or scheduling
- persistence backend/database selection
- retry policy beyond recording failure state
- replacement of the Production Orchestrator
- new dependencies
