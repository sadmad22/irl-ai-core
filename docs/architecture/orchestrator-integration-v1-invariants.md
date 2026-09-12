# IRL AI Core — Orchestrator Integration v1
# Final Fields, Enums & Invariants

## 1. Contract status

This document is the normative field-, enum-, lifecycle-, and invariant-level contract for the Orchestrator Integration v1 layer.

It operationalizes `docs/architecture/orchestrator-integration-v1.md` without implementing the Orchestrator, its JSON Schema, tests, or downstream engines.

O2 establishes the exact orchestration state model that O3 will encode as JSON Schema and O4 will enforce through tests.

## 2. Scope

### In scope

- Orchestration root fields.
- Stage identity and lifecycle enums.
- Stage transition rules.
- Production-chain ordering.
- Artifact hand-off invariants.
- Lineage invariants.
- Immutable production intent.
- Failure and resume semantics.
- Downstream result ownership.
- Safety invariants required before O5/O6 implementation.

### Out of scope

- JSON Schema implementation (O3).
- Test implementation (O4).
- Orchestrator code changes (O5).
- WordPress adapter integration (O6).
- Research, LLM, Web, DataForSEO, media generation, link discovery, taxonomy creation, or transport implementation.

## 3. Canonical stage enum

The only valid production stages are, in this exact order:

```text
research
intelligence
configuration
structure
draft
editorial_cleanup
media
linking
optimization
qa
production_assembly
article_package
production_delivery_boundary
wordpress_delivery
```

The stage order is authoritative. A stage may not execute before all required predecessor stages have completed successfully.

`human_review` is a terminal lifecycle state, not an executable production stage in v1.

## 4. Orchestration root contract

The canonical orchestration result is an object with these domains:

```text
orchestration_id
project_name
schema_version
lifecycle_stage
current_stage
completed_stages
remaining_stages
lineage
production
error
audit
```

### 4.1 Identity fields

| Field | Type | Required | Constraint |
|---|---|---:|---|
| `orchestration_id` | string | yes | deterministic; pattern `^orchestration_[a-f0-9]{16}$` |
| `project_name` | string | yes | non-empty |
| `schema_version` | string | yes | exactly `1.0` |

`orchestration_id` is derived deterministically from the project identity, completed stage set, lineage, and schema version. It is not a random attempt identifier.

### 4.2 Lifecycle fields

| Field | Type | Required | Constraint |
|---|---|---:|---|
| `lifecycle_stage` | string | yes | enum defined in §5 |
| `current_stage` | string/null | yes | valid stage when active/failed; null when terminal |
| `completed_stages` | array[string] | yes | unique; canonical order; subset of stage enum |
| `remaining_stages` | array[string] | yes | unique; canonical order; complement of completed stages for an active/failed run |

## 5. Orchestration lifecycle enum

The valid lifecycle states are:

```text
running
failed
completed
human_review
```

### Semantics

- `running`: execution is active or a resumable production chain is in progress.
- `failed`: a stage failed; execution stopped at that stage; downstream stages are not completed.
- `completed`: all executable production stages completed successfully. In controlled production this state is reached only when WordPress draft delivery has succeeded and the result has transitioned to the human approval boundary; therefore O5 may represent the delivery outcome through the production result while the overall terminal state is `human_review`.
- `human_review`: terminal controlled-production state after a WordPress draft is confirmed. No automatic publish transition exists.

### v1 terminal-state rule

For controlled WordPress production, the normative successful terminal state is:

```text
lifecycle_stage = human_review
current_stage = null
remaining_stages = []
```

`completed` is retained as a generic orchestration lifecycle value for non-delivery execution contexts and schema compatibility, but it MUST NOT be used to imply publication.

## 6. Current-stage rules

### `running`

- `current_stage` MUST be a valid stage.
- `current_stage` MUST NOT be in `completed_stages`.
- `current_stage` MUST be the first item in `remaining_stages`.

### `failed`

- `current_stage` MUST be the stage that failed.
- `current_stage` MUST NOT be in `completed_stages`.
- `current_stage` MUST be the first item in `remaining_stages`.
- `error` MUST be present.
- No later stage may be marked completed.

### `human_review`

- `current_stage` MUST be null.
- `remaining_stages` MUST be empty.
- `wordpress_delivery` MUST be in `completed_stages`.
- `error` MUST be null.
- Publication remains prohibited.

### `completed`

- `current_stage` MUST be null.
- `remaining_stages` MUST be empty.
- All executable stages MUST be in `completed_stages`.
- `error` MUST be null.
- `completed` MUST NOT be interpreted as permission to publish.

## 7. Stage checkpoint invariants

