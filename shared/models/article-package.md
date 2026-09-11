# Article Package Contract v1

## 1. Purpose

The Article Package is the canonical production payload produced by IRL AI Core after content has passed the required production gates and before platform-specific delivery.

It is the boundary between **content production** and **publication delivery**.

The package must be sufficient for a delivery adapter to construct a WordPress Draft without reaching backward into research artifacts or reconstructing production decisions.

## 2. Position in the production architecture

```text
Research
  -> Intelligence / Configuration / Structure
  -> Article Writer
  -> Editorial / Grounding / QA
  -> Article Package
  -> Publication / Publisher
  -> Platform Delivery Adapter
  -> WordPress Draft
  -> Human Review
  -> Publish
```

The Article Package is not a WordPress request. It is a platform-neutral production artifact.

## 3. Ownership

- **Producer:** IRL AI Core production pipeline.
- **Consumer:** Publisher and platform delivery adapters.
- **Source of truth:** The package itself for the content and production assets required for delivery.
- **Research artifacts:** Supporting provenance only; delivery must not depend on re-reading raw research to reconstruct the package.
- **WordPress Connector:** Serialization and transport only. It must not invent missing content, media, links, SEO metadata, taxonomy, or publication decisions.

## 4. Contract scope

Article Package v1 covers the complete reader-facing and delivery-ready article representation:

1. **Core article content** — title, slug/excerpt where applicable, content type, primary keyword, ordered sections and claims.
2. **Structured content** — tables that are part of the article experience.
3. **Media assets** — image specifications and, once materialized, the media identity required for delivery; featured-image intent is part of the package boundary.
4. **Accessibility metadata** — alt text associated with media assets.
5. **Linking assets** — approved internal and external links with placement information.
6. **Optimization metadata** — SEO fields required by the publication destination.
7. **Taxonomy metadata** — category and tag intent required by the destination.
8. **Lineage and provenance** — identities linking the package to the production artifacts that produced it.
9. **Production intent** — delivery target and publication safety state.

## 5. Conceptual package structure

The package is organized into these logical domains:

```text
article_package
├── identity
├── lineage
├── content
│   ├── article
│   ├── sections
│   ├── tables
│   └── claims
├── media
│   ├── images
│   └── featured_image
├── linking
│   ├── internal
│   └── external
├── optimization
│   ├── seo
│   └── metadata
├── taxonomy
│   ├── categories
│   └── tags
├── delivery
└── audit
```

This is a conceptual contract. Exact field names, enums, cardinalities, and validation invariants are intentionally deferred to the next contract-hardening step.

## 6. Package lifecycle

The lifecycle is strictly ordered:

```text
production_ready
    -> package_assembled
    -> package_validated
    -> delivery_ready
    -> delivered_as_draft
    -> human_review
```

A package is not delivery-ready merely because Article Draft Quality passed. The package must contain every required production asset for the selected article type and delivery target.

## 7. Boundary rules

### Article Draft -> Article Package

Article Draft is the authored content source. The package promotes the authored content into a complete delivery artifact and adds the production assets required downstream.

The package must not silently discard tables, images, links, optimization metadata, taxonomy, or accessibility information.

### Article Package -> Publisher

Publisher receives a complete package and prepares a publication operation. Publisher must not regenerate article content or recover missing assets from research files.

### Publisher -> Delivery Adapter

The delivery adapter receives an explicit publication-ready representation and maps it to the target platform. Platform-specific serialization belongs here, not in the Article Package.

### Delivery Adapter -> WordPress Connector

The WordPress Connector creates or updates a WordPress Draft only. It may serialize HTML, media references, metadata, taxonomy, and links for WordPress, but it may not change publication intent.

## 8. Media boundary

Article Package v1 deliberately separates **media specification** from **media materialization**.

A writer may define an image requirement, prompt, placement, and alt text. A package becomes delivery-ready only when the selected delivery path has a valid materialized media identity or an explicitly supported deferred-media state.

No fake URL, media ID, attachment ID, or featured-media ID is permitted.

Media generation/upload is a production stage; it is not performed by the Article Writer and must not be hidden inside the WordPress Connector.

## 9. Linking boundary

Links are first-class production assets, not strings discovered opportunistically by the WordPress serializer.

The package owns approved link targets and placement. The delivery adapter owns platform-specific serialization.

## 10. Optimization boundary

SEO strategy and validation remain upstream decision/validation artifacts. Article Package owns the final optimization values selected for delivery.

A delivery adapter must not infer SEO metadata from prose when an explicit package value is required.

## 11. Taxonomy boundary

Categories and tags are production metadata. The package carries the selected taxonomy intent; the WordPress Connector maps that intent to WordPress taxonomy identifiers or performs the explicitly defined lookup required by the next contract.

No connector may silently assign arbitrary categories or tags.

## 12. Publication safety

Article Package v1 is **draft-first and human-review gated**.

The package must carry publication intent that resolves to:

```text
mode = wordpress_draft
publish = false
human_approval_required = true
```

No package may authorize automatic publication in v1.

## 13. Fail-closed principle

If a required package component is absent, malformed, inconsistent with lineage, or not ready for the selected delivery target, package validation must fail closed.

The system must not:

- fabricate missing assets;
- substitute research metadata for reader-facing content;
- silently drop production assets;
- infer publication authorization;
- publish a package that has not passed its required gates.

## 14. Stage truthfulness

The production orchestrator may mark a stage complete only when the corresponding artifact or validated state exists.

In particular, `editorial_cleanup`, `media`, `linking`, and `optimization` must not be inferred merely from the existence of `editorial_review` or `seo_validation`.

The Article Package boundary therefore becomes the checkpoint at which completion of delivery-relevant production assets is explicit and auditable.

## 15. What is intentionally out of scope

Article Package v1 does not define:

- the LLM provider;
- image-generation provider;
- WordPress authentication;
- HTTP transport implementation;
- WordPress REST request syntax;
- automatic publishing;
- UI/editor workflows;
- the exact JSON Schema;
- the final field-by-field enum/cardinality/invariant specification.

Those concerns remain in their appropriate layers or are defined in subsequent contract-hardening work.

## 16. Acceptance definition

Article Package v1 is considered implemented only when a production run can demonstrate:

```text
validated Article Draft
  -> complete Article Package
  -> validated delivery representation
  -> WordPress Draft containing the package's required content/assets/metadata
  -> human review
```

The implementation must preserve lineage, be deterministic where applicable, fail closed on missing required assets, and never bypass the human-approval boundary.
