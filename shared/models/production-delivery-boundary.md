# Production Delivery Boundary Contract v1 — Final Fields, Enums & Invariants

## 1. Contract status

This document is the normative **Contract Design** for Production Delivery Boundary v1.

It finalizes, before implementation:

- boundary responsibilities;
- field names and types;
- required and optional fields;
- enums and cardinalities;
- lifecycle states;
- cross-field invariants;
- ownership and mutation rules;
- failure semantics;
- delivery response requirements.

JSON Schema, tests, Engine implementation, and WordPress transport changes are **not defined by this document**. They are subsequent implementation steps.

---

## 2. Boundary purpose

Production Delivery Boundary v1 is the controlled handoff between a **validated Article Package v1** and a platform delivery adapter.

```text
Article Package v1
        |
        v
Production Delivery Boundary v1
        |
        v
WordPress Delivery Adapter
        |
        v
WordPress REST Transport
        |
        v
WordPress Draft
        |
        v
Human Review
```

The boundary exists to ensure that the platform delivery layer receives a complete, validated production artifact and that every delivery attempt is:

- deterministic;
- traceable to one Article Package;
- draft-only in v1;
- fail-closed;
- auditable;
- free from content invention or silent asset loss.

The Article Package remains the canonical production source. The Delivery Boundary does **not** replace or mutate it.

---

## 3. Audit of the existing boundary

The pre-contract audit identified the following gaps in the existing implementation/schema:

| Area | Finding | Severity | Contract decision |
|---|---|---:|---|
| Article Package as delivery source | Existing delivery consumes older Production Contract / Article Draft shapes | Critical | Package v1 is the only canonical source |
| Content | Only title + section prose reaches WordPress | High | Rendered content must preserve sections, tables and approved links |
| Media | No real media delivery lifecycle | Critical | Distinguish IRL `asset_ref` from platform media identity |
| Alt text | Present upstream but not delivered as a required media property | High | Alt text is mandatory at delivery |
| Links | Internal/external links are not first-class in the old request | High | Preserve explicit link target, anchor and placement |
| SEO | SEO title/meta are not delivered | High | Final package values are authoritative |
| Taxonomy | Categories/tags are not delivered | High | Explicit taxonomy intent must be resolved or fail closed |
| Publication | Existing draft-only behavior is correct | Critical | Preserve immutable draft-only safety |
| Response | Draft response exists but boundary semantics are incomplete | Medium | Record platform identity, remote status and edit URL |
| Lifecycle | Existing schema has too few operational states | High | Define preparation, delivery and terminal states without auto-publish |

The existing `production-delivery-boundary.schema.json` therefore becomes an implementation artifact that must be reconciled with this contract; it is **not authoritative over this Contract Design**.

---

## 4. Ownership

### Article Package

Owns:

- canonical article content;
- structured tables;
- claims and evidence lineage;
- media specifications and materialized IRL assets;
- alt text;
- approved internal/external links;
- final SEO values;
- taxonomy intent;
- publication safety intent.

The package is immutable input to delivery.

### Production Delivery Boundary

Owns:

- delivery identity;
- package binding;
- delivery lifecycle;
- execution mode;
- publication safety enforcement;
- platform request handoff;
- delivery response recording;
- deterministic failure reporting;
- delivery audit state.

### WordPress Delivery Adapter / Connector

Owns:

- conversion of package structures to WordPress-compatible request values;
- WordPress media resolution/upload where explicitly supported;
- WordPress category/tag resolution where explicitly supported;
- HTML/REST serialization;
- WordPress-specific request construction;
- HTTP authentication and transport through the existing connector client.

It may not:

- generate article prose;
- rewrite or invent SEO values;
- discover links;
- invent taxonomy;
- generate images;
- fabricate media references;
- change publication safety;
- publish automatically.

### WordPress

Owns:

- final platform persistence;
- remote post identity;
- remote draft status;
- human review and eventual manual publication.

---

## 5. Root object

`production_delivery_boundary` is an object with `additionalProperties = false`.

