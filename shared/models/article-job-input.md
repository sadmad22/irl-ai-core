# IRL Article Job Input v1

## Purpose

This document defines the current v1 source of truth for the article input used by the existing production pipeline.

It is a contract clarification, not a new runtime agent, queue, database, or orchestration layer.

## Canonical input

For an existing project named `<project_name>`, the canonical article input is:

`research/<project_name>/keyword.json` → `keyword`

Example:

`research/expat-health-insurance/keyword.json` contains:

`"keyword": "expat health insurance"`

The remaining fields in `keyword.json` provide keyword research metadata such as search volume, difficulty, CPC, trend, language, and country. They do not replace the `keyword` field as the article subject input.

## Identity semantics

- `project_name` = project/artifact namespace and workspace identifier.
- `keyword.json.keyword` = canonical article input for v1.
- `primary_keyword` = downstream representation propagated into content artifacts.
- `production_id` = identity of the validated Article Production package.
- `orchestration_id` = identity of the Production Orchestrator result.
- `job_id` = identity of Production Job State.
- `run_id` = identity of a Controlled Production Run.

`project_name` must not be interpreted as the article topic merely because the project directory is derived from it.

## Current production lineage

`project_name`
→ `research/<project_name>/keyword.json.keyword`
→ Research Report
→ Decision
→ Content Strategy.primary_keyword
→ Content Brief.primary_keyword
→ Article Draft
→ Article Production Package
→ Production Job / Controlled Production
→ WordPress draft

The downstream production envelopes reference the validated production artifacts and do not need a second independent topic input.

## Article Job boundary

There is currently no separate first-class runtime `Article Job Input` object above `keyword.json` in v1.

Accordingly, v1 establishes the existing project workspace input as the canonical source rather than introducing a duplicate job-input object. A future Article Job contract may formalize this boundary, but that is a separate architectural change and is out of scope for this stabilization step.

## Controlled Production rule

Controlled Production Run does not accept or store an independent `topic` field. It receives the project identity and production lineage from the established pipeline. The article subject remains owned by the upstream production artifacts.

This prevents a caller from supplying a topic that disagrees with the article actually produced by the project pipeline.
