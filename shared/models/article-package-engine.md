# Article Package Engine v1 — Boundary, I/O & Invariants

## 1. Purpose

The Article Package Engine v1 is the deterministic assembly boundary between approved production artifacts and the canonical Article Package v1.

Its single responsibility is:

> Assemble, normalize, bind lineage, and validate a complete Article Package from explicitly supplied upstream artifacts, then fail closed when the package is incomplete, inconsistent, unsafe, or not delivery-ready.

The Engine is not a research, generation, discovery, platform, or publication component.

Normative dependencies:

- `shared/models/article-package.md`
- `shared/schemas/article-package.schema.json`
- `shared/schemas/production-delivery-boundary.schema.json`

## 2. Boundary

```text
Approved Production Artifacts
        |
        v
+-----------------------------+
| Article Package Engine v1   |
|                             |
| assemble                     |
| normalize                    |
| bind lineage                 |
| check completeness           |
| check references             |
| validate lifecycle          |
| fail closed                 |
+-----------------------------+
        |
        v
Validated Article Package v1
        |
        v
Production Delivery Boundary
        |
        v
Platform Adapter / Connector
```

The Engine must not cross the boundary into content generation, research, asset discovery, platform transport, or publication.

## 3. Input contract

The Engine accepts an explicit input object containing only declared upstream artifacts and production context.

Required logical inputs:

| Input | Role | Engine may transform? | Engine may create if absent? |
|---|---|---:|---:|
| Article Draft | authoritative article content | yes, canonical mapping only | no |
| Quality result | quality gate evidence | yes, binding only | no |
| Claim grounding | claim support state | yes, canonical mapping only | no |
| Editorial result | editorial gate state | yes, binding only | no |
| Optimization artifact | final SEO delivery values | yes, canonical mapping only | no |
| Internal links artifact | approved internal links | yes, canonical mapping only | no |
| External links artifact | approved external links | yes, canonical mapping only | no |
| Media artifact | image specifications/materialization state | yes, canonical mapping only | no |
| Taxonomy artifact | selected categories/tags | yes, canonical mapping only | no |
| Production lineage | upstream identities | yes, binding only | no |
| Production intent | publication safety | yes, enforce only | no |

The implementation must use explicit typed/structured inputs. It must not receive an unrestricted project directory and decide which files to inspect.

## 4. Output contract

The Engine returns exactly one of two outcomes:

### Success

A complete `Article Package v1` object conforming to the Article Package schema and Engine invariants.

### Failure

A structured, deterministic Engine error identifying the failed invariant/domain. A failure must not return a package marked `package_validated` or `delivery_ready`.

No best-effort or partially repaired package is a valid Engine success.

## 5. Allowed responsibilities

The Engine has exactly these responsibilities:

1. **Assembly** — construct all Article Package root domains.
2. **Normalization** — map supplied artifacts into the canonical package representation without changing meaning.
3. **Lineage binding** — attach the actual upstream artifact identities.
4. **Structural completeness** — ensure required fields and domains exist.
5. **Reference integrity** — verify cross-object references resolve.
6. **Lifecycle validation** — enforce package lifecycle requirements and monotonic state.
7. **Fail-closed enforcement** — block invalid or incomplete packages.

The Engine may perform deterministic formatting/normalization required by the contract, but may not make editorial or platform decisions.

## 6. Explicit non-responsibilities

The Engine MUST NOT:

- call an LLM or generate prose;
- perform research, web search, retrieval, or competitor discovery;
- generate or rewrite SEO values;
- discover, invent, or replace links;
- generate images;
- materialize images unless a separately contracted production artifact already represents the materialized asset;
- upload media;
- authenticate to WordPress;
- call WordPress REST APIs;
- resolve arbitrary WordPress taxonomy/media IDs as a substitute for package data;
- render platform-specific post payloads;
- publish or authorize publication;
- reread research artifacts to repair missing package fields;
- silently drop unsupported or missing delivery assets;
- fabricate defaults for required values;
- downgrade a failure into a warning.

## 7. Media boundary

The Engine consumes media state; it does not create media state.

```text
image specification
      |
      v
media production/materialization stage
      |
      v
materialized media artifact
      |
      v
Article Package Engine
```

For `delivery_ready`, every required image must be `materialized` and must contain a real IRL media `asset_ref` plus non-empty `alt_text`.

`asset_ref` is not a WordPress attachment ID.

If materialization is missing, the Engine fails. It must not invent a URL, attachment ID, path, or asset reference.

## 8. Linking boundary

Links are approved inputs, not Engine discoveries.

The Engine may validate:

- link identity uniqueness;
- section references;
- target URL presence;
- anchor text;
- placement;
- internal/external classification;
- approved destination rules defined by the package contract.

The Engine must not search for replacement targets when a link is absent or invalid.

## 9. Optimization boundary

`seo_title`, `meta_description`, and optional `canonical_url` are authoritative final delivery values supplied by the optimization stage.

The Engine may validate and bind them.

It must not generate, score, rewrite, infer, or replace them from article prose.

## 10. Taxonomy boundary

Categories and tags are explicit production decisions.

The Engine may validate and bind taxonomy intent.

It must not infer categories/tags from the article, research, keyword, or section headings.

Platform-specific ID resolution belongs to the delivery layer.

## 11. Content boundary

The Engine preserves Article Draft meaning and structure.

