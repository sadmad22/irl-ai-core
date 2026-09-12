# IRL AI Core — Orchestrator Integration Contract v1

## 1. Contract status

This document is the normative integration contract for connecting the existing production stages to the canonical production chain:

```text
Production Artifacts
        ↓
Production Assembly v1
        ↓
Article Package v1
        ↓
Production Delivery Boundary v1
        ↓
WordPress Delivery Adapter
        ↓
WordPress Draft
```

This step defines orchestration boundaries and contracts only. It does **not** implement the Orchestrator, define the final orchestration JSON Schema, or change the existing Assembly, Article Package, Delivery Boundary, or WordPress Adapter engines.

The existing Orchestrator currently contains a legacy `build_article_production()` path and does not explicitly coordinate Production Assembly, Production Delivery Boundary, and WordPress Delivery. O1 replaces that legacy coordination path conceptually with the canonical chain; implementation is deferred to O5/O6.

## 2. Scope

### In scope

- Canonical production stage sequence.
- Stage inputs, outputs, required artifacts, success/failure conditions, and next transition.
- Canonical artifact-name normalization between upstream production artifacts and Production Assembly.
- Lineage propagation.
- Immutable production intent.
- Boundary ownership between Orchestrator, Assembly, Article Package, Delivery Boundary, and WordPress Adapter.
- Legacy article-package path replacement requirement.
- Fail-stop and controlled-resume expectations.

### Out of scope

- Research implementation.
- LLM, Web, DataForSEO, or external discovery implementation.
- Article generation or rewriting.
- Media generation/materialization implementation.
- Link discovery.
- Taxonomy creation or arbitrary taxonomy assignment.
- WordPress HTTP implementation.
- Credential handling.
- Automatic publishing.
- Orchestrator schema implementation (O3).
- Test implementation (O4).

## 3. Canonical stage sequence

The Orchestrator MUST use this ordered sequence:

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

No downstream production stage may execute before all required preceding stages have completed successfully.

## 4. Stage contract

| Stage | Primary input | Required output/artifact | Success | Failure | Next |
|---|---|---|---|---|---|
| `research` | Topic / production request | `research_report` | Valid research result exists | Research cannot produce a valid result | `intelligence` |
| `intelligence` | Research result | Intelligence/decision artifact | Required intelligence decision exists | Intelligence artifact missing/invalid | `configuration` |
| `configuration` | Intelligence + project requirements | Configuration/brief inputs | Configuration is valid | Required configuration unavailable/invalid | `structure` |
| `structure` | Configuration | Article structure/brief | Required structure is valid | Structure missing/invalid | `draft` |
| `draft` | Structure + approved upstream context | `article_draft` | Article Draft reaches its ready state | Draft generation/validation fails | `editorial_cleanup` |
| `editorial_cleanup` | `article_draft` + editorial inputs | `editorial_review` | Editorial Review is approved and validated | Review fails or remains unapproved | `media` |
| `media` | Article structure/content + media strategy | `media` / materialized image assets | Required delivery media is materialized with valid `asset_ref` and alt text | Required media is missing/unmaterialized/invalid | `linking` |
| `linking` | Article + approved link inputs | `linking` | Internal/external link arrays are valid | Link artifact missing/invalid | `optimization` |
| `optimization` | Article + SEO inputs | `optimization` | Final `seo_title` and `meta_description` exist | Required optimization values missing/invalid | `qa` |
| `qa` | Draft + quality + claim audit + publication gate | `quality`, `claim_audit`, publication gate state | Quality and claim gates pass and publication gate allows output | Any required QA gate fails | `production_assembly` |
| `production_assembly` | Canonical mapped production artifacts | `ProductionAssemblyResult` | Assembly lifecycle reaches `production_assembly_ready` | Any assembly invariant fails | `article_package` |
| `article_package` | `ProductionAssemblyResult` | `ArticlePackage` | Package lifecycle reaches `delivery_ready` | Package contract/readiness fails | `production_delivery_boundary` |
| `production_delivery_boundary` | `ArticlePackage` | `ProductionDeliveryBoundaryResult` | Boundary produces a valid draft-only request | Package not delivery-ready or boundary validation fails | `wordpress_delivery` |
| `wordpress_delivery` | Canonical delivery-boundary result | WordPress draft delivery result | WordPress confirms draft creation/update | Adapter/connector delivery fails | `human_review` |

`human_review` is the terminal controlled-production state for v1. It is not an auto-publish stage.

## 5. Upstream artifact normalization

The Orchestrator is responsible for explicit mapping into the Production Assembly input contract. It MUST NOT silently rename, invent, regenerate, or substitute values.

```text
article_draft_quality → quality
seo_validation        → optimization
media_strategy        → media
internal_linking      → linking.internal
external_linking      → linking.external
```

