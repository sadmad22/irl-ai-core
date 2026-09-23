# Expected Claim Map

Version: 1.0

## Purpose

The Expected Claim Map defines what kinds of claims each article section is expected to support before Section Evidence Readiness can be evaluated.

It implements D in the production Evidence Quality & Section Readiness Work Plan:

> Define the claim attributes/types required by each Section instead of treating Evidence count as sufficiency.

The map converts a section's editorial purpose into an explicit claim space.

It does not:

- replace the canonical Evidence Contract;
- add new fields to the Evidence object;
- decide source authority;
- define source diversity;
- define final Evidence Depth thresholds;
- declare a section READY;
- generate article prose;
- create recommendations or decisions.

Those concerns remain owned by the B, C, E, F, G, and downstream production layers.

## Architectural Position

```text
Canonical Research Evidence
        ↓
B — Evidence Quality Contract
        ↓
C — Quality Dimensions
        ↓
D — Expected Claim Map
        ↓
E — Section Evidence Readiness
        ↓
Section Evidence Eligibility
        ↓
Article Writer
        ↓
Claim Grounding / Audit
```

D is the bridge between generic Evidence quality and section-specific sufficiency.

Without D, a section can contain many valid Evidence records while still lacking the factual claim categories needed to write the section.

## Map Semantics

For each section, the map defines:

- `section_key`;
- expected claim families;
- canonical-style `claim.type` + `claim.attribute` pairs;
- whether the claim family is `required` or `supporting`;
- whether a claim is substantive or signal-oriented;
- evidence characteristics that later readiness logic must verify.

The map is a semantic contract, not a requirement to create every claim record.

A section is not covered merely because one or more Evidence records exist.

## Claim Requirement Classes

### Required

A required claim family represents information that the section is expected to contain when the section is part of the approved outline.

If no eligible Evidence can support an essential required family, the later Section Readiness layer must not treat the section as fully covered.

### Supporting

Supporting claim families strengthen or contextualize a section but do not, by themselves, define its minimum claim space.

### Signal-only

Signal-only evidence can inform planning or framing, but cannot by itself satisfy a substantive factual claim requirement.

Examples include:

- query intent;
- search-result distribution;
- authority scores;
- entity presence;
- commercial-value signals.

Signal-only does not mean invalid Evidence. It means insufficient as standalone substantive support for the affected section.

## Baseline Section Map v1

The current Content Brief uses seven recurring sections:

1. Introduction
2. What You Need to Know
3. Coverage and Key Factors
4. Costs and Pricing Factors
5. How to Compare Options
6. Frequently Asked Questions
7. Sources and Editorial Methodology

The map below is the production baseline for these sections.

---

## 1. Introduction

### Section purpose

Orient the reader to the topic, audience need, and scope without introducing unsupported factual detail.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `topic_definition` | `definition` | required |
| `query_intent` | `primary_intent` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `entity_presence` | `mentioned` | supporting |
| `entity_classification` | `type` | supporting |
| `topic_scope` | `scope` | supporting |

### Signal-only inputs

- `query_intent.primary_intent` may support framing but does not establish product facts.
- SERP position, distribution, or commercial signals do not become reader-facing claims without substantive Evidence.

### Coverage interpretation

The Introduction should be considered claim-covered only when its core definition/scope space has appropriate Evidence. Entity or intent signals alone are insufficient for substantive introduction facts.

---

## 2. What You Need to Know

### Section purpose

Explain the foundational concepts a reader needs before considering coverage, pricing, or comparison.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `topic_definition` | `definition` | required |
| `topic_scope` | `scope` | required |
| `eligibility` | `who_needs_it` | required |
| `use_case` | `primary_use` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `risk_factor` | `risk` | supporting |
| `entity_presence` | `mentioned` | supporting |
| `question` | `frequency` | supporting |

### Signal-only inputs

- question frequency can identify recurring reader concerns but is not itself an answer;
- entity presence can show that an entity appears in the research landscape but does not establish what that entity provides;
- authority scores do not establish eligibility.

### Coverage interpretation

The section needs foundational factual claims, not merely evidence that the topic appears frequently in search results.

---

## 3. Coverage and Key Factors

### Section purpose

