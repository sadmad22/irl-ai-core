# IRL Production Assembly v1

## Purpose

Production Assembly v1 is the deterministic boundary that normalizes explicit upstream production artifacts into the canonical input set consumed by the Article Package Engine.

It is an assembly layer, not an editorial, research, discovery, generation, transport, or publishing layer.

## Input fields

The input object contains exactly these top-level domains:

- `article_draft`
- `quality`
- `claim_audit`
- `editorial_review`
- `optimization`
- `media`
- `linking`
- `taxonomy`
- `production_intent`
- `lineage`

All ten domains are required.

## Output fields

`ProductionAssemblyResult` contains:

- `assembly_id`: deterministic identifier matching `^assembly_[a-f0-9]{16}$`.
- `project_name`: non-empty production project identifier.
- `schema_version`: `1.0`.
- `lifecycle_stage`: `assembly_started`, `inputs_validated`, `artifacts_normalized`, `production_assembly_ready`, or `failed`.
- `lineage`: required production lineage plus optional downstream lineage identifiers.
- `artifacts`: the nine canonical Article Package inputs: `article_draft`, `quality`, `claim_audit`, `editorial_review`, `optimization`, `media`, `linking`, `taxonomy`, `production_intent`.
- `audit`: `method=production_assembly`, `version=v1`, and `validation_status`.

## Required upstream gates

- Article Draft lifecycle: `draft_ready`.
- Quality lifecycle: `article_draft_quality_ready`; outcome `passed`; audit validation `validated`.
- Claim Audit outcome: `passed`; audit validation `validated`.
- Editorial Review outcome: `approved`; audit validation `validated`.
- Optimization contains final `seo_title` and `meta_description`.
- Media contains at least one image. Every image has `materialization_status` of `materialized`, a non-empty `asset_ref`, `alt_text`, `prompt`, placement, and section reference.
- Linking contains `internal` and `external` arrays. Assembly does not discover or rewrite links.
- Taxonomy contains at least one category; tags are unique when present.
- Production intent is immutable and exactly:

```json
{
  "target": "wordpress",
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

- Lineage must contain `report_id`, `decision_id`, `strategy_id`, `brief_id`, `draft_id`, and `quality_id`.

## Enums

### Lifecycle

`assembly_started` | `inputs_validated` | `artifacts_normalized` | `production_assembly_ready` | `failed`

### Media materialization

`specified` | `materialized`

Only `materialized` media may be accepted as delivery-capable assembly input.

## Invariants

1. No required artifact may be missing.
2. No upstream artifact may be silently substituted, generated, or fabricated.
3. No `asset_ref` may be fabricated to satisfy readiness.
4. Assembly must not perform network access, LLM calls, search, DataForSEO calls, WordPress writes, image generation, link discovery, taxonomy creation, platform-ID resolution, rewriting, or publishing.
5. Production intent is fail-closed and draft-only.
6. Assembly preserves lineage and does not mutate caller-owned input objects.
7. The assembly identifier is deterministic for the same project and canonical input set.
8. Assembly readiness does not itself imply Article Package readiness; the Article Package Engine remains the canonical package validation gate.
9. Assembly must fail closed on invalid lifecycle, failed quality/claim/editorial gates, unmaterialized media, invalid taxonomy, or unsafe production intent.

## Downstream boundary

```text
Production Artifacts
        ↓
Production Assembly v1
        ↓
Article Package Engine
        ↓
Production Delivery Boundary
        ↓
WordPress Delivery Adapter
        ↓
WordPress Draft
```

Production Assembly v1 does not produce a WordPress request and does not call the WordPress adapter.