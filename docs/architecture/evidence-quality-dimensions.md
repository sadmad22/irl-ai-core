# Evidence Quality Dimensions

Version: 1.0

## Purpose

This document defines the semantic dimensions used to assess Research Evidence quality before Section Evidence Readiness and Article Generation.

It implements the C-stage requirement of the production Evidence Quality & Section Readiness Work Plan:

- Integrity
- Relevance
- Coverage
- Authority
- Diversity
- Depth
- Freshness
- Lineage

The dimensions are evaluation boundaries, not a replacement Evidence schema and not a single opaque quality score.

The B-stage Evidence Quality Contract remains the minimum contract for structurally valid, traceable Evidence. This document defines what additional questions the quality layer asks about that Evidence.

## Architectural Position

```text
Research Sources
      ↓
Analyzers / Connectors
      ↓
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
Content Brief / Section Eligibility
      ↓
Article Writer
      ↓
Claim Grounding / Audit
```

C evaluates Evidence as Evidence.

C does not:

- generate prose;
- decide publication;
- define the Expected Claim Map;
- declare a section READY;
- replace Section Eligibility;
- replace Claim Grounding or Claim Audit;
- create recommendation or decision semantics.

## Dimension Model

Each dimension answers one independent question.

| Dimension | Core question | Primary boundary |
| --- | --- | --- |
| Integrity | Is the Evidence record valid under the canonical contract? | Structural and contract validity |
| Relevance | Does the Evidence materially relate to the research topic and/or evaluated section context? | Topical/section fit |
| Coverage | Does the available Evidence cover the expected claim space? | Claim-type coverage |
| Authority | Is the underlying source appropriate and authoritative for this claim? | Source quality |
| Diversity | Are supporting records materially independent rather than repeated views of one artifact? | Source independence |
| Depth | Does the Evidence contain substantive factual material rather than only a surface signal? | Writing usefulness |
| Freshness | Is the Evidence temporally appropriate for the claim being made? | Temporal suitability |
| Lineage | Can the Evidence and its derivations be traced to known upstream records? | Provenance continuity |

These dimensions are intentionally orthogonal. A record may pass one dimension and fail another.

Examples:

- valid Evidence can be irrelevant;
- relevant Evidence can be shallow;
- authoritative Evidence can be stale;
- multiple Evidence records can be valid but non-diverse;
- deep Evidence can still lack expected claim coverage.

## Evaluation States

C uses explainable dimension states rather than a composite score.

Allowed semantic outcomes for a dimension are:

### PASS

The dimension's requirements are demonstrably satisfied by available data.

### FAIL

The available data directly violates a defined requirement.

### UNKNOWN

The dimension cannot yet be determined because a required input or policy context is missing.

UNKNOWN must not be silently converted to PASS.

Later readiness logic may map UNKNOWN to INSUFFICIENT or BLOCKED depending on whether the missing information is essential. That mapping belongs to E — Section Evidence Readiness.

## 1. Integrity

### Question

Is the Evidence record complete and compliant with the canonical Evidence contract?

### Required basis

Integrity uses:

- `shared/schemas/evidence.schema.json`;
- `docs/architecture/evidence-contract.md`;
- B — Evidence Quality Contract.

### PASS conditions

The record has:

- required canonical identity;
- canonical Evidence type and domain;
- valid subject;
- structured claim and value;
- source and provenance;
- normalized confidence;
- valid relation;
- valid status;
- capture timestamp;
- required derived lineage.

### FAIL conditions

Examples include:

- malformed required field;
- invalid enum;
- missing source/provenance structure;
- invalid confidence;
- missing lineage for derived Evidence;
- invalid status.

### Boundary

Integrity does not establish:

- topical relevance;
- source authority;
- depth;
- diversity;
- section sufficiency.

A structurally valid record is merely safe to evaluate further.

## 2. Relevance

### Question

Does the Evidence materially relate to the research subject and, when evaluated for generation, to the intended section context?

### Evaluation basis

Relevance may use:

- Evidence domain;
- claim type and attribute;
- subject identity;
- claim/value content;
- report topic;
- section heading/purpose;
- explicit Evidence-to-section eligibility rules.

### PASS conditions

The record contains a substantive connection between the Evidence claim and the evaluated topic/section requirement.

The connection must be explainable from the Evidence itself and the known research/section context.

### FAIL conditions

Examples include:

- Evidence belongs to an unrelated domain for the section;
- claim/value has no material relationship to the section requirement;
- record is only present because it shares a generic token with the section;
- unrelated business/SEO signals are used as factual support for a cost, coverage, or other substantive section.

### UNKNOWN conditions

