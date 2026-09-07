# Internal Linking v1

## Roadmap

Roadmap item #22: **Internal Linking — P2**. The upstream dependency is **WordPress API / local index**.

## Architecture

```text
Outline Editor / article structure
        ↓
WordPress API or verified local index
        ↓
Internal Linking Contract
        ↓
Editorial / publication formatter
```

The Core contract is intentionally provider-agnostic. Discovery and verification happen upstream. The engine does not call WordPress, fetch destination pages, generate anchor text, edit article prose, or publish content.

## Contract

`internal_linking` contains:

- `enabled`
- `required`
- `max_links`
- `placement`: `intro | body | conclusion`
- `source_requirement`: `wordpress_api | local_index`
- `site_domain`
- `current_url`
- `links[]`

Each selected link contains:

- `post_id`
- `url`
- `title`
- `slug`
- `relevance_score`
- `source`
- `link_type`: `article | guide | comparison | buyer_guide | category`

## Invariants

1. Upstream lifecycle must be `outline_editor_ready`.
2. Required lineage identifiers are preserved from the Outline Editor.
3. `required=true` requires `enabled=true`.
4. Disabled linking requires `max_links=0` and emits no links.
5. Enabled linking requires `max_links>=1`.
6. Required linking needs at least one verified candidate.
7. Candidate `post_id` and `url` values are unique.
8. Candidate source must match `source_requirement`.
9. Candidate URLs must be HTTPS and belong to `site_domain`.
10. `current_url`, when supplied, must belong to `site_domain`; it cannot be selected as a target.
11. `relevance_score` is constrained to `0..1`.
12. Unknown candidate/settings fields are rejected.
13. Selection is deterministic: relevance descending, then URL ascending.
14. The engine does not invent target metadata or anchor text.

## Deterministic identity

The contract ID is a SHA-256-derived `int_` identifier over normalized lineage and payload, including schema and method versions.

## Scope boundary

This version defines **selection and validation**, not link placement inside prose. A later publication/formatting layer may consume this contract to insert approved internal links.