The complete Assembly input MUST be represented as:

```json
{
  "article_draft": "<validated artifact>",
  "quality": "<validated artifact>",
  "claim_audit": "<validated artifact>",
  "editorial_review": "<validated artifact>",
  "optimization": "<validated artifact>",
  "media": "<validated artifact>",
  "linking": "<validated artifact>",
  "taxonomy": "<validated artifact>",
  "production_intent": "<immutable intent>",
  "lineage": "<preserved lineage>"
}
```

The values above are placeholders for contract shape only; the Orchestrator must pass actual validated artifacts during implementation.

## 6. Production intent

Production intent is immutable across the complete production path.

The only valid v1 production intent is exactly:

```json
{
  "target": "wordpress",
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

The Orchestrator MUST:

1. establish this intent before downstream production packaging;
2. preserve it without mutation;
3. reject any conflicting intent;
4. never convert `wordpress_draft` into a publish operation;
5. never pass `publish=true` into Assembly, Package, Boundary, or Adapter integration.

## 7. Lineage contract

Lineage is a mandatory cross-boundary concern.

### Required lineage

The minimum lineage identifiers are:

```text
report_id
decision_id
strategy_id
brief_id
draft_id
quality_id
```

Optional stage lineage identifiers may be preserved when supplied by the production artifacts, including configuration, semantic, optimization, image, alt-text, internal-link, external-link, or news identifiers.

### Propagation rule

```text
Research
  ↓
Decision / Strategy / Brief
  ↓
Article Draft
  ↓
Quality / Editorial / Optimization / Media / Linking
  ↓
Production Assembly
  ↓
Article Package
  ↓
Production Delivery Boundary
  ↓
WordPress Delivery
```

A downstream stage MUST preserve the lineage received from upstream. It may add valid stage-specific lineage identifiers, but it may not remove, overwrite, or fabricate required lineage.

The final orchestration result MUST retain enough lineage to trace a WordPress draft back to the originating research and article-production artifacts.

## 8. Stage completion truthfulness

The Orchestrator may mark a stage complete only when its corresponding required artifact/state exists and satisfies that stage's contract.

In particular:

- `editorial_cleanup` is not complete merely because `article_draft` exists.
- `media` is not complete merely because a media specification exists; delivery-capable media must be materialized.
- `linking` is not complete merely because article prose contains links; the canonical linking artifact must exist.
- `optimization` is not complete without final delivery optimization values.
- `qa` is not complete unless the required quality, claim-audit, and publication-gate conditions pass.
- `production_assembly` is not complete until lifecycle is `production_assembly_ready`.
- `article_package` is not delivery-complete until lifecycle is `delivery_ready`.
- `production_delivery_boundary` is not complete until it has produced a valid draft-only delivery representation.
- `wordpress_delivery` is not complete until the target confirms draft creation/update.

## 9. Downstream boundary rules

### 9.1 Production Assembly

The Orchestrator supplies the ten required Assembly domains. Production Assembly owns deterministic validation, normalization, readiness, and its own lifecycle.

The Orchestrator MUST NOT duplicate Assembly validation logic.

### 9.2 Article Package

The Article Package Engine is the canonical package builder and validator.

The Orchestrator MUST replace the legacy `build_article_production()` coordination path with the canonical Article Package Engine after successful Production Assembly.

The Orchestrator MUST NOT construct a parallel package representation.

### 9.3 Production Delivery Boundary

The Delivery Boundary consumes only a delivery-ready Article Package.

The Orchestrator MUST NOT bypass the Package Engine or construct a WordPress request directly.

The Boundary owns conversion of the validated package into the canonical delivery request and preserves the immutable draft-only publication policy.

### 9.4 WordPress Delivery Adapter

The Adapter consumes the canonical Production Delivery Boundary result.

The Orchestrator MUST NOT:

- perform HTTP requests;
- handle credentials;
- upload media;
- resolve WordPress taxonomy IDs;
- discover links;
- generate or rewrite content;
- generate images;
- publish.

Those concerns remain owned by their established downstream boundary/adapter components.

## 10. Lifecycle and transition contract

The Orchestrator lifecycle is governed by the ordered production stages.

Conceptually:

```text
running
  ↓
qa passed
  ↓
production_assembly_ready
  ↓
package delivery_ready
  ↓
delivery boundary ready
  ↓
wordpress draft delivered
  ↓