Relevance is UNKNOWN when the system lacks sufficient topic or section context to evaluate it reliably.

### Boundary

Current deterministic Section Evidence Eligibility remains the section-specific implementation boundary. C does not weaken or replace it.

## 3. Coverage

### Question

Does the Evidence set cover the expected claim space required by the evaluated section?

### Evaluation basis

Coverage is a set-level dimension. It cannot be decided from Evidence count alone.

It will consume the Expected Claim Map introduced in D.

A coverage evaluation may inspect:

- claim.type;
- claim.attribute;
- section requirement;
- supporting Evidence relations;
- active status;
- relevance state.

### PASS conditions

All essential claim categories defined for the section have sufficient supporting Evidence under the later D/E rules.

### FAIL conditions

Coverage fails when an essential claim category is explicitly required but no eligible Evidence supports it.

### UNKNOWN conditions

Coverage is UNKNOWN before the Expected Claim Map exists or when the required claim expectations are incomplete.

### Boundary

Coverage is not:

- number of Evidence records;
- lexical similarity count;
- number of paragraphs;
- Writer output length.

No fixed Evidence-count threshold can substitute for claim coverage.

## 4. Authority

### Question

Is the source appropriate and sufficiently authoritative for the claim being evaluated?

### Evaluation basis

Authority uses source information, not provenance metadata alone.

Relevant inputs can include:

- source identity;
- provider;
- source type;
- source classification;
- claim domain;
- later Source Authority policy.

### PASS conditions

The source is classified as acceptable for the claim under the Source Authority policy.

### FAIL conditions

The source is explicitly disallowed or materially inadequate for the claim under that policy.

### UNKNOWN conditions

Authority is UNKNOWN when the source classification or applicable authority policy is absent.

### Boundary

C does not create a source-tier hierarchy or numeric authority score.

That detailed policy belongs to F — Source Authority Model.

In particular:

- `provider` is not an authority score;
- `provenance.analyzer` is not source authority;
- an Evidence record being canonical does not make its source authoritative.

## 5. Diversity

### Question

Does the supporting Evidence represent materially independent sources or independent upstream observations?

### Evaluation basis

Diversity must consider:

- source identity;
- source artifact/page/dataset where available;
- upstream lineage;
- duplicated or derivative records;
- number of independent source families.

### PASS conditions

Supporting Evidence contains sufficient independent source representation under the later diversity policy.

### FAIL conditions

The set is materially repetitive, for example when several Evidence records are different projections, fields, or derivations of one underlying artifact and are counted as though they were independent sources.

### UNKNOWN conditions

Source identity or lineage is insufficient to determine independence.

### Boundary

Different `evidence_id` values do not imply different sources.

The same artifact producing several Evidence records is not automatically source diversity.

Detailed independence and diversity rules are defined in G — Evidence Depth & Diversity Rules.

## 6. Depth

### Question

Is the Evidence substantive enough to support factual writing, rather than being only a surface signal?

### Evaluation basis

Depth may inspect:

- claim/value substance;
- descriptive factual detail;
- specificity;
- explanatory material;
- direct source-backed content;
- whether the record can support a factual statement without inventing missing information.

### PASS conditions

The Evidence contains material that can support a substantive factual claim or passage within the evaluated context.

### FAIL conditions

The record is only a surface signal for the intended use, with no sufficient factual substance.

Examples of signals that may be valid Evidence but are not automatically deep support:

- authority scores;
- search metrics;
- intent labels;
- entity-presence signals;
- commercial-value signals.

### UNKNOWN conditions

Depth is UNKNOWN when the available Evidence representation does not contain enough information to distinguish signal from substantive factual material.

### Boundary

C establishes the distinction but does not define the final depth rubric or threshold.

The detailed operational rubric belongs to G — Evidence Depth & Diversity Rules.

## 7. Freshness

### Question

Is the Evidence temporally appropriate for the claim being evaluated?

### Evaluation basis

Freshness should use actual timestamps where available, including:

- `source.retrieved_at`;
- `captured_at`;
- upstream source publication/update time when available.

Freshness is claim-dependent. There is no universal age threshold that is correct for every Evidence domain.

### PASS conditions

The evidence age is acceptable for the claim's temporal sensitivity under the applicable freshness policy.

### FAIL conditions

The evidence is demonstrably too old for a claim that requires more current information, under that policy.

### UNKNOWN conditions

Freshness is UNKNOWN when relevant timestamps are missing or when the temporal sensitivity of the claim has not yet been classified.

### Boundary

A timestamp proves when information was captured or retrieved; it does not by itself prove current validity.

Freshness is also not a substitute for authority or relevance.

