# Evidence Quality Contract

Version: 1.0

## Purpose

The Evidence Quality Contract defines the minimum quality and integrity conditions that Research Evidence must satisfy before it can be considered for downstream Article Generation.

This contract is a quality gate contract. It does not replace the canonical Evidence Contract, Section Evidence Eligibility, Claim Grounding, or Claim Audit.

The contract closes one specific architectural gap:

> Evidence existence is not sufficient evidence quality for Article Generation.

The contract therefore defines what must be true before Evidence is allowed to participate in later section-level readiness decisions.

## Architectural Position

The production boundary is:

```text
Research Sources
      ↓
Analyzers / Connectors
      ↓
Canonical Research Evidence
      ↓
Evidence Quality Contract
      ↓
Section Evidence Readiness
      ↓
Content Brief
      ↓
Section Evidence Eligibility
      ↓
Article Writer
      ↓
Claim Grounding / Audit
```

Evidence Quality is upstream of generation. It does not generate article prose and it does not decide whether a specific section is READY.

## Relationship to the Canonical Evidence Contract

The canonical Research Evidence Contract remains authoritative.

This document does not introduce:

- a second Evidence object schema;
- a replacement for `shared/schemas/evidence.schema.json`;
- a new Evidence identity;
- new production-lineage identifiers;
- recommendation or decision semantics.

The quality contract evaluates canonical Evidence; it does not redefine it.

Canonical requirements remain governed by:

- `docs/architecture/evidence-contract.md`
- `shared/schemas/evidence.schema.json`

Domain-specific minimum claim surfaces remain governed by the existing domain contracts, including:

- `docs/architecture/domain-evidence-minimum.md`

Editorial Source Evidence remains governed separately by:

- `docs/architecture/editorial-source-evidence-contract.md`

## Contract Scope

The B-stage contract is intentionally limited to hard minimum conditions that can be evaluated without introducing the later quality dimensions.

It covers:

1. canonical structural integrity;
2. traceable Evidence identity;
3. claim/value presence;
4. source and provenance presence;
5. confidence and status validity;
6. derived-evidence lineage;
7. explicit distinction between Evidence and analyzer metadata;
8. fail-closed handling of missing essential information.

The following remain later-stage policies and are not defined by this contract:

- Expected Claim Map;
- Section Sufficiency;
- Source Authority scoring;
- Source Diversity scoring;
- Evidence Depth rubric;
- Freshness policy;
- composite Evidence Quality scores;
- section READY / INSUFFICIENT / BLOCKED decisions.

Those belong to the subsequent C–G and E layers in the production work plan.

## Minimum Contract Requirements

An Evidence record is contract-compliant only when all required canonical fields are structurally present and valid.

### 1. Identity

The record must contain:

- `evidence_id`;
- `report_id`;
- `schema_version`.

The `evidence_id` must identify the Evidence record and must not be fabricated or silently replaced during quality evaluation.

### 2. Evidence Classification

The record must contain:

- `type`;
- `domain`;
- `subject`.

The `type` must be one of the canonical Evidence types:

- `observation`;
- `derived`;
- `comparison`;
- `contradiction`.

The `domain` remains extensible and must not be restricted by a new quality-layer enum.

### 3. Claim and Value

The record must contain a canonical `claim` with:

- `claim.type`;
- `claim.attribute`.

The record must also contain a canonical `value` with:

- `value.type`;
- `value.data`.

The quality contract does not decide whether a claim is sufficiently useful for a specific section. It only requires that the Evidence actually expresses a structured claim/value pair.

### 4. Source Traceability

The record must contain the canonical `source` object with:

- `source.type`;
- `source.source_id`;
- `source.provider`;
- `source.retrieved_at`.

The quality contract does not redefine the meaning of source metadata.

Source metadata answers:

> Where did the underlying information come from?

A missing or unusable source locator is a traceability defect. The quality layer must not invent, infer, or silently substitute source identity.

### 5. Provenance

The record must contain the canonical `provenance` object with:

- `provenance.analyzer`;
- `provenance.analyzer_version`;
- `provenance.method`.

