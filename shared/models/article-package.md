# Article Package Contract v1 — Final Fields, Enums, Cardinalities & Invariants

## 1. Contract status

This document is the normative field-level contract for **Article Package v1**.

It finalizes:

- field names and types;
- required and optional fields;
- enums;
- cardinalities;
- cross-field invariants;
- lifecycle requirements;
- the Production Delivery Boundary.

JSON Schema, tests, and engine implementation are **not** defined in this step.

## 2. Root object

`article_package` is an object with `additionalProperties = false`.

| Field | Type | Required | Cardinality / Enum | Meaning |
|---|---|---:|---|---|
| `identity` | object | yes | exactly 1 | Package identity and article identity |
| `lineage` | object | yes | exactly 1 | Upstream production lineage |
| `content` | object | yes | exactly 1 | Reader-facing article content |
| `media` | object | yes | exactly 1 | Article media assets |
| `linking` | object | yes | exactly 1 | Approved internal/external links |
| `optimization` | object | yes | exactly 1 | Final delivery optimization values |
| `taxonomy` | object | yes | exactly 1 | Selected category/tag intent |
| `delivery` | object | yes | exactly 1 | Delivery target and publication safety |
| `audit` | object | yes | exactly 1 | Package validation state |

No undeclared root fields are permitted.

## 3. Identity

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `package_id` | string | yes | exactly 1; `package_[a-f0-9]{16}` |
| `project_name` | string | yes | non-empty |
| `schema_version` | string | yes | exactly `1.0` |
| `lifecycle_stage` | string | yes | one of `production_ready`, `package_assembled`, `package_validated`, `delivery_ready`, `delivered_as_draft`, `human_review` |
| `content_type` | string | yes | one of `guide`, `comparison`, `buyer_guide`, `article` |
| `primary_keyword` | string | yes | non-empty |

`package_id` is deterministic for the same canonical production input and package version. It is not a random per-attempt identifier.

## 4. Lineage

`lineage` contains the minimum identities needed to trace the package back to the production pipeline.

### Required

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `report_id` | string | yes | exactly 1, non-empty |
| `decision_id` | string | yes | exactly 1, non-empty |
| `strategy_id` | string | yes | exactly 1, non-empty |
| `brief_id` | string | yes | exactly 1, non-empty |
| `draft_id` | string | yes | exactly 1, non-empty |
| `quality_id` | string | yes | exactly 1, non-empty |

### Optional stage lineage

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `config_id` | string | no | 0..1 |
| `semantic_id` | string | no | 0..1 |
| `optimization_id` | string | no | 0..1 |
| `image_spec_id` | string | no | 0..1 |
| `alt_text_id` | string | no | 0..1 |
| `external_links_id` | string | no | 0..1 |
| `internal_links_id` | string | no | 0..1 |
| `news_id` | string | no | 0..1 |

If an optional lineage ID is present, the corresponding asset/state must also be present and internally consistent. An ID must never be used as a substitute for the actual delivery asset.

## 5. Content

`content` is an object containing `article`, `sections`, `claims`, and `tables`.

### 5.1 Article

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `title` | string | yes | exactly 1, non-empty |
| `slug` | string | yes | exactly 1, non-empty |
| `excerpt` | string | no | 0..1 |

`content_type` and `primary_keyword` remain canonical under `identity`; they are not duplicated under `article`.

### 5.2 Sections

`sections` is an ordered array with **1..N** items.

Each section contains:

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `section_id` | string | yes | exactly 1, non-empty; unique within package |
| `order` | integer | yes | exactly 1; starts at 0 and increments by 1 |
| `heading` | string | yes | exactly 1, non-empty |
| `body` | string | yes | exactly 1, non-empty |
| `purpose` | string | yes | exactly 1, non-empty |
| `claim_ids` | array[string] | yes | 0..N; unique |
| `evidence_refs` | array[string] | yes | 1..N; unique |

Section order is authoritative. Delivery adapters must preserve it.

### 5.3 Claims

`claims` is an array with **0..N** items.

Each claim contains:

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `claim_id` | string | yes | exactly 1; unique within package |
| `section_id` | string | yes | exactly 1; must reference an existing section |
| `text` | string | yes | exactly 1, non-empty |
| `evidence_refs` | array[string] | yes | 0..N; unique |
| `grounding_status` | string | yes | `grounded` only for delivery-ready package |

A claim may not be marked `grounded` without evidence references.

### 5.4 Tables

`tables` is an array with **0..N** items.

Each table contains:

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `table_id` | string | yes | exactly 1; unique within package |
| `title` | string | yes | exactly 1, non-empty |
| `section_id` | string | yes | exactly 1; must reference an existing section |
| `columns` | array[string] | yes | 1..N; non-empty values |
| `rows` | array[array[string]] | yes | 1..N |
| `evidence_refs` | array[string] | yes | 0..N; unique |