| Field | Type | Required | Cardinality / Enum | Meaning |
|---|---|---:|---|---|
| `delivery_id` | string | yes | exactly 1; `delivery_[a-f0-9]{16}` | Deterministic identity of the delivery boundary record |
| `package_id` | string | yes | exactly 1; `package_[a-f0-9]{16}` | Article Package being delivered |
| `publisher_id` | string | yes | exactly 1; non-empty | Publication operation identity |
| `adapter_id` | string | yes | exactly 1; non-empty | Delivery adapter identity/version |
| `target` | string | yes | exactly `wordpress` | Platform target in v1 |
| `execution_mode` | string | yes | `dry_run` or `live` | Whether network side effects are permitted |
| `publication` | object | yes | exactly 1 | Immutable publication safety policy |
| `source` | object | yes | exactly 1 | Package binding and source integrity |
| `request` | object | yes | exactly 1 | Platform delivery request produced from the package |
| `lifecycle_stage` | string | yes | v1 lifecycle enum | Current delivery state |
| `delivery_status` | string | yes | `ready`, `delivering`, `delivered`, `failed` | Operational delivery state |
| `response` | object | conditional | 0..1 | Platform response or deterministic failure |
| `audit` | object | yes | exactly 1 | Boundary validation/audit state |

No undeclared root fields are permitted.

---

## 6. Delivery identity

### 6.1 `delivery_id`

`delivery_id` is deterministic for the same:

- `package_id`;
- adapter identity/version;
- target;
- boundary contract version.

Format:

```text
 delivery_[a-f0-9]{16}
```

A retry of the same package through the same adapter is therefore traceable to the same logical delivery identity. A separate operational attempt identifier may be introduced in a future contract if required; it is not part of v1.

### 6.2 `package_id`

Must exactly match the Article Package v1 `identity.package_id`.

The Delivery Boundary must never construct a new Article Package identity.

### 6.3 `publisher_id` and `adapter_id`

These identify the concrete publication operation and adapter used for the delivery.

They are lineage/operation identities, not authorization to publish.

---

## 7. Source binding

`source` is required and contains:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `package_id` | string | yes | Exact source package ID |
| `package_lifecycle_stage` | string | yes | Must be `delivery_ready` |
| `package_validation_status` | string | yes | Must be `validated` |
| `package_schema_version` | string | yes | Must be `1.0` |

### Source invariants

1. `source.package_id == package_id`.
2. The referenced Article Package must be `delivery_ready`.
3. The referenced package audit must be `validated`.
4. The referenced package schema version must be `1.0`.
5. No delivery may proceed from `package_assembled`, `package_validated`, or any non-ready package.
6. The Delivery Boundary must not reread research artifacts to repair a package.

The source binding is evidence that the delivery operation consumed the intended package rather than an earlier Article Draft or Production Contract.

---

## 8. Execution mode

`execution_mode` enum:

```text
 dry_run
 live
```

### `dry_run`

- No external write is permitted.
- The adapter may build and validate the platform request.
- No media upload, taxonomy mutation, post creation, or update may occur.
- A successful dry run may end in `request_ready`.

### `live`

- Network side effects are permitted only for the explicitly authorized draft delivery operation.
- Post creation/update must remain draft-only.
- Media upload/resolution is permitted only for assets already materialized by the Article Package.
- Automatic publish remains prohibited.

---

## 9. Publication safety

`publication` is required and immutable in v1.

| Field | Type | Required | Value |
|---|---|---:|---|
| `mode` | string | yes | exactly `wordpress_draft` |
| `publish` | boolean | yes | exactly `false` |
| `human_approval_required` | boolean | yes | exactly `true` |

### Publication invariants

1. `mode` cannot be changed by the adapter.
2. `publish` must always be `false`.
3. `human_approval_required` must always be `true`.
4. A request containing `status=publish` is invalid.
5. No v1 lifecycle transition can publish a post.
6. `live` means **live draft delivery**, not live publication.

---

## 10. Platform request

`request` is the **adapter-produced WordPress delivery representation**.

It is not a second source of truth. It is a serialized delivery view derived only from the bound Article Package.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `title` | string | yes | Package article title |
| `content` | string | yes | Rendered WordPress article content |
| `status` | string | yes | exactly `draft` |
| `slug` | string | conditional | Package slug when supplied |
| `excerpt` | string | conditional | Package excerpt when supplied |
| `media` | array | yes | Materialized package images mapped to platform assets |
| `links` | array | yes | Explicit package links represented in delivered content/request |
| `optimization` | object | yes | Final package SEO values |
| `taxonomy` | object | yes | Package taxonomy intent plus resolved platform references where available |

### Request authority

The request may transform representation, but not meaning.

Allowed transformations include:

- Article Package sections → WordPress HTML sections;
- Article Package tables → WordPress table markup;
- package `asset_ref` → WordPress media attachment ID after successful resolution/upload;
- package category/tag names → WordPress IDs after explicit resolution;
- package links → HTML link elements while preserving target and anchor;
- package SEO values → WordPress metadata fields supported by the target installation.

