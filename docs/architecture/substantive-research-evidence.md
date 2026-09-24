# Substantive Research Evidence

Version: 1.0

## Purpose

The substantive research layer converts reviewed source material into canonical Evidence records for article claim families.

It exists because SERP, intent, entity, authority, and business analyzers identify the research landscape but do not, by themselves, provide substantive support for coverage, pricing, eligibility, comparison, FAQ answers, or methodology claims.

## Input Boundary

The layer consumes an explicit `source-material.json` artifact.

Each source must declare:

- source identifier and URL;
- provider;
- source class (`official`, `institutional`, or `secondary`);
- retrieval date;
- title;
- structured factual items.

The layer does not infer substantive facts from:

- SERP titles;
- SERP snippets;
- rankings;
- search volume;
- CPC;
- business value;
- entity presence;
- question frequency;
- authority scores.

Those remain discovery or signal Evidence.

## Canonical Output

The output is `substantive-evidence.json`.

Every emitted record uses the canonical Evidence contract and preserves:

- report lineage;
- source identity;
- provenance;
- deterministic Evidence IDs;
- confidence;
- capture time;
- active status.

No alternate Evidence schema is introduced.

## Claim Boundary

A source-material fact may be emitted only when its `claim_type + attribute` exists in the Expected Claim Map as a substantive claim.

Signal-only claim families are rejected.

This prevents a source packet from becoming an unrestricted fact store that bypasses the article claim contract.

## Authority Boundary

Substantive facts must originate from Class A, B, or C source material:

```
official
institutional
secondary
```

Community and search-surface material cannot be upgraded into substantive Evidence by this layer.

## Method

The conversion is deterministic:

```
source material
    ↓
schema validation
    ↓
claim-family validation
    ↓
canonical Evidence construction
    ↓
methodology/source/lineage records
    ↓
substantive-evidence.json
```

No LLM is used to create or reinterpret a fact in this layer.

## Downstream Integration

When `source-material.json` exists for a project, the Research Agent:

1. produces the existing research signals;
2. converts source material into substantive Evidence;
3. stores the substantive Evidence artifact;
4. exposes its Evidence references in the canonical Research Report;
5. lets Recommendation → Decision → Content Strategy → Content Brief inherit those references.

The Section Evidence Quality Gate then decides section-by-section whether the evidence is sufficient.

## Fail-Closed Behavior

Invalid source material, unsupported claim families, and non-substantive signal claims are rejected rather than converted.

Missing source material does not manufacture Evidence. Existing projects therefore retain their previous research behavior until substantive source material is supplied.

## E2E Requirement

A real research project should reach the Article Writer only when the expected substantive claim families are present and section readiness is `READY`.

For `expat-health-insurance`, the source-material E2E test uses current source pages from Allianz Care, Cigna Global, and International Insurance to cover the required definition, scope, eligibility, coverage, pricing, comparison, FAQ, and methodology claim families.