Explain what the relevant insurance/product/service covers and the material factors, limits, exclusions, or conditions that affect that coverage.

This is a substantive section and therefore requires substantive claim families.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `coverage_fact` | `coverage` | required |
| `coverage_fact` | `benefit` | required |
| `exclusion_fact` | `exclusion` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `network_fact` | `network` | supporting |
| `requirement_fact` | `requirement` | supporting |
| `limitation_fact` | `limitation` | supporting |
| `claim_process_fact` | `claim_process` | supporting |

### Signal-only inputs

- entity-presence signals do not establish coverage;
- search intent does not establish benefits;
- business/commercial-value Evidence does not establish coverage terms;
- authority scores do not establish exclusions.

### Coverage interpretation

A valid section cannot be considered substantively covered when it contains only entity, intent, SERP, authority, or business signals.

---

## 4. Costs and Pricing Factors

### Section purpose

Explain pricing, premium/cost drivers, and relevant cost variables without inventing numerical values that are not supported by Evidence.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `pricing_fact` | `premium` | required |
| `pricing_factor` | `cost_driver` | required |
| `pricing_factor` | `price_variable` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `pricing_fact` | `cost_range` | supporting |
| `pricing_fact` | `deductible` | supporting |
| `pricing_fact` | `limit_effect` | supporting |
| `pricing_fact` | `coverage_effect` | supporting |

### Signal-only inputs

- business value is not pricing Evidence;
- CPC is not insurance premium Evidence;
- commercial value, conversion potential, affiliate potential, or AdSense potential do not establish reader-facing cost claims;
- search volume does not establish price.

### Coverage interpretation

Cost section sufficiency requires Evidence about actual pricing facts or cost drivers. Business/SEO Evidence must not be promoted to pricing Evidence.

---

## 5. How to Compare Options

### Section purpose

Give the reader a factual framework for comparing options or providers without turning the comparison section into an unsupported recommendation.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `comparison_fact` | `criterion` | required |
| `option_attribute` | `coverage_difference` | required |
| `option_attribute` | `cost_difference` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `provider_presence` | `mentioned` | supporting |
| `network_fact` | `network_difference` | supporting |
| `exclusion_fact` | `exclusion_difference` | supporting |
| `service_fact` | `service_difference` | supporting |

### Signal-only inputs

- SERP ranking does not establish provider quality;
- authority score does not automatically establish that one option is preferable;
- commercial value does not establish a consumer comparison outcome.

### Coverage interpretation

A comparison requires claim-level comparison criteria and factual differences. A list of provider/entity Evidence alone is not sufficient.

---

## 6. Frequently Asked Questions

### Section purpose

Answer reader questions using source-backed factual Evidence.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `question_fact` | `question` | required |
| `answer_fact` | `answer` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `question_frequency` | `count` | supporting |
| `intent` | `question_intent` | supporting |
| `coverage_fact` | `faq_topic` | supporting |
| `cost_fact` | `faq_topic` | supporting |

### Critical rule

`question_frequency.count` identifies demand for a question; it does not answer the question.

Therefore:

```text
question frequency Evidence
        ≠
answer Evidence
```

A FAQ item must not be considered factually supported only because the question appears frequently in research.

### Coverage interpretation

The FAQ map requires both a question claim and an answer-support claim.

---

## 7. Sources and Editorial Methodology

### Section purpose

Explain the research/source basis and editorial method using traceable metadata and methodology Evidence.

### Required claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `source_identity` | `source` | required |
| `provenance_fact` | `method` | required |
| `lineage_fact` | `evidence_lineage` | required |

### Supporting claim families

| Claim type | Attribute | Role |
| --- | --- | --- |
| `source_identity` | `provider` | supporting |
| `provenance_fact` | `analyzer` | supporting |
| `provenance_fact` | `analyzer_version` | supporting |
| `evidence_status` | `status` | supporting |

### Signal-only inputs

Authority scores may provide supporting context but are not themselves a methodology description.

### Coverage interpretation

This section should describe what was sourced, how evidence was produced/verified, and how lineage is retained. It must not claim source authority that has not been established by the later Source Authority policy.

---

## Cross-Section Claim Rules

### 1. Claim type is not Evidence domain

The map uses claim types and attributes to define expected information.

