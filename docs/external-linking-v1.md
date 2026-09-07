# External Linking v1

## Roadmap position

Roadmap item #21 — External Linking (P2). The Final Implementation Roadmap specifies URL data with DataForSEO / Search as the discovery dependency.

## Audit conclusion

No existing External Linking contract was found in the Core. Existing article and media layers do not own external-link selection. External Linking is therefore introduced as a separate downstream editorial-link contract after the Outline Editor.

## Architecture

```text
Outline Editor
    ↓
DataForSEO / Search discovery and verification (upstream integration)
    ↓
External Linking Contract
    ↓
Editorial / publication formatter
```

## Contract

```text
external_linking
├── enabled
├── required
├── max_links
├── placement
├── source_requirement
└── links[]
    ├── url
    ├── title
    ├── domain
    ├── relevance_score
    ├── source
    └── link_type
```

## Final enums

- `source_requirement`: `dataforseo` | `search`
- `source`: `dataforseo` | `search`
- `placement`: `intro` | `body` | `conclusion`
- `link_type`: `official` | `research` | `reference` | `guidance`

## Final invariants

1. Upstream Outline Editor must be `outline_editor_ready`.
2. Required lineage identifiers must be present and preserved.
3. `required=true` requires `enabled=true`.
4. `enabled=false` requires `max_links=0` and produces no selected links.
5. `enabled=true` requires `max_links >= 1`.
6. Required External Linking needs at least one verified candidate.
7. Candidate URLs must be unique.
8. Candidate source must match `source_requirement`.
9. Candidate URLs must use HTTPS.
10. Relevance scores must be numeric values from 0 to 1.
11. Selection is deterministic: relevance descending, then URL ascending.
12. Unknown candidate/settings fields are rejected.
13. The engine does not invent URLs, titles, domains, or other link metadata.

## Architectural boundary

The contract consumes already discovered/verified candidates. It does not call DataForSEO/Search, fetch destination pages, generate anchor text, insert links into article prose, publish to WordPress, or perform internal-link discovery.

## Out of scope

- DataForSEO / Search API transport implementation
- live credentials or secrets
- destination-page fetching
- anchor-text generation
- HTML/Markdown link rendering
- WordPress publication
- Internal Linking (#22)
- LLM-based link selection
- SEO keyword stuffing