Forbidden transformations include:

- rewriting prose;
- dropping a table because the adapter does not support it;
- replacing an explicit link with a discovered link;
- inventing missing taxonomy;
- generating an image from an image prompt;
- inventing a media URL or attachment ID;
- changing draft status to publish.

---

## 11. Media delivery contract

Each `request.media` item represents one Article Package image that is materialized and eligible for delivery.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `image_id` | string | yes | Package image identity |
| `asset_ref` | string | yes | IRL AI Core materialized asset reference |
| `platform_asset_id` | string/integer | conditional | WordPress attachment/media identity after resolution |
| `alt_text` | string | yes | Authoritative accessibility text from package |
| `placement` | string | yes | Approved placement in article |
| `featured` | boolean | yes | Whether this image is the package featured image |

### Media invariants

1. Every delivery-ready package image must be represented.
2. `asset_ref` must come from the Article Package.
3. `asset_ref` is not a WordPress attachment ID.
4. `platform_asset_id` may only be created/returned by the platform delivery layer after successful resolution/upload.
5. No platform media identity may be fabricated.
6. `alt_text` must be non-empty and must be preserved exactly unless a future explicit transformation contract permits otherwise.
7. A failed required media resolution/upload blocks successful delivery.
8. The adapter must not generate images from `prompt`.
9. The adapter must not silently omit unsupported media.
10. If the package identifies a featured image, the corresponding delivered media item must be marked `featured=true` and must resolve successfully.

---

## 12. Linking delivery contract

`request.links` contains the explicit links from the Article Package.

Each item:

| Field | Type | Required | Cardinality / Enum |
|---|---|---:|---|
| `link_id` | string | yes | unique within delivery |
| `target_url` | string | yes | explicit package URL |
| `anchor_text` | string | yes | explicit package anchor |
| `placement` | string | yes | explicit package placement |
| `kind` | string | yes | `internal` or `external` |

### Link invariants

1. Link IDs must match the source package links.
2. Targets must not be discovered downstream.
3. Anchor text must be preserved.
4. Internal/external classification must be preserved.
5. Missing or invalid explicit targets block delivery.
6. The adapter may serialize links into HTML but may not substitute different targets.
7. A link represented in the request must also be represented in the rendered content when the target platform supports links.

---

## 13. Optimization delivery contract

`request.optimization` contains:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `seo_title` | string | yes | Final SEO title from package |
| `meta_description` | string | yes | Final meta description from package |
| `canonical_url` | string | conditional | Final canonical URL from package |

### Optimization invariants

1. Values must equal the Article Package values.
2. The adapter must not regenerate them from article prose.
3. The adapter may map them to supported WordPress metadata fields.
4. Unsupported required metadata must produce a deterministic failure rather than silent loss.
5. No optimization value may be invented.

---

## 14. Taxonomy delivery contract

`request.taxonomy` contains explicit taxonomy intent and its platform resolution state.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `categories` | array | yes | Explicit package categories plus resolved platform IDs where available |
| `tags` | array | yes | Explicit package tags plus resolved platform IDs where available |

Each taxonomy item must retain the source value and, when resolved, the platform identity.

Conceptually:

```text
category/tag
├── name       # package authority
└── platform_id  # adapter/platform resolution
```

### Taxonomy invariants

1. Package taxonomy names are authoritative.
2. Platform IDs are derived by the delivery adapter/connector, never by the package Engine.
3. The connector may resolve an explicit taxonomy name to an existing WordPress ID.
4. It may create a taxonomy term only if a future explicit connector capability authorizes creation; v1 does not authorize arbitrary taxonomy creation.
5. Failure to resolve a required category must fail closed.
6. Tags must not be invented from keywords or prose.
7. Taxonomy may not be silently dropped.

---

## 15. Content preservation

`request.content` is the WordPress-rendered representation of the complete Article Package content.

The following source structures are mandatory preservation targets:

- article title;
- section order;
- section headings;
- section bodies;
- tables;
- approved internal links;
- approved external links;
- required media placements;
- featured image placement where applicable.

### Content invariants

1. Section order remains authoritative.
2. Every source section appears in the delivered content.
3. Every source table appears in the delivered content.
4. Table column/row data must not be flattened or replaced by prose.
5. Every approved link remains represented with its approved target and anchor text.
6. Every required image remains represented at its approved placement.
7. Rendering is representation-only; it must not change article meaning.
8. Missing platform capability is a delivery failure, not permission to silently drop content.

