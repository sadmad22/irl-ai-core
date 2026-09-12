# IRL AI Core — Orchestrator Integration v1
## O2 — Final Fields, Enums & Invariants

This document is the normative O2 contract for the Orchestrator Integration layer. It fixes the exact orchestration fields, enums, lifecycle transitions, hand-off invariants, lineage rules, production intent, failure/resume semantics, ownership boundaries, and safety constraints. O2 introduces no runtime behavior.

## 1. Canonical stage enum

The only valid executable stages, in this exact order:

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

`human_review` is a terminal lifecycle state, not an executable stage.

## 2. Orchestration root

The canonical orchestration result contains:

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

`orchestration_id` is deterministic and matches `^orchestration_[a-f0-9]{16}$`. `project_name` is non-empty. `schema_version` is exactly `1.0`.

## 3. Lifecycle enum and terminal-state semantics

Allowed lifecycle values:

```text
running
failed
completed
human_review
```

`running` and `failed` are execution/checkpoint states. `completed` and `human_review` are terminal states with distinct meanings:

- `running`: execution is active or resumable; `current_stage` is valid, incomplete, and the first item in `remaining_stages`.
- `failed`: execution stopped at `current_stage`; `error` is required; the failed and all downstream stages remain incomplete.
- `completed`: all executable stages required by the selected **non-delivery orchestration mode** are complete, with `remaining_stages=[]` and `current_stage=null`. This state never authorizes publication and is not the terminal state of controlled WordPress production.
- `human_review`: all 14 canonical executable stages have completed successfully, WordPress draft creation/update has been confirmed, `wordpress_delivery` is complete, `remaining_stages=[]`, `current_stage=null`, and `error=null`. Publication remains prohibited and human approval is still required.

For terminal states, `current_stage=null`. In controlled WordPress production, successful completion MUST resolve to `human_review`, never `completed`.

## 4. Checkpoint invariants

1. `completed_stages` is unique and in canonical order.
2. `remaining_stages` is unique and in canonical order.
3. No stage appears in both arrays.
4. A stage is complete only when its required artifact/state satisfies its contract.
5. A downstream artifact cannot retroactively prove upstream completion.
6. Failed stages cannot be silently skipped.
7. Resume requires valid predecessor checkpoints and artifacts.
8. Resume cannot bypass a required predecessor.

## 5. Canonical transitions

```text
research → intelligence → configuration → structure → draft
→ editorial_cleanup → media → linking → optimization → qa
→ production_assembly → article_package
→ production_delivery_boundary → wordpress_delivery → human_review
```

A successful stage advances only to its declared successor. Failure stops execution. No backward or automatic retry transition exists in v1.

For non-delivery orchestration, the terminal transition is `... → completed` once the selected non-delivery stage set is complete. For controlled WordPress production, the canonical terminal transition is `wordpress_delivery → human_review`.

## 6. Stage readiness

- `research`: valid production request/topic and `research_report`.
- `intelligence`: valid intelligence/decision artifact.
- `configuration`: valid configuration/brief inputs.
- `structure`: valid article structure/brief.
- `draft`: Article Draft ready state.
- `editorial_cleanup`: approved and validated `editorial_review`.
- `media`: materialized delivery-capable media with valid `asset_ref`, alt text, prompt, placement, and section references.
- `linking`: canonical internal/external linking artifacts.
- `optimization`: final `seo_title` and `meta_description`.
- `qa`: passing quality, claim-audit, and publication-gate conditions.
- `production_assembly`: all ten Assembly domains and `production_assembly_ready`.
- `article_package`: successful Assembly and Package `delivery_ready`.
- `production_delivery_boundary`: valid draft-only delivery representation.
- `wordpress_delivery`: confirmed WordPress draft creation/update.
- `human_review`: confirmed WordPress delivery with publication prohibited.

## 7. Production Assembly hand-off

Exactly these ten domains are supplied:

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

Explicit upstream normalization:

```text
article_draft_quality → quality
seo_validation → optimization
media_strategy → media
internal_linking → linking.internal
external_linking → linking.external
```

The Orchestrator may map names but must not alter meaning, fabricate values, or silently substitute missing artifacts.

## 8. Immutable production intent

The only valid v1 intent is exactly:

```json
{
  "target": "wordpress",
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

Conflicting intent is rejected, not normalized. No downstream stage may mutate it. `publish=true` is invalid at every production boundary. v1 contains no publish transition.

## 9. Lineage

Required lineage identifiers:

```text
report_id
decision_id
strategy_id
brief_id
draft_id
quality_id
```

Optional valid identifiers may include:

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

Required lineage cannot be removed, overwritten, or fabricated. Conflicting lineage invalidates the hand-off. Downstream stages may add valid stage-specific lineage. Final state must trace the WordPress draft to originating research and production artifacts.

## 10. Production result ownership

```text
production.assembly → Production Assembly Engine
production.package → Article Package Engine
production.boundary → Production Delivery Boundary Engine
production.wordpress → WordPress Delivery Adapter / Connector
```

The Orchestrator coordinates and records these results; it does not reimplement their validation or transport logic.

## 11. Boundary invariants

1. No Package before Assembly reaches `production_assembly_ready`.
2. No Boundary before Package reaches `delivery_ready`.
3. No WordPress delivery before a valid Boundary result.
4. No `human_review` without confirmed WordPress delivery.
5. No publish transition.

## 12. Failure and controlled resume

Failure produces:

```text
lifecycle_stage = failed
current_stage = <failed stage>
error = { stage, type, message }
```

The failed stage and every downstream stage remain incomplete; no downstream artifact may be fabricated. Valid upstream checkpoints remain available for controlled resume.

A valid resume requires a canonical `start_stage`, complete and contract-valid predecessors, revalidated production intent, and revalidated lineage. Resume never skips Assembly, Package, Boundary, or WordPress Delivery.

## 13. External-system ownership

The Orchestrator must not own WordPress HTTP transport, credentials, media upload, taxonomy platform-ID resolution, link discovery, taxonomy creation, image generation/materialization, downstream LLM/Web/DataForSEO discovery, or publishing.

## 14. Legacy-path invariant

`build_article_production()` is not part of the canonical chain. O5 must replace direct legacy package construction with:

```text
build_production_assembly
        ↓
build_article_package
        ↓
build_production_delivery_boundary
        ↓
WordPress Delivery Adapter
```

O2 does not delete the legacy function; it defines that it is outside the canonical path.

## 15. Safety invariants

- No auto-publish.
- `publish=true` never crosses a production boundary.
- Human approval remains mandatory.
- No direct WordPress transport or credentials in the Orchestrator.
- No platform-specific media/taxonomy identity fabrication.
- No silent artifact substitution.
- No fabricated lineage or `asset_ref`.
- No downstream reconstruction to fill package gaps.
- No mutation of caller-owned canonical artifacts as an orchestration side effect.
- No destructive Git operation is part of O2.

## 16. O3/O4 acceptance criteria

O3 must encode these rules without inventing new production semantics. O4 must deterministically test: happy path to `human_review`; non-delivery completion to `completed`; Assembly/Package/Boundary/WordPress failure stops; `publish=true` rejection; missing lineage rejection; resume cannot bypass predecessors; ordered/disjoint checkpoints; and legacy `build_article_production()` isolation.

## 17. O2 Definition of Done

Fields, enums, lifecycle transitions, hand-off rules, lineage, production intent, failure/resume semantics, ownership, and safety invariants are deterministic and implementation-ready for O3 schema design. O2 introduces no runtime behavior changes.