The Evidence `domain` remains independently defined by the canonical Evidence Contract.

A domain label must not be treated as a substitute for claim coverage.

### 2. One Evidence record may support more than one section only when valid

The same Evidence record can legitimately support multiple sections when its actual claim is materially relevant to each section.

However, Section Eligibility remains authoritative for section assignment.

### 3. One claim family may require multiple Evidence records

The map does not impose a universal numeric Evidence count.

Some claims may need more than one independent supporting record under later authority, diversity, or depth rules.

### 4. Required claim families are not automatically sufficient

A required family identifies what the section needs to cover.

It does not by itself establish:

- source authority;
- depth;
- freshness;
- diversity;
- final readiness.

Those are evaluated by C, E, F, and G.

### 5. Unsupported claim families remain uncovered

The system must not convert:

- intent into a factual product statement;
- entity presence into a product capability;
- commercial value into pricing;
- search metrics into consumer facts;
- question frequency into an answer.

Doing so violates the evidence boundary.

## Interaction With Current Evidence Contracts

The Expected Claim Map builds on the existing domain evidence minimums.

Current canonical domain surfaces include:

- Entity: `entity_presence.mentioned`, `entity_classification.type`, optional `entity_relevance.score`;
- Question: `question_frequency.count`;
- Business: `business_value.*`;
- Authority: `authority.authority_score`, `authority.topic_fit`.

These existing claims remain valid in their domains.

D does not relabel them to satisfy unrelated substantive section claims.

For example:

```text
authority.authority_score
        ≠
coverage_fact.coverage

question_frequency.count
        ≠
answer_fact.answer

business_value.commercial_value
        ≠
pricing_fact.premium
```

This explicit non-equivalence is a core purpose of the map.

## Content Type Compatibility

The baseline map applies to the current Content Brief content types:

- `guide`;
- `comparison`;
- `buyer_guide`;
- `article`.

The map is section-first rather than content-type-first.

A later implementation may add content-type modifiers, but those modifiers must preserve the baseline required claim families unless an explicit strategy layer changes the section itself.

## Readiness Boundary

D produces the Expected Claim Map.

E consumes it.

Therefore D must not produce:

- READY;
- INSUFFICIENT;
- BLOCKED.

Those are Section Evidence Readiness outcomes.

The expected flow is:

```text
Expected Claim Map
        ↓
Which claim families are needed?
        ↓
Eligible Evidence
        ↓
Are the required families actually supported?
        ↓
Section Readiness (E)
```

## Known Implication for Current Production Evidence

The Expected Claim Map intentionally exposes an important production fact:

The presence of Entity, Question, Authority, Intent, SERP, or Business Evidence does not guarantee that substantive Coverage or Pricing claims exist.

This is not an error in those domain Evidence contracts. It is the reason the claim map exists.

If a required section claim family has no eligible Evidence, later readiness must surface the gap instead of allowing generic or unrelated Evidence to fill the section.

## D-Stage Invariants

1. Every recurring article section has an explicit expected claim space.
2. Claim coverage is evaluated by claim type/attribute, not Evidence count alone.
3. Required and supporting claim families are distinguishable.
4. Signal-only Evidence cannot satisfy an unrelated substantive claim family.
5. Domain labels do not substitute for claim coverage.
6. Question frequency never substitutes for an answer.
7. Business/SEO metrics never substitute for pricing or coverage facts.
8. Entity presence never substitutes for product capability or coverage.
9. Expected Claim Map does not replace the canonical Evidence schema.
10. Expected Claim Map does not define Source Authority, Diversity, Depth, or Freshness thresholds.
11. Expected Claim Map does not declare Section Readiness.
12. Missing required claim support must remain visible to E rather than being filled by fallback Evidence.

## Definition of D Completion

D is complete when the repository provides a deterministic, inspectable baseline map for each current article section that states:

- the section purpose;
- required claim families;
- supporting claim families;
- signal-only boundaries;
- claim type and attribute pairs;
- coverage interpretation;
- interaction with existing Evidence contracts;
- explicit separation between claim coverage and Evidence count;
- the hand-off boundary to Section Evidence Readiness.

The next stage is E — Section Evidence Readiness, which will evaluate whether the expected claim space is actually satisfied by eligible Evidence and return explicit readiness states.