human_review
```

A failure at any stage produces a fail-stop result:

```text
running → failed
```

The failed stage becomes the current stage and no later stage is executed.

### Resume rule

Resume is permitted only from a previously successful checkpoint when all required earlier stage checkpoints and artifacts are present and valid. Resume MUST continue from the failed/incomplete stage; it MUST NOT skip required stages.

## 11. Required integration invariants

1. **Ordered execution:** stages execute only in canonical order.
2. **No Package before Assembly:** Article Package cannot execute before successful `production_assembly`.
3. **No Boundary before Package:** Production Delivery Boundary cannot execute before Article Package reaches `delivery_ready`.
4. **No WordPress delivery before Boundary:** WordPress Adapter cannot execute before a valid Delivery Boundary result exists.
5. **Draft-only:** `publish` is always `false`.
6. **Human gate:** `human_approval_required` is always `true`.
7. **No stage skipping:** failed or missing earlier stages block downstream execution.
8. **Lineage preservation:** required lineage cannot be lost across boundaries.
9. **No silent substitution:** missing artifacts cannot be replaced with inferred or fabricated values.
10. **No duplicate engine logic:** the Orchestrator coordinates existing engines; it does not reimplement them.
11. **No direct transport:** the Orchestrator never talks directly to WordPress.
12. **No external discovery in integration:** the Orchestrator does not perform Web, DataForSEO, link discovery, taxonomy discovery, or media discovery to repair missing inputs.
13. **No credential ownership:** credentials remain outside the Orchestrator.
14. **No automatic publishing:** v1 has no publish transition.
15. **Deterministic boundary use:** downstream identifiers and readiness states come from their canonical engines, not from ad-hoc Orchestrator reconstruction.
16. **Fail closed:** any required downstream invariant failure blocks the next boundary.

## 12. Legacy path retirement

The current Orchestrator contains:

```python
from shared.utils.article_production_contract import build_article_production
```

and currently creates an `article_package` directly from Article Draft + Quality.

This path is legacy for the new production chain.

O5 MUST remove this coordination dependency from the canonical production path and replace it with:

```text
Production Assembly
        ↓
Article Package Engine
        ↓
Production Delivery Boundary
        ↓
WordPress Delivery Adapter
```

The legacy helper must not remain an alternate route that can bypass Assembly, Package readiness, Delivery Boundary, or the WordPress Adapter.

## 13. Failure ownership

| Failure | Owner | Orchestrator response |
|---|---|---|
| Research artifact invalid | Research stage | Stop at `research` |
| Intelligence/configuration/structure unavailable | Corresponding stage | Stop at failed stage |
| Draft invalid | Draft stage | Stop at `draft` |
| Editorial review not approved | Editorial stage | Stop at `editorial_cleanup` |
| Media not materialized/invalid | Media stage / Assembly gate | Stop before Package readiness |
| Linking invalid | Linking stage | Stop at `linking` |
| SEO values invalid | Optimization / QA | Stop before Assembly |
| Quality/Claim Audit/Publication Gate fails | QA | Stop at `qa` |
| Assembly invariant fails | Production Assembly | Stop at `production_assembly` |
| Package contract/readiness fails | Article Package Engine | Stop at `article_package` |
| Delivery Boundary validation fails | Production Delivery Boundary | Stop at `production_delivery_boundary` |
| WordPress delivery fails | WordPress Adapter / Connector | Stop at `wordpress_delivery` |

The Orchestrator records the failure; it does not repair a missing downstream contract by performing the responsibility of another component.

## 14. Controlled-production completion

A successful v1 controlled-production run must be traceable through:

```text
orchestration_id
assembly_id
package_id
delivery_id
lineage
post_id / platform identity
remote draft status
```

The final state is:

```text
human_review
```

and publication remains prohibited.

## 15. Implementation boundary for O5/O6

The implementation following this contract is intentionally limited to orchestration wiring:

```text
Existing production stages
        ↓
Orchestrator artifact mapping
        ↓
build_production_assembly(...)
        ↓
build_article_package(...)
        ↓
build_production_delivery_boundary(...)
        ↓
WordPress Delivery Adapter
```

The implementation MUST reuse the existing canonical engines and their contracts. It MUST NOT alter their internal behavior merely to simplify orchestration.

## 16. Acceptance criteria for O1

O1 is complete when:

- the canonical stage sequence is explicitly defined;
- every stage has a documented input/output/success/failure/next contract;
- Assembly input mapping is explicit;
- lineage requirements and propagation are explicit;
- production intent is immutable and draft-only;
- the legacy `build_article_production()` route is identified for retirement from the canonical path;
- ownership boundaries prevent direct WordPress transport from the Orchestrator;
- fail-stop and controlled-resume expectations are defined;
- no implementation code or schema changes are introduced as part of O1.

## 17. Next step

After review and acceptance of this contract, proceed to **O2 — Final Fields / Enums / Invariants**.

O2 must finalize the orchestration state machine and invariants before O3 schema work begins.