### Table invariants

- Every row has exactly the same number of cells as `columns`.
- Every `section_id` exists in `sections`.
- Tables are ordered by their array position; delivery must preserve order.
- A `comparison` or `buyer_guide` package requires **at least one table**.
- Table content is authoritative package content; the delivery adapter must not replace it with prose or drop it.

## 6. Media

`media` is an object containing `images` and `featured_image`.

### 6.1 Images

`images` is an array with **1..N** items for every delivery-ready package.

Each image contains:

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `image_id` | string | yes | exactly 1; unique within package |
| `section_id` | string | yes | exactly 1; existing section |
| `placement` | string | yes | exactly 1, non-empty |
| `prompt` | string | yes | exactly 1, non-empty |
| `alt_text` | string | yes | exactly 1, non-empty |
| `materialization_status` | string | yes | `specified`, `materialized` |
| `asset_ref` | string | conditional | required when `materialization_status = materialized` |

`asset_ref` is an IRL AI Core media artifact reference. It is not a WordPress attachment ID.

### 6.2 Featured image

`featured_image` is **0..1** and, when present, contains:

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `image_id` | string | yes | exactly 1; must reference `media.images` |

For a delivery-ready package, a present `featured_image.image_id` must reference an image whose `materialization_status = materialized`.

### Media invariants

- No fake URL, WordPress media ID, attachment ID, or fabricated `asset_ref` is permitted.
- `specified` is valid for an assembled package but **not** for `delivery_ready`.
- Every delivery-ready image must be materialized.
- Every image must have non-empty alt text before delivery readiness.
- Media generation/materialization is a production stage; the Article Writer and WordPress Connector must not silently perform it.

## 7. Linking

`linking` contains `internal` and `external` arrays.

### 7.1 Internal links

`internal` is **0..N**. Each item:

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `link_id` | string | yes | exactly 1; unique |
| `section_id` | string | yes | exactly 1; existing section |
| `target_url` | string | yes | exactly 1, non-empty |
| `anchor_text` | string | yes | exactly 1, non-empty |
| `placement` | string | yes | exactly 1, non-empty |

### 7.2 External links

`external` is **0..N** with the same fields as internal links.

### Linking invariants

- Link targets are explicit package values; adapters must not discover or invent links.
- Internal links must target an approved Insurance Review Lab destination.
- External links must use an explicit target URL supplied by the package.
- Link IDs are unique across both internal and external arrays.
- Delivery must preserve the approved target and anchor text.
- Missing link assets do not permit the adapter to infer replacements.

## 8. Optimization

`optimization` contains final values for delivery.

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `seo_title` | string | yes | exactly 1, non-empty |
| `meta_description` | string | yes | exactly 1, non-empty |
| `canonical_url` | string | no | 0..1 |

The package may carry additional optimization metadata only through a future contract revision; undeclared optimization fields are not permitted in v1.

### Optimization invariants

- These are final delivery values, not suggestions.
- The delivery adapter must not regenerate or infer them from article prose.
- If a required optimization value is missing, package validation fails closed.
- `optimization_id`, when present in lineage, must correspond to the optimization values carried by the package.

## 9. Taxonomy

`taxonomy` contains selected taxonomy intent.

| Field | Type | Required | Cardinality |
|---|---|---:|---|
| `categories` | array[string] | yes | 1..N; unique, non-empty |
| `tags` | array[string] | yes | 0..N; unique, non-empty values |

### Taxonomy invariants

- Category and tag values are explicit production decisions.
- The package carries taxonomy intent, not platform-specific numeric IDs.
- The WordPress Connector may map/resolve names to WordPress IDs, but may not silently invent or arbitrarily assign taxonomy.
- A delivery failure to resolve required taxonomy must fail closed rather than silently dropping it.

## 10. Delivery boundary

`delivery` is the publication-safety contract.

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `target` | string | yes | exactly `wordpress` |
| `mode` | string | yes | exactly `wordpress_draft` |
| `publish` | boolean | yes | exactly `false` |
| `human_approval_required` | boolean | yes | exactly `true` |

No other publication mode is valid in Article Package v1.

The delivery adapter may serialize and transport the package, but it may not change these values.

## 11. Audit

`audit` contains package validation state.

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `method` | string | yes | exactly `article_package_contract` |
| `version` | string | yes | exactly `v1` |
| `validation_status` | string | yes | `pending`, `validated` |

A package may enter `delivery_ready` only when `validation_status = validated`.

## 12. Lifecycle invariants

The lifecycle is strictly monotonic:

```text
production_ready
    -> package_assembled
    -> package_validated
    -> delivery_ready
    -> delivered_as_draft
    -> human_review
```

Allowed transitions are only forward transitions in this sequence.