The operational freshness policy may introduce claim/domain volatility classes later without changing the canonical Evidence object.

## 8. Lineage

### Question

Can the Evidence be traced back to its known upstream origin and transformation path?

### Evaluation basis

Lineage uses:

- `evidence_id`;
- `report_id`;
- `derived_from`;
- source;
- provenance;
- upstream Evidence references.

### PASS conditions

The lineage is internally consistent and can be followed from derived Evidence to its known upstream Evidence records.

### FAIL conditions

Examples include:

- derived Evidence with missing required parents;
- broken or unresolved upstream reference;
- lineage identity replaced without documented migration;
- silent substitution of an unrelated Evidence record.

### UNKNOWN conditions

Lineage is UNKNOWN when upstream records are not available to verify an otherwise present reference.

### Boundary

Lineage does not determine factual truth by itself.

It establishes traceability and auditability.

## Cross-Dimension Rules

### Independence

A dimension result must not be used as a proxy for another dimension.

Examples:

- PASS Integrity does not imply PASS Relevance.
- PASS Authority does not imply PASS Freshness.
- PASS Diversity does not imply PASS Depth.
- PASS Relevance does not imply PASS Coverage.

### Evidence-set evaluation

Some dimensions are naturally record-level:

- Integrity;
- basic Relevance;
- basic Freshness;
- basic Lineage.

Some are naturally set-level:

- Coverage;
- Diversity;
- Section-level Depth.

The implementation must preserve this distinction rather than assigning identical logic to every Evidence record.

### Missing information

Missing essential information produces FAIL or UNKNOWN according to the nature of the missing requirement.

It must never be replaced with fabricated values.

### Legacy data

Evidence artifacts produced with legacy source/provenance shapes must not receive an automatic PASS for Integrity merely because they resemble canonical Evidence.

Migration is a separate operation.

### Protected fixtures

The quality-dimension implementation must not modify protected production fixtures solely to make dimension evaluations pass.

## No Composite Quality Score

C deliberately defines no formula such as:

```text
quality = weighted sum of dimensions
```

and no universal threshold such as:

```text
quality >= X  => generation-ready
```

The purpose of C is explainability.

Later readiness logic may define explicit requirements across dimensions, but those requirements must remain inspectable and dimension-specific.

## Dimension-to-Layer Ownership

| Concern | Owning layer |
| --- | --- |
| Canonical Evidence structure | Evidence Contract / Schema |
| Minimum contract compliance | B — Evidence Quality Contract |
| Dimension semantics | C — Quality Dimensions |
| Expected claim types per section | D — Expected Claim Map |
| READY / INSUFFICIENT / BLOCKED | E — Section Evidence Readiness |
| Source authority policy | F — Source Authority Model |
| Depth and diversity operational rules | G — Evidence Depth & Diversity Rules |
| Official schema additions | H — Schema |
| Automated tests | I — Tests |
| Pipeline enforcement | J — Engine Integration |
| Real article regression | K — Regression + E2E |

## Compatibility With Existing Production Guarantees

C must preserve:

- canonical Evidence identity;
- evidence lineage;
- explicit Content Brief evidence references;
- deterministic section eligibility;
- Writer rejection of empty Evidence packages;
- Claim Grounding with required matching;
- Claim Audit fail-closed behavior;
- protected research fixtures;
- secret environment files outside the change scope.

C is an assessment layer. It must not weaken downstream safeguards in order to produce a more complete-looking article.

## C-Stage Invariants

1. Every dimension has one explicit question.
2. Dimension PASS never means article-ready by itself.
3. Evidence count never substitutes for Coverage.
4. Canonical validity never substitutes for Relevance.
5. Source metadata never substitutes for Authority.
6. Multiple evidence IDs never substitute for Diversity.
7. Surface signals never automatically count as substantive Depth.
8. Timestamps never automatically prove current validity.
9. Lineage must remain traceable and must not be fabricated.
10. UNKNOWN must not silently become PASS.
11. No opaque composite quality score is introduced.
12. C does not modify the canonical Evidence object model.

## Definition of C Completion

C is complete when the repository has a documented, explainable definition for:

- Integrity;
- Relevance;
- Coverage;
- Authority;
- Diversity;
- Depth;
- Freshness;
- Lineage;

and when the document clearly states:

- each dimension's evaluation question;
- its principal inputs;
- PASS / FAIL / UNKNOWN semantics;
- its boundaries with neighboring layers;
- the later layer responsible for detailed implementation where deferred;
- the prohibition on evidence-count sufficiency and opaque composite scoring.

C does not require implementation of the readiness engine. That belongs to I–J after D–H.