---

## 16. Lifecycle

The v1 lifecycle is intentionally small and monotonic:

```text
 delivery_ready
       |
       v
 request_ready
       |
       v
 delivering
       |
       +-------> failed
       |
       v
 delivered_as_draft
       |
       v
 human_review
```

### Lifecycle states

#### `delivery_ready`

Boundary has received a valid Article Package v1 with:

- lifecycle `delivery_ready`;
- validation status `validated`;
- draft-only publication intent;
- materialized required media;
- grounded required claims;
- complete required package domains.

#### `request_ready`

The adapter has successfully constructed and validated the WordPress request without performing a platform write.

This state is valid for `dry_run` and may also be an internal pre-write state for `live` delivery.

#### `delivering`

A live delivery operation is actively performing the authorized draft-only platform operation.

This is an operational state, not a terminal success state.

#### `delivered_as_draft`

The platform has confirmed that the target post exists/was updated as a draft and has returned the required platform identity.

#### `human_review`

The system has stopped at the human approval boundary. No automatic publication transition exists in v1.

#### `failed`

A deterministic boundary, adapter, media, taxonomy, metadata, transport, or platform verification failure prevented successful delivery.

### Lifecycle invariants

1. Transitions are forward-only.
2. `delivery_ready` cannot bypass request validation.
3. `request_ready` cannot be treated as delivered.
4. `delivering` cannot be treated as published.
5. `delivered_as_draft` must prove remote draft status.
6. `human_review` is terminal for v1.
7. `failed` is terminal for the current delivery record; retry orchestration is outside this contract.
8. No state permits automatic publication.

---

## 17. Delivery status

`delivery_status` enum:

```text
 ready
 delivering
 delivered
 failed
```

The lifecycle stage and status must remain semantically consistent.

Minimum consistency rules:

| Lifecycle | Allowed status |
|---|---|
| `delivery_ready` | `ready` |
| `request_ready` | `ready` |
| `delivering` | `delivering` |
| `delivered_as_draft` | `delivered` |
| `human_review` | `delivered` |
| `failed` | `failed` |

A mismatch is invalid.

---

## 18. Response contract

`response` is required when a delivery operation reaches `delivered` or `failed` status.

### Successful response

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `platform_post_id` | integer | yes | WordPress post ID |
| `remote_status` | string | yes | exactly `draft` |
| `edit_url` | string | yes | WordPress edit URL when available |
| `media_results` | array | conditional | Platform media resolution results |
| `taxonomy_results` | object | conditional | Platform taxonomy resolution results |

### Failed response

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `error_code` | string | yes | Stable machine-readable failure code |
| `error_message` | string | yes | Human-readable deterministic failure description |
| `failed_stage` | string | yes | Boundary/adapter/media/taxonomy/request/transport/verification |
| `retryable` | boolean | yes | Whether an external retry may be appropriate |

### Response invariants

1. A delivered response must contain `platform_post_id`.
2. `remote_status` must equal `draft`.
3. A response claiming delivery without remote draft verification is invalid.
4. A failed response must not contain a successful publication claim.
5. Error details must not contain secrets such as application passwords.
6. Platform IDs in the response must originate from the platform response, not local invention.

---

## 19. Audit object

`audit` contains:

| Field | Type | Required | Value |
|---|---|---:|---|
| `method` | string | yes | exactly `production_delivery_boundary` |
| `version` | string | yes | exactly `v1` |
| `validation_status` | string | yes | `pending` or `validated` |

For a delivery attempt, the boundary may additionally record a future attempt/result structure only through a contract revision. v1 does not permit undeclared audit fields.

A boundary record is `validated` only when all contract invariants applicable to its lifecycle stage pass.

---

## 20. Cross-domain invariants

The following invariants are normative.

