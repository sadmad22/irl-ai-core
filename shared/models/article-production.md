# IRL Article Production Contract v1

## Purpose

The Article Production Contract is the single validated hand-off from IRL AI Core to the future WordPress Connector.

It is an integration envelope, not a second content engine and not a replacement for the existing artifact contracts.

## Required top-level fields

- `production_id`: deterministic identifier for this production result.
- `schema_version`: contract version, currently `1.0`.
- `lifecycle_stage`: must be `production_ready`.
- `lineage`: immutable identifiers connecting the production result to the existing Core pipeline.
- `article`: the validated Article Draft payload.
- `quality`: the validated Article Draft Quality payload.
- `publication`: controlled WordPress delivery intent.
- `audit`: production-contract validation metadata.

## Lineage

Required identifiers:

- `report_id`
- `decision_id`
- `strategy_id`
- `brief_id`
- `draft_id`
- `quality_id`

Optional downstream identifiers are allowed only when the corresponding capability has produced them:

- `config_id`
- `semantic_id`
- `optimization_id`
- `image_spec_id`
- `alt_text_id`
- `external_links_id`
- `internal_links_id`
- `news_id`

The contract must never invent lineage identifiers.

## Article

`article` is the existing Article Draft contract. It is embedded as the canonical content payload rather than reimplemented with a second shape.

## Quality

`quality` is the existing Article Draft Quality contract. A production result cannot be `production_ready` unless quality outcome is `passed` and its validation status is `validated`.

## Publication

Initial production is draft-only:

- `mode`: `wordpress_draft`
- `publish`: `false`
- `human_approval_required`: `true`

The connector may create or update a WordPress Draft, but publication remains outside this contract's authority.

## Invariants

1. `production_id` is deterministic from the stable production inputs.
2. `schema_version` is exactly `1.0`.
3. `lifecycle_stage` is exactly `production_ready`.
4. All six mandatory lineage identifiers are non-empty.
5. `article.draft_id` equals `lineage.draft_id`.
6. `quality.quality_id` equals `lineage.quality_id`.
7. `quality.draft_id` equals `lineage.draft_id`.
8. `quality.outcome` is `passed`.
9. `quality.audit.validation_status` is `validated`.
10. `publication.publish` is `false`.
11. `publication.human_approval_required` is `true`.
12. The production contract contains no WordPress credentials.
13. The production contract does not mutate or replace ResearchReport history.

## Explicit non-goals

This contract does not define:

- production job state
- retry policy
- WordPress API transport
- authentication credentials
- automatic publication
- a new content-generation engine
- a replacement for existing Core artifact schemas
