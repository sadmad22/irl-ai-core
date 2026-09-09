# IRL AI Core — Production Job & Status v1

## Audit

The production roadmap requires Phase 4 to give each article a trackable Article Job ID, record the current status and stage, capture primary errors, and expose publication readiness. Phase 3 deliberately excluded persistent Production Job State, so no existing job-state implementation is being replaced.

The existing Production Orchestrator remains the execution coordinator. The Article Production Contract remains the validated production payload. Phase 4 adds only the operational state representation and its status transition/projection rules.

## Contract

Production Job State is the operational tracking envelope for one article production run. It is intentionally smaller than Article Production Contract and contains no article content.

Required fields:

- `job_id`
- `schema_version`
- `status`
- `current_stage`
- `lineage`
- `error`
- `ready_to_publish`
- `audit`

## Final status enum

`queued`, `researching`, `building`, `drafting`, `editing`, `optimizing`, `qa`, `ready`, `published`, `failed`.

## Final stage enum

`research`, `intelligence`, `configuration`, `structure`, `draft`, `editorial_cleanup`, `media`, `linking`, `optimization`, `qa`, `article_package`, or `null`.

## Status → stage mapping

| Status | Allowed current stage |
|---|---|
| `queued` | `null` |
| `researching` | `research` |
| `building` | `intelligence`, `configuration`, `structure` |
| `drafting` | `draft` |
| `editing` | `editorial_cleanup` |
| `optimizing` | `media`, `linking`, `optimization` |
| `qa` | `qa` |
| `ready` | `article_package` |
| `published` | `null` |
| `failed` | the failed production stage |

## Invariants

1. Every job has a stable opaque `job_id` matching `^job_[a-f0-9]{16}$`.
2. `schema_version` is exactly `1.0`.
3. `lineage.project_name` is mandatory; existing orchestration and production IDs may be attached without duplicating their contracts.
4. `ready_to_publish` is derived from status: only `ready` is `true`.
5. `queued` and `published` have no active stage.
6. A failed job records the exact failed stage and a non-empty error type/message.
7. Failure state does not erase lineage or imply downstream completion.
8. `ready` means the Article Production Contract is ready for the later WordPress hand-off; it does not publish anything.
9. `published` is a state representation only. WordPress publication is outside this Phase 4 engine.
10. State changes do not execute research, content generation, QA, WordPress transport, or publication.
11. The Phase 4 state machine does not define a retry policy. Recovery/resume behavior remains governed by the production execution layer.

## Engine responsibilities

- create an initial `queued` job
- validate job identifiers
- advance a job through the roadmap status machine
- reject invalid status/stage combinations
- record terminal failure information
- project an existing Production Orchestrator record into the operational Job State

## Boundary

`Production Orchestrator` owns execution and stage checkpoints.

`Production Job State` owns the externally trackable status representation.

`Article Production Contract` owns the validated content payload.

`WordPress Connector` is not implemented here and remains Phase 5.

## Explicit non-goals

- database/persistence backend selection
- dashboard
- scheduling
- WordPress authentication or API calls
- automatic publication
- retry policy implementation
- new providers or dependencies
- changes to the existing Production Orchestrator