1. `completed_stages` contains each stage at most once.
2. `completed_stages` preserves canonical stage order.
3. `remaining_stages` preserves canonical stage order.
4. No stage may appear in both arrays.
5. The union of `completed_stages` and `remaining_stages` is the complete canonical stage set, except that a currently running/failed stage remains in `remaining_stages` until successful completion.
6. A stage is complete only when its required artifact/state satisfies the stage contract.
7. A downstream artifact does not retroactively prove an upstream stage completed.
8. Failed stages cannot be silently skipped.
9. Resume is permitted only from a failed or resumable checkpoint whose predecessor checkpoints are complete and whose supplied artifacts remain valid.
10. Resume cannot jump over a required stage.

## 8. Canonical stage transitions

The only forward transitions are:

```text
research
  → intelligence
  → configuration
  → structure
  → draft
  → editorial_cleanup
  → media
  → linking
  → optimization
  → qa
  → production_assembly
  → article_package
  → production_delivery_boundary
  → wordpress_delivery
  → human_review
```

A successful stage advances to exactly its declared successor.

A failed stage transitions to `failed` and stops execution.

No backward transition is defined in v1.

No automatic retry transition is defined in the contract; retry/resume behavior is controlled externally by an explicit resume operation using valid checkpoints.

## 9. Stage readiness invariants

### Upstream stages

- `research` requires a valid production request/topic and produces `research_report`.
- `intelligence` requires a valid research result and produces the required intelligence/decision artifact.
- `configuration` requires valid intelligence and project requirements.
- `structure` requires valid configuration and produces valid article structure/brief.
- `draft` requires valid structure and produces an Article Draft in its ready state.
- `editorial_cleanup` requires the Article Draft and approved editorial inputs; completion requires an approved, validated `editorial_review`.
- `media` requires the article/media strategy and delivery-capable materialized media; completion requires valid materialized image assets, `asset_ref`, alt text, prompt, placement, and section references.
- `linking` requires canonical internal/external linking artifacts; prose alone does not satisfy the stage.
- `optimization` requires final delivery values, including `seo_title` and `meta_description`.
- `qa` requires passing quality and claim-audit gates and an allowed publication gate.

### Canonical production boundaries

- `production_assembly` requires all ten canonical Assembly input domains.
- `article_package` requires a successful Production Assembly result.
- `production_delivery_boundary` requires an Article Package whose lifecycle is `delivery_ready`.
- `wordpress_delivery` requires a valid draft-only Production Delivery Boundary result.
- `human_review` requires confirmed WordPress draft creation/update.

## 10. Production boundary ordering invariants

The following rules are absolute:

1. **No Package before Assembly.** `article_package` cannot execute unless `production_assembly` completed with `production_assembly_ready`.
2. **No Boundary before delivery-ready Package.** `production_delivery_boundary` cannot execute unless the Article Package lifecycle is exactly `delivery_ready`.
3. **No WordPress delivery before Boundary.** `wordpress_delivery` cannot execute unless a valid Production Delivery Boundary result exists.
4. **No human-review state without WordPress delivery.** `human_review` requires confirmed draft delivery.
5. **No publish transition.** v1 contains no publish stage or publish transition.

## 11. Canonical Assembly input fields

The Orchestrator MUST construct exactly these ten top-level domains for Production Assembly:

```text
article_draft
quality
claim_audit
editorial_review
optimization
media
linking
taxonomy
production_intent
lineage
```

Explicit upstream normalization is:

```text
article_draft_quality → quality
seo_validation        → optimization
media_strategy        → media
internal_linking      → linking.internal
external_linking      → linking.external
```

The Orchestrator may map field names, but it may not alter artifact meaning or silently fill missing values.

## 12. Production intent invariant

The only valid v1 production intent is exactly:

```json
{
  "target": "wordpress",
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

The following are mandatory invariants:

1. `target` MUST equal `wordpress`.
2. `mode` MUST equal `wordpress_draft`.
3. `publish` MUST equal `false`.
4. `human_approval_required` MUST equal `true`.
5. The Orchestrator MUST reject conflicting intent rather than normalize it.
6. No downstream stage may mutate the intent.
7. `publish=true` is invalid at every production boundary.
8. WordPress draft delivery does not authorize publication.

## 13. Lineage contract

### Required lineage

Every production orchestration must preserve:

```text
report_id
decision_id
strategy_id
brief_id
draft_id
quality_id
```

### Optional lineage

When present and valid, the Orchestrator may preserve:

```text
config_id
semantic_id
optimization_id
image_spec_id
alt_text_id
external_links_id
internal_links_id
news_id
```

### Invariants

1. Required lineage IDs may not be removed.
2. Required lineage IDs may not be overwritten by downstream identifiers.
3. Required lineage IDs may not be fabricated.
4. Conflicting lineage between artifacts invalidates the orchestration hand-off.
5. Downstream components may add valid stage-specific lineage.
6. Final orchestration state must retain enough lineage to trace the WordPress draft to the originating research and article-production artifacts.

## 14. Production result ownership

The Orchestrator result contains a `production` domain with these logical outputs:

```text
production.assembly
production.package
production.boundary
production.wordpress
```

Ownership is strict:

| Domain | Producer | Orchestrator responsibility |
|---|---|---|
| `assembly` | Production Assembly Engine | Coordinate and record result |
| `package` | Article Package Engine | Coordinate and record result |
| `boundary` | Production Delivery Boundary Engine | Coordinate and record result |
| `wordpress` | WordPress Delivery Adapter / Connector | Coordinate and record delivery result |

The Orchestrator must not reimplement the validation or transport logic owned by these components.

## 15. Failure contract

A failed stage must produce:

```text
lifecycle_stage = failed
current_stage = <failed stage>
error = {
  stage,
  type,
  message
}
```

Failure invariants:

- The failing stage remains incomplete.
- All downstream stages remain incomplete.
- No downstream artifact may be fabricated to make the run appear complete.
- Existing valid upstream artifacts remain available for controlled resume.
- A failure at Assembly blocks Package, Boundary, and WordPress delivery.
- A failure at Package blocks Boundary and WordPress delivery.
- A failure at Boundary blocks WordPress delivery.
- A failure at WordPress delivery blocks human-review completion.

## 16. Controlled resume contract

Resume is checkpoint-based and fail-closed.

A valid resume requires:

1. A known `start_stage` from the canonical stage enum.
2. Every predecessor stage is present in `completed_stages`.
3. Required predecessor artifacts are supplied and remain contract-valid.
4. The resume does not bypass a failed stage or any missing predecessor.
5. Production intent is revalidated and remains the immutable draft-only intent.
6. Lineage is revalidated before downstream execution.

Resume does not authorize skipping Assembly, Package, Boundary, or WordPress Delivery.

## 17. External-system ownership invariants

The Orchestrator MUST NOT own:

- WordPress HTTP transport.
- WordPress credentials.
- WordPress media upload.
- WordPress taxonomy platform-ID resolution.
- Link discovery.
- Taxonomy creation.
- Image generation/materialization.
- LLM calls for downstream boundary construction.
- Web or DataForSEO discovery for downstream boundary construction.
- Publishing.

The Orchestrator only coordinates explicit artifacts and invokes the existing boundary components.

## 18. Legacy-path invariant

The legacy `build_article_production()` path is not part of the canonical production chain.

O5 MUST replace the current direct legacy package construction with:

```text
build_production_assembly
        ↓
build_article_package
        ↓
build_production_delivery_boundary
        ↓
WordPress Delivery Adapter
```

The legacy function may remain available for backward compatibility only if it is isolated from the canonical Orchestrator production path. O2 does not delete or modify that function.

## 19. Non-negotiable safety invariants

1. No auto-publish.
2. `publish=true` must never cross a production boundary.
3. Human approval remains mandatory.
4. No direct WordPress transport from the Orchestrator.
5. No credential handling inside the Orchestrator.
6. No platform-specific media or taxonomy identity fabrication.
7. No silent artifact substitution.
8. No fabricated lineage.
9. No fabricated `asset_ref`.
10. No downstream reconstruction from research artifacts to compensate for missing package data.
11. No mutation of caller-owned canonical artifacts as a side effect of orchestration.
12. No destructive Git operation is part of this implementation step.

## 20. O3/O4 acceptance criteria

O2 is complete when O3 can encode these rules without inventing additional production semantics and O4 can test them deterministically.

Minimum O4 scenarios implied by this contract:

- canonical happy path reaches `human_review` after confirmed draft delivery;
- Assembly failure stops before Package;
- Package failure stops before Boundary;
- Boundary failure stops before WordPress delivery;
- WordPress delivery failure prevents `human_review`;
- invalid `publish=true` intent is rejected;
- missing required lineage is rejected;
- resume cannot bypass a predecessor stage;
- completed and remaining stages remain ordered and disjoint;
- legacy `build_article_production()` is not used by the canonical path.

## 21. Definition of Done for O2

O2 is complete when this document provides a deterministic, implementation-ready field/enum/invariant contract for the Orchestrator Integration layer, with no unresolved production semantics required to begin O3 schema design.

O2 does not modify runtime behavior. Runtime enforcement begins with O4/O5 according to the production plan.