### Stage requirements

**`production_ready`**
- Upstream Article Production Contract is valid.
- Article Draft and Quality are available.
- Package assembly has not yet been validated.

**`package_assembled`**
- All root domains exist.
- Article Draft content has been promoted without silent loss.
- Required package fields are populated to the extent allowed before validation.

**`package_validated`**
- Contract validation passes.
- Lineage is internally consistent.
- Section, claim, table, media, link, optimization, and taxonomy references resolve.
- No prohibited metadata leakage or fabricated delivery value exists.

**`delivery_ready`**
- `audit.validation_status = validated`.
- Required images are materialized.
- Required tables exist for `comparison` and `buyer_guide`.
- Required SEO values exist.
- Required taxonomy exists.
- Publication safety is exactly draft-first/human-review gated.

**`delivered_as_draft`**
- The target platform confirms creation/update of a draft.
- The returned platform identity and edit reference are recorded by the delivery boundary, not invented by the package.
- Publication remains prohibited.

**`human_review`**
- The system has stopped at the human approval boundary.
- No automatic publish transition exists in v1.

## 13. Cross-domain invariants

1. **No silent loss:** every delivery-relevant Article Draft asset represented in the package must remain represented after serialization.
2. **No fabrication:** missing content, media, links, metadata, taxonomy, or publication authorization must never be invented downstream.
3. **No backward reconstruction:** Publisher and delivery adapters must not reread research artifacts to fill package gaps.
4. **Lineage consistency:** package lineage must identify the upstream artifacts that produced the package; conflicting IDs invalidate the package.
5. **Identity uniqueness:** `package_id`, `section_id`, `claim_id`, `table_id`, `image_id`, and `link_id` are unique within their defined scope.
6. **Reference integrity:** every section/image/table/link/claim reference resolves to an existing package object.
7. **Evidence integrity:** delivery-ready grounded claims must retain their evidence references; package delivery does not authorize unsupported claims.
8. **Structured content preservation:** tables are first-class content and cannot be flattened, omitted, or replaced by the adapter.
9. **Media readiness:** delivery-ready media must be materialized and have alt text; no platform-specific media identity is fabricated inside the package.
10. **Optimization authority:** final SEO values in the package are authoritative for delivery.
11. **Taxonomy authority:** selected taxonomy is explicit; connector resolution is allowed, arbitrary assignment is not.
12. **Publication safety:** `wordpress_draft + publish=false + human_approval_required=true` is immutable for v1.
13. **Stage truthfulness:** the orchestrator may mark `editorial_cleanup`, `media`, `linking`, or `optimization` complete only when their corresponding artifact/state exists; existence of another stage does not imply completion.
14. **Fail closed:** any required invariant failure blocks `delivery_ready` and therefore blocks delivery.

## 14. Production Delivery Boundary contract

The boundary is divided into four responsibilities:

```text
Article Package
      |
      v
Publisher
      |
      v
Delivery Adapter
      |
      v
WordPress Connector
      |
      v
WordPress Draft
```

### Article Package

Owns the complete, validated production representation.

### Publisher

Owns publication-operation identity and consumes the package as authoritative input. It does not regenerate content or assets.

### Delivery Adapter

Owns target-platform serialization. It may convert package structures to WordPress-compatible representations but may not alter content meaning, approved links, taxonomy intent, optimization values, or publication safety.

### WordPress Connector

Owns authentication, HTTP transport, platform mapping, and draft creation/update. It may resolve WordPress-specific IDs for media and taxonomy where explicitly supported by the delivery contract. It must not invent missing package values or publish.

### WordPress Draft acceptance

A successful delivery must prove, through the platform response and delivery audit, that:

- a WordPress post exists;
- its status is `draft`;
- package article content was delivered;
- tables were preserved;
- materialized media required by the package was delivered or explicitly recorded as a delivery failure;
- alt text was preserved through the media path;
- approved links were preserved;
- SEO metadata was delivered where the target integration supports it;
- selected taxonomy was delivered where supported;
- human review remains required;
- no publish operation occurred.

## 15. Explicit non-goals for this step

This contract-hardening step does **not** define:

- JSON Schema syntax;
- Python dataclasses/models;
- validators;
- Article Package builder implementation;
- media generation/upload implementation;
- WordPress REST request field mapping;
- automatic publishing;
- UI behavior.

Those belong to subsequent workflow steps.

## 16. Definition of done for this contract step

The contract-hardening step is complete when:

1. every Article Package v1 field has a defined type and cardinality;
2. every enum is explicit;
3. required/optional behavior is explicit;
4. cross-object references and lifecycle requirements are explicit;
5. fail-closed invariants are explicit;
6. the Production Delivery Boundary responsibilities are explicit;
7. the next step can implement JSON Schema without making architectural decisions.
