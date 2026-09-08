# IRL AI Core — Production Orchestrator v1

## Audit

The repository already contains the production-oriented content pipeline and a `core_orchestrator.py`, but the latter is a decision/recovery orchestrator rather than the production pipeline coordinator. The established content pipeline already performs the real component chaining through Research, Content Brief/Intelligence, Article Draft, quality gates, SEO validation, Editorial Review, Publication Gate, Publisher, and WordPress Draft Delivery. Phase 3 therefore adds a thin production orchestration boundary instead of rebuilding those components.

The existing Article Production Contract from Phase 2 is the downstream hand-off and remains unchanged.

## Purpose

Production Orchestrator v1 provides one deterministic execution boundary around the existing Core pipeline. It records the ordered production stages, captures completed stage checkpoints, stops on the first failed stage, preserves the accumulated outputs, and can resume by starting at a named stage when a compatible stage runner is supplied.

## Stage order

1. `research`
2. `intelligence`
3. `configuration`
4. `structure`
5. `draft`
6. `editorial_cleanup`
7. `media`
8. `linking`
9. `optimization`
10. `qa`
11. `article_package`

These are orchestration boundaries. Existing agents remain the owners of their internal work.

## Final fields

- `orchestration_id`
- `project_name`
- `schema_version`
- `lifecycle_stage`
- `current_stage`
- `completed_stages`
- `remaining_stages`
- `lineage`
- `article_package`
- `error`
- `audit`

## Enums

`lifecycle_stage`:
- `running`
- `completed`
- `failed`

`current_stage`:
- one of the eleven ordered stage names, or `null` after completion/failure before a stage starts

## Invariants

1. Stage order is fixed and deterministic.
2. A stage is added to `completed_stages` only after its runner returns successfully.
3. Execution stops at the first stage runner exception.
4. Failed execution preserves already completed stages and outputs.
5. No later stage is executed after a failure.
6. `article_package` exists only when the pipeline reaches `article_package` successfully.
7. The Article Production Contract is built from the existing Article Draft and Article Draft Quality outputs; it is not redefined here.
8. `production_id` is deterministic for the same validated Article Draft and Quality pair.
9. Resume starts at an explicit stage and never silently skips required earlier stages unless their outputs are already supplied by the caller.
10. The orchestrator performs no WordPress authentication, transport, or publishing.
11. The orchestrator does not implement persistent Production Job State; that is Phase 4.

## Existing pipeline integration

The default runner delegates to the established `run_content_research_to_wordpress_draft` pipeline. The orchestrator derives stage checkpoints from its returned artifacts and then constructs the Phase 2 Article Production Contract after QA has passed.

This keeps Phase 3 focused on coordination while preserving existing component ownership.

## Explicit non-goals

- Production Job State persistence
- retry policy beyond controlled resume entry
- WordPress Connector implementation
- WordPress credentials
- automatic publishing
- dashboard or scheduling
- new providers or dependencies
- replacement of `core_orchestrator.py`
