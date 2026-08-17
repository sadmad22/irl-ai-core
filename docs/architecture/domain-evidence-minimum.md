# Minimum Domain Evidence

## Purpose

This document defines the minimum Evidence surface for the next four ResearchReport domains: Entity, Question, Business, and Authority.

These builders are contract adapters, not analyzers. The repository does not yet contain dedicated analyzers for these domains, so the builders accept normalized observations from a future analyzer or connector and emit canonical Evidence.

## Entity Evidence

Minimum claims:

- `entity_presence.mentioned`
- `entity_classification.type`
- optional `entity_relevance.score`

Entity evidence is observation-level. Derived entity scoring is intentionally deferred.

## Question Evidence

Minimum claim:

- `question_frequency.count`

This establishes a canonical count without prematurely defining question clustering, intent, or coverage scoring.

## Business Evidence

Minimum claims:

- `business_value.affiliate_potential`
- `business_value.adsense_potential`
- `business_value.conversion_potential`
- `business_value.commercial_value`

Only one claim is emitted per builder call. No recommendation or decision is produced here.

## Authority Evidence

Minimum claims:

- `authority.authority_score`
- `authority.topic_fit`

Scores are normalized to 0..1. Authority Evidence does not itself approve or reject a keyword.

## Shared Invariants

All four domains use the same Evidence Contract and therefore retain:

- deterministic report-scoped `evidence_id`
- `report_id`
- explicit source and provenance
- normalized confidence
- timestamp
- independent Evidence status
- no direct decision semantics

## Deliberate Non-Goals

This phase does not implement:

- dedicated Entity/Question/Business/Authority analyzers
- derived cross-domain lineage
- ResearchReport aggregation
- Recommendation or Decision logic
- Agent integration

Those are subsequent layers and should consume these canonical observations rather than redefine their schemas.