Provenance answers:

> Which engine, version, and method produced this Evidence?

Analyzer metadata is provenance; it is not Evidence quality by itself.

### 6. Confidence

`confidence` must be numeric and normalized to the canonical range 0..1.

The quality contract does not convert confidence into a standalone Evidence Quality score.

A high confidence value does not make weak or irrelevant Evidence sufficient for a section.

### 7. Relation

The record must contain a canonical `relation`:

- `supports`;
- `contradicts`;
- `qualifies`;
- `neutral`.

The quality layer must preserve the recorded relation rather than reinterpret it as a recommendation or decision.

### 8. Status

The record must contain a valid canonical `status`:

- `active`;
- `superseded`;
- `invalidated`.

Only Evidence that is valid for current downstream use may participate in generation readiness.

An Evidence item marked `superseded` or `invalidated` must not be treated as current supporting material merely because its identifier is still present in a Content Brief lineage.

### 9. Capture and Lineage

The record must contain:

- `captured_at`;
- `derived_from`.

For Evidence of type `derived`, upstream Evidence references in `derived_from` are mandatory.

A derived record without traceable upstream Evidence is not contract-compliant.

The quality layer must preserve lineage. It must never replace a missing lineage reference with an invented parent or an unrelated Evidence record.

## Evidence Eligibility Boundary

The Quality Contract and Section Evidence Eligibility answer different questions.

### Evidence Quality Contract

> Is this Evidence structurally valid, traceable, and safe to evaluate further?

### Section Evidence Eligibility

> Does this valid Evidence belong to this specific article section?

Section eligibility remains the responsibility of the existing section-grounding layer.

Therefore:

- contract compliance does not imply section relevance;
- section relevance does not imply section sufficiency;
- section sufficiency is defined later by the Section Evidence Readiness layer.

The system must not use contract-compliant Evidence as a reason to bypass section-level eligibility.

## Evidence Quality Is Not Evidence Count

The number of Evidence records is not itself a quality or sufficiency criterion.

These cases remain distinct:

```text
0 valid Evidence
→ not ready for generation

many invalid Evidence records
→ still not ready

many repetitive Evidence records
→ not proven sufficient

few valid Evidence records
→ may be useful, but sufficiency is decided later

valid + relevant + sufficiently deep/diverse Evidence
→ eligible for later Section Readiness evaluation
```

No numeric threshold is introduced here to claim that a section is sufficiently supported.

## Signal vs Substantive Evidence Boundary

The B-stage contract does not yet define the full Evidence Depth rubric.

However, it establishes the architectural rule that analyzer signals and substantive Evidence are not interchangeable.

Examples such as:

- authority scores;
- search metrics;
- intent labels;
- entity-presence signals;
- commercial-value signals;

may be valid Evidence under their domain contracts, but their presence alone does not establish that a section has substantive material from which a respectable factual passage can be written.

The distinction is intentionally deferred to the later Depth and Diversity layer.

## Source Authority Boundary

The B-stage contract requires source traceability, but it does not define a source-authority ranking model.

In particular:

- source metadata is not an authority score;
- provenance is not source authority;
- a known provider does not automatically establish that the source is authoritative for every claim;
- authority policy will be defined separately in the Source Authority layer.

## Source Diversity Boundary

Multiple Evidence records do not automatically represent multiple independent sources.

Evidence derived from the same artifact, page, dataset, or upstream source must not be counted as independent simply because it has different `evidence_id` values.

Independence and diversity are deferred to the later Diversity layer.

## No Composite Quality Score

This contract deliberately does not define a single opaque Evidence Quality number.

No downstream component may infer:

```text
quality_score >= threshold  ⇒  article-ready
```

without the later dimensions and explicit readiness rules.

The production architecture favors explainable gates over an untraceable composite score.

## Fail-Closed Rules

The following conditions are hard failures for contract compliance:

