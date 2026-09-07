# Content Optimization / Gap Analysis v1

## Roadmap

Roadmap item #23: **Content Optimization / Gap Analysis — P2**. The Final Implementation Roadmap identifies **DataForSEO** as the external dependency.

## Purpose

This layer reviews an existing article against normalized upstream content targets and identifies missing or weak coverage. It produces deterministic gaps and actionable recommendations. It is an analysis contract, not a rewriting or publishing engine.

## Architecture

```text
Semantic SEO / Outline Editor / Details to Include
                         ↓
                DataForSEO evidence
                         ↓
              Content Optimization
                         ↓
           Gap + Recommendation Contract
                         ↓
              Editorial / Drafting Layer
```

DataForSEO discovery is supplied as verified, normalized input. The Core engine does not make network calls in v1.

## Contract

`content_optimization` contains lineage, article evidence, analysis mode, threshold, `gaps[]`, `recommendations[]`, and a deterministic `summary`.

Gap categories: `keyword`, `semantic`, `topic`, `heading`, `coverage`, `entity`, `question`.

Gap sources: `semantic_seo`, `outline_editor`, `details_to_include`, `dataforseo`.

Recommendation types: `add_section`, `expand_section`, `add_keyword`, `add_entity`, `add_question`, `improve_coverage`, `adjust_heading`.

Analysis modes: `coverage`, `competitive`, `combined`.

## Invariants

1. Outline Editor must be `outline_editor_ready`.
2. Supplied Semantic SEO and Details to Include contracts must be ready and line up with Outline Editor lineage.
3. Threshold is constrained to `0..1`.
4. Competitive and combined modes require verified DataForSEO evidence.
5. Coverage mode excludes DataForSEO-only targets.
6. Competitive mode evaluates only DataForSEO targets.
7. Target coverage is deterministic from normalized article text and target tokens.
8. Gaps are emitted only when coverage is below the configured threshold.
9. Gap and recommendation ordering is deterministic.
10. IDs are SHA-256-derived from normalized payloads.
11. The engine does not invent content targets, competitor facts, prose, URLs, or metadata.
12. The engine does not call DataForSEO, an LLM, a search engine, WordPress, or a publisher.

## Scope boundary

v1 performs content coverage and gap detection. It does not rewrite the article, automatically insert missing sections, run live DataForSEO requests, or publish changes. Those responsibilities belong to downstream integrations/editorial layers.