1. **Canonical source:** Article Package v1 is the only production content source for delivery.
2. **Exact package binding:** `package_id` must match the source package exactly.
3. **No reconstruction:** delivery code must not reread research, SEO, decision, or draft artifacts to fill package gaps.
4. **No silent loss:** delivery must not silently omit tables, media, links, SEO, taxonomy, or required article content.
5. **No fabrication:** no content, URL, taxonomy, media identity, metadata, or publication authorization may be invented.
6. **Representation-only transformation:** adapter serialization may change representation but not production meaning.
7. **Media identity separation:** IRL `asset_ref` and WordPress `platform_asset_id` are different namespaces and must remain distinguishable.
8. **Platform resolution traceability:** platform IDs must be attributable to explicit package values and actual platform responses.
9. **Structured-content preservation:** tables remain first-class content through delivery.
10. **Link preservation:** approved link target, anchor text, and kind remain intact.
11. **Optimization authority:** package SEO values are authoritative.
12. **Taxonomy authority:** package taxonomy intent is authoritative; resolution is not invention.
13. **Draft-only:** all v1 platform writes must use draft status.
14. **Human gate:** successful delivery always stops at human review.
15. **No auto-publish:** no v1 operation may publish automatically.
16. **Fail closed:** any required invariant failure prevents successful delivery.
17. **Response proof:** successful delivery requires platform-confirmed draft state.
18. **Secret safety:** credentials and application passwords must never enter the boundary payload or error response.
19. **Stage truthfulness:** lifecycle state must reflect actual completed work; one stage cannot imply another.
20. **Deterministic identity:** the same package/adapter/target/contract combination yields the same logical `delivery_id`.

---

## 21. Failure semantics

Failure is explicit and fail-closed.

Required failure classes for v1:

```text
PACKAGE_INVALID
PACKAGE_NOT_DELIVERY_READY
PACKAGE_LINEAGE_MISMATCH
REQUEST_INVALID
CONTENT_LOSS_DETECTED
MEDIA_ASSET_MISSING
MEDIA_RESOLUTION_FAILED
TAXONOMY_RESOLUTION_FAILED
LINK_INVALID
OPTIMIZATION_MISSING
PLATFORM_AUTH_FAILED
PLATFORM_REQUEST_FAILED
PLATFORM_RESPONSE_INVALID
REMOTE_NOT_DRAFT
PUBLICATION_POLICY_VIOLATION
```

The exact implementation exception hierarchy is outside this contract, but every failure must map to a stable machine-readable code and must prevent a false `delivered` result.

---

## 22. Dry-run invariants

A `dry_run` must prove request construction without external mutation.

Therefore:

- no post is created or updated;
- no media is uploaded;
- no taxonomy term is created or changed;
- no publication operation occurs;
- request validation still runs;
- package preservation checks still run;
- the resulting state may be `request_ready`, never `delivered_as_draft`.

---

## 23. Live delivery invariants

A `live` delivery may perform only the minimum platform side effects required to create/update the target draft.

Required order:

```text
Validate Package
      ->
Build/Validate Request
      ->
Resolve/Upload Required Materialized Media
      ->
Resolve Required Taxonomy
      ->
Create/Update WordPress Draft
      ->
Verify Remote Draft
      ->
Record Delivery Response
      ->
Human Review
```

If a required pre-post operation fails, the delivery must fail closed rather than creating a knowingly incomplete article.

---

## 24. What is explicitly out of scope for v1

- automatic publication;
- scheduled publication;
- LLM generation or rewriting;
- research discovery;
- SEO generation;
- link discovery;
- image generation;
- image editing;
- arbitrary taxonomy creation;
- WordPress UI automation;
- human approval UI;
- retry orchestration;
- rollback orchestration;
- multi-platform delivery;
- analytics/reporting beyond delivery audit;
- new authentication architecture;
- replacing the existing HTTP transport dependency without a production need.

---

## 25. Contract acceptance criteria

Production Delivery Boundary v1 is considered contract-complete only when all are true:

1. The boundary consumes **Article Package v1**, not Article Draft or the older Article Production Contract.
2. All package domains required for delivery are represented: content, tables, media, links, optimization, taxonomy, lineage and publication intent.
3. Platform serialization is separated from package authority.
4. IRL media references are distinct from WordPress attachment identities.
5. Tables cannot be silently dropped.
6. Approved internal/external links cannot be silently dropped or replaced.
7. Final SEO values cannot be regenerated downstream.
8. Taxonomy cannot be invented downstream.
9. Delivery is immutable draft-only in v1.
10. Successful delivery proves remote draft status.
11. Failures are deterministic and fail closed.
12. No lifecycle state permits automatic publication.
13. The contract is precise enough to derive JSON Schema and contract tests without inventing additional semantics.

---

## 26. Implementation gate

Only after this Contract Design is accepted should the project proceed to:

```text
Contract
   -> Final Fields / Enums / Invariants
   -> Schema
   -> Tests
   -> Delivery Boundary Engine
   -> WordPress Adapter integration
   -> Regression
   -> PR
   -> Review
   -> Squash Merge
```

**No implementation is authorized by this document itself.**