1. canonical required structure is missing or malformed;
2. Evidence identity cannot be established;
3. claim or value structure is missing;
4. source or provenance structure is missing;
5. confidence is outside the canonical range or is not numeric;
6. status is invalid;
7. a derived Evidence record lacks required upstream lineage;
8. essential traceability information has been silently fabricated or substituted.

When a hard requirement is missing, the system must fail closed.

It must not:

- invent Evidence;
- copy unrelated Evidence;
- select a fallback Evidence record only to avoid an empty section;
- transform a signal into a factual claim without supporting Evidence;
- downgrade the contract requirement to keep the Writer running.

## Compatibility With Existing Production Layers

This contract must preserve the current production guarantees:

- `section_evidence_grounding.py` remains the Section Evidence Eligibility layer;
- `article_writer.py` must continue to reject an empty section Evidence package;
- `claim_evidence_grounding.py` continues to ground generated claims;
- `claim_audit.py` continues to fail closed when claims lack support;
- protected research fixtures remain unchanged during Evidence Quality implementation;
- Evidence lineage remains traceable to the Content Brief and Research Evidence.

The contract is additive. It must not weaken existing fail-closed behavior.

## Compatibility With Current Transitional Data

The repository currently contains Evidence artifacts produced by more than one generation of source/provenance shape.

This contract therefore defines the target production contract, while migration and enforcement of the canonical schema are handled separately.

The quality layer must not silently normalize legacy records into canonical records and then treat them as if the original contract had been satisfied.

Where a required canonical field cannot be established from the actual record, the result must remain non-compliant until a later explicit migration or producer fix supplies the required information.

## Implementation Boundary for B

B is complete when the repository contains this explicit contract and the subsequent implementation can evaluate Evidence against it without changing the canonical Evidence model.

B does not require:

- a new LLM;
- a new score field in Evidence;
- Writer changes;
- ResearchReport redesign;
- source-authority scoring;
- section claim maps;
- section readiness states.

Those are intentionally separate production steps.

## Contract Invariants

The following invariants are non-negotiable:

1. Canonical Evidence remains the single factual Evidence representation.
2. Quality evaluation does not create a second Evidence identity.
3. Evidence Quality does not produce recommendations or decisions.
4. Evidence count is never a sufficient quality criterion.
5. A valid Evidence record is not automatically relevant to every section.
6. Section Eligibility is not the same as Section Readiness.
7. Repeated Evidence from one artifact is not automatically independent source diversity.
8. Weak Evidence must not be promoted by an opaque numeric score.
9. Missing essential requirements fail closed.
10. Evidence lineage must never be fabricated or silently broken.
11. Protected production fixtures and secret environment files are outside the scope of this contract change.

## Definition of Contract Compliance

For B, an Evidence record is contract-compliant when:

- canonical structure is present and valid;
- identity is established;
- claim and value are structured;
- source and provenance are traceable;
- confidence and relation are valid;
- status is valid for downstream evaluation;
- required lineage is present for derived Evidence;
- no required information has been invented or silently substituted.

Contract compliance means:

> safe to evaluate further.

It does not mean:

> sufficient for a section.

It does not mean:

> safe to publish.

It does not mean:

> guaranteed factual accuracy.

## Planned Follow-on Layers

The Evidence Quality work plan continues after B with:

- C — Quality Dimensions;
- D — Expected Claim Map;
- E — Section Evidence Readiness;
- F — Source Authority Model;
- G — Evidence Depth & Diversity Rules;
- H — Schema;
- I — Tests;
- J — Engine Integration;
- K — Regression + E2E.

Each later layer must build on this contract without redefining the canonical Evidence model.

## Source of Truth

This contract is derived from the production Evidence Quality & Section Readiness Work Plan and the repository's existing canonical architecture.

Primary references:

- `docs/architecture/evidence-contract.md`
- `docs/architecture/domain-evidence-minimum.md`
- `docs/architecture/editorial-source-evidence-contract.md`
- `shared/schemas/evidence.schema.json`
- `IRL_AI_Core_Evidence_Quality_Section_Readiness_Work_Plan_AR`

The production work plan remains the sequencing authority. This document is the B-stage contract within that plan.
