# IRL Production Orchestrator Contract v1

## Purpose

Coordinate the existing Core content pipeline into one production execution boundary.

The orchestrator is a coordinator, not a replacement for the existing agents and not a second Production Job State system.

## Ordered stages

`research → intelligence → configuration → structure → draft → editorial_cleanup → media → linking → optimization → qa → article_package`

## Execution record

Required fields:

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

## Lifecycle

- `running`: execution is in progress or has produced a partial checkpoint.
- `completed`: all stages completed and Article Production Contract exists.
- `failed`: a stage failed; completed outputs remain available.

## Failure semantics

The first failing stage stops execution. The error is captured without replacing successful outputs from earlier stages.

## Resume semantics

A caller may resume from an explicit stage only when the required upstream outputs are already available in the supplied context. The orchestrator never silently invents missing outputs.

## Boundary

The orchestrator may consume and coordinate existing agents and the Phase 2 Article Production Contract builder. It does not implement WordPress authentication, transport, publication, persistent job state, or new content-generation capabilities.
