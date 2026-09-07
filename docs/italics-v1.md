# Italics v1

## Roadmap position

Roadmap item #19.1 — Italics (P2). The Final Implementation Roadmap classifies Italics as an optional editorial-formatting capability.

## Purpose

The Italics contract defines whether and how a downstream editorial formatter may apply italic emphasis. It is a formatting policy, not a prose generator.

## Contract

```text
italics
├── enabled
├── required
├── max_per_section
└── policy
```

The v1 policy is fixed to `editorial_emphasis_only`.

## Defaults and invariants

1. Italics are optional and disabled by default.
2. `enabled` and `required` are booleans.
3. `required=true` requires `enabled=true`.
4. `enabled=false` requires `max_per_section=0`.
5. `enabled=true` requires `max_per_section >= 1`.
6. `max_per_section` is a non-negative integer.
7. `policy` must be `editorial_emphasis_only`.
8. Unknown contract fields are rejected.
9. The contract preserves Outline Editor lineage.
10. The engine is deterministic and makes no network, provider, or LLM calls.

## Architectural boundary

```text
Outline Editor ──> Italics Contract ──> Editorial Formatter
```

The engine does not insert Markdown/HTML markup, rewrite prose, choose phrases, perform SEO keyword stuffing, or generate text. Applying italics to actual text remains a downstream editorial-formatting responsibility.

## Relationship to Bold

Bold remains governed by Details to Include (#18.3). Italics is a separate #19.1 contract so the roadmap capability is independently configurable without duplicating or changing the Bold contract.

## Out of scope

- LLM/provider selection
- prose generation
- text rewriting
- SEO analysis
- automatic quote/key-takeaway generation
- actual markup rendering
- #20 YouTube Videos