It may map:

```text
Draft -> canonical package article/sections/claims/tables
```

It must preserve:

- section order;
- section content;
- claim identity and grounding;
- evidence references;
- tables and table structure;
- required structured assets.

It must never replace a table with prose, drop a table, invent a claim, or rewrite body content as an assembly shortcut.

## 12. Cross-artifact invariants

The following are Engine-level invariants in addition to JSON Schema validation:

### Identity

- `package_id` follows the canonical deterministic format.
- IDs are stable for the same canonical production input and package version.
- package-local IDs are unique in their defined scope.

### Lineage

- all required lineage IDs are present;
- supplied optional lineage IDs correspond to actual supplied artifacts;
- lineage IDs are never fabricated to satisfy validation.

### Sections

- section order starts at `0` and increments by `1`;
- every section ID is unique;
- every section reference resolves.

### Claims

- every claim references an existing section;
- every claim reference from a section resolves;
- `grounded` claims retain evidence references;
- `delivery_ready` requires all required claims to be grounded.

### Tables

- every table references an existing section;
- table IDs are unique;
- every row has exactly the number of cells declared by `columns`;
- `comparison` and `buyer_guide` packages contain at least one table.

### Media

- every image references an existing section;
- image IDs are unique;
- materialized images contain `asset_ref`;
- delivery-ready images are materialized and have alt text;
- featured image, when present, references an existing materialized image at delivery readiness.

### Links

- link IDs are unique across internal and external links;
- every link references an existing section;
- approved target and anchor text are preserved.

### Optimization

- required final optimization values are present before delivery readiness;
- values are not regenerated downstream.

### Taxonomy

- at least one category is present;
- taxonomy values are explicit and preserved;
- missing required taxonomy blocks delivery readiness.

### Publication safety

The Engine must emit only:

```text
 target = wordpress
 mode = wordpress_draft
 publish = false
 human_approval_required = true
```

Any other publication intent is invalid for v1.

## 13. Lifecycle enforcement

The Engine recognizes the Article Package lifecycle:

```text
production_ready
    -> package_assembled
    -> package_validated
    -> delivery_ready
    -> delivered_as_draft
    -> human_review
```

The Engine itself is responsible only for package states through `delivery_ready`.

It must not claim `delivered_as_draft` merely because a package was built. Delivery confirmation belongs to the Production Delivery Boundary.

A package can become `delivery_ready` only when:

- schema validation passes;
- lineage is internally consistent;
- all required cross-references resolve;
- required claims are grounded;
- required media are materialized;
- required tables exist;
- optimization values are present;
- taxonomy is present;
- publication safety is exact.

## 14. Stage truthfulness

The Engine must not use one artifact as evidence that another production stage completed.

Invalid shortcuts include:

```text
editorial_review exists -> media complete
editorial_review exists -> linking complete
seo_validation exists -> optimization artifact exists
Article Draft exists -> Article Package complete
```

A stage is complete only when its corresponding artifact/state exists and satisfies its contract.

## 15. Fail-closed rules

Any of the following blocks successful package construction or delivery readiness:

- missing required artifact;
- malformed artifact;
- conflicting lineage;
- unresolved reference;
- duplicate package-local ID;
- unsupported lifecycle transition;
- missing required table;
- ungrounded required claim;
- unmaterialized required image;
- missing alt text;
- missing optimization value;
- missing taxonomy;
- unsafe publication intent;
- fabricated or placeholder delivery value;
- silent asset loss during normalization.

The Engine must not auto-repair these conditions.

## 16. Determinism

For the same canonical inputs, contract version, and package version, the Engine must produce the same package content and deterministic identity.

The Engine must not depend on:

- current time for package identity;
- random IDs;
- network availability;
- WordPress state;
- LLM output;
- unordered filesystem discovery;
- mutable external search results.

## 17. Platform neutrality

The Article Package remains platform-neutral.

The Engine may encode the package's declared delivery intent, but must not encode WordPress-specific transport details such as:

- REST request paths;
- authentication headers;
- WordPress post IDs;
- attachment IDs;
- platform-generated HTML conventions.

Those belong to the Production Delivery Boundary and WordPress connector.

## 18. Validation order

The implementation should validate in this order so failures are deterministic and easy to diagnose:

```text
1. Input contract
2. Required artifact presence
3. Lineage consistency
4. Canonical assembly
5. Local structural invariants
6. Cross-artifact reference invariants
7. Lifecycle requirements
8. Article Package JSON Schema
9. delivery_ready invariants
10. return validated package
```

No downstream side effect is allowed during validation.

## 19. Engine acceptance criteria

The Engine phase is complete only when all are true:

- a single explicit Engine input contract exists;
- a single explicit Engine output contract exists;
- responsibilities and exclusions are encoded in tests;
- valid packages are assembled without silent loss;
- invalid packages fail closed;
- cross-artifact references are tested;
- lifecycle requirements are tested;
- deterministic identity/output behavior is tested;
- tables, media, links, optimization, taxonomy, and publication safety are tested;
- the Engine has no network/platform/LLM side effects;
- full repository regression passes;
- delivery remains a separate subsequent boundary.

## 20. Implementation rule

Do not expand Engine v1 while implementing it.

If a required value cannot be produced from an explicit upstream artifact, stop and classify the missing producer/boundary rather than adding discovery or generation logic to the Engine.
