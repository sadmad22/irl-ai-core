# Section Evidence Readiness

Version: 1.0

## Purpose

Section Evidence Readiness defines the deterministic decision boundary that answers:

> Does this article section have enough eligible Evidence to proceed toward Article Generation?

It consumes:

- the canonical Evidence contract;
- B — Evidence Quality Contract;
- C — Quality Dimensions;
- D — Expected Claim Map;
- Section Evidence Eligibility results.

It produces one explicit readiness outcome for each article section:

- `READY`
- `INSUFFICIENT`
- `BLOCKED`

The result must be explainable from the evaluated inputs. It must never be reduced to Evidence count alone or to an opaque composite score.

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
Section Evidence Eligibility
        ↓
E — Section Evidence Readiness
        ↓
Article Writer
        ↓
Claim Grounding / Audit
```

E is a pre-generation gate.

E does not:

- redefine the canonical Evidence object;
- create Evidence;
- repair invalid Evidence;
- replace Section Evidence Eligibility;
- redefine Expected Claim Map;
- define Source Authority scoring;
- define final Depth/Diversity rubrics;
- generate article prose;
- publish content;
- create recommendations or decisions.

## Decision Inputs

For every section, readiness evaluation consumes four evidence-side inputs and one expectation input.

### 1. Expected Claim Map

The D-stage map identifies:

- required claim families;
- supporting claim families;
- signal-only inputs;
- `claim.type`;
- `claim.attribute`.

Required claim families are the minimum substantive claim space for the section.

### 2. Eligible Evidence

The evaluator must receive Evidence that has already crossed the Section Evidence Eligibility boundary.

E must not bypass or redo the eligibility decision by searching the full Content Brief Evidence pool.

An Evidence record that is not section-eligible cannot be counted toward readiness merely because it matches one of the expected claim names.

### 3. Evidence Contract / Integrity Result

Every Evidence item considered by E must have a known contract state.

Invalid or untraceable Evidence cannot contribute to a READY decision.

### 4. Quality Dimension Results

E consumes explainable dimension results defined by C.

These may include:

- Integrity;
- Relevance;
- Coverage;
- Authority;
- Diversity;
- Depth;
- Freshness;
- Lineage.

C owns the meaning of these dimensions.

E owns how dimension outcomes affect section readiness.

### 5. Section Context

The section heading/key and approved section purpose provide the context needed to keep the readiness decision tied to the actual article outline.

## Readiness States

### READY

The section has sufficient eligible Evidence for its expected claim space and satisfies all currently required quality/readiness conditions.

READY means:

> eligible for the next production step.

READY does not mean:

- factually perfect;
- published;
- automatically safe to publish without downstream claim grounding/audit;
- guaranteed to produce high-quality prose.

### INSUFFICIENT

The section has usable/eligible Evidence, but its expected claim space or required quality conditions are not sufficiently covered.

Typical reasons:

- one or more required claim families have no supporting Evidence;
- supporting Evidence is too shallow under the active Depth policy;
- source diversity is insufficient under the active Diversity policy;
- authority is inadequate under the active Source Authority policy;
- freshness is inadequate for a temporally sensitive claim.

INSUFFICIENT means:

> the section should not be treated as fully supported, but the underlying Evidence set is not necessarily structurally invalid.

### BLOCKED

A prerequisite required for safe evaluation or generation is invalid or missing.

Typical reasons:

- canonical Evidence contract violation;
- untraceable Evidence;
- broken required lineage;
- invalid/superseded/invalidated Evidence being presented as active support;
- section-level eligibility cannot be established or trusted when the section requires substantive support;
- an essential readiness input is missing and cannot safely be interpreted.

BLOCKED means:

> do not pass this section to the Writer.

## Deterministic Decision Order

Readiness must be evaluated in the following order to prevent weaker states from masking hard failures.

### Step 1 — Validate evaluation context

Required context:

- valid section identity;
- expected claim map entry;
- section-eligible Evidence reference set;
- Evidence records for those references;
- quality/contract results necessary for the active readiness policy.

Missing evaluation context is a readiness failure.

### Step 2 — Check hard Evidence validity

Reject Evidence that is:

- structurally invalid under the canonical contract;
- untraceable;
- missing required lineage when derived;
- invalid for downstream status use.

A hard invalidity affecting the required evidence basis yields `BLOCKED`.

### Step 3 — Preserve Section Eligibility

Only Evidence already accepted by the Section Evidence Eligibility boundary may contribute to claim coverage.

If the eligibility evaluation is missing or cannot be trusted, this is a hard prerequisite failure and the section is BLOCKED. If eligibility is valid but returns no supporting Evidence, the section is INSUFFICIENT because the claim space is unsupported.

No fallback to:

- unrelated Evidence;
- another section's Evidence;
- raw Content Brief Evidence that failed section eligibility;
- business/SEO signals for substantive pricing or coverage claims.

### Step 4 — Evaluate required claim families

For every D-stage required claim family, determine whether at least one eligible Evidence record supports the exact claim family:

```text
claim.type + claim.attribute
```

The evaluator must not match a different claim merely because the wording is similar.

If an essential required claim family is missing:

```text
required claim family missing
        ↓
INSUFFICIENT
```

### Step 5 — Evaluate readiness dimensions

Apply the active dimension requirements to the Evidence supporting the section.

The decision must remain dimension-specific.

Examples:

- Integrity failure → BLOCKED.
- Lineage failure that prevents traceability → BLOCKED.
- Relevance failure for required Evidence → INSUFFICIENT or BLOCKED depending on whether safe eligible support remains.
- Coverage gap → INSUFFICIENT.
- Authority failure → INSUFFICIENT under the active authority policy.
- Diversity failure → INSUFFICIENT under the active diversity policy.
- Depth failure → INSUFFICIENT under the active depth policy.
- Freshness failure → INSUFFICIENT when the claim is time-sensitive.

### Step 6 — Handle UNKNOWN explicitly

An UNKNOWN dimension result is never converted into PASS.

If the missing input is essential to safe generation, readiness cannot be READY.

The result is:

- `BLOCKED` when the missing information prevents safe evaluation itself;
- `INSUFFICIENT` when the section can be evaluated but cannot demonstrate the required quality condition.

The exact mapping must be included in the readiness reasons.

### Step 7 — Produce the final state

The state follows:

```text
hard prerequisite failure
        → BLOCKED

otherwise, required claim/quality condition not met
        → INSUFFICIENT

otherwise
        → READY
```

No fourth state is introduced in E.

## Reason Model

Every non-READY result must carry machine-readable and human-readable reasons.

The reason should identify:

- section key/index;
- failed or missing dimension;
- expected claim type;
- expected claim attribute;
- affected Evidence IDs when known;
- whether the issue is missing, invalid, unresolved, or insufficient;
- the layer that owns remediation.

Recommended reason-code families:

| Code | Meaning |
| --- | --- |
| `context_missing` | Required evaluation context is absent |
| `evidence_contract_invalid` | Evidence violates the canonical/B contract |
| `evidence_untraceable` | Source/provenance/lineage cannot be established |
| `evidence_not_section_eligible` | Evidence cannot contribute to this section |
| `required_claim_missing` | Required claim family has no eligible support |
| `coverage_insufficient` | Expected claim space is not sufficiently covered |
| `authority_insufficient` | Source authority requirement not satisfied |
| `diversity_insufficient` | Independent-source requirement not satisfied |
| `depth_insufficient` | Substantive Evidence requirement not satisfied |
| `freshness_insufficient` | Temporal requirement not satisfied |
| `dimension_unknown` | Required dimension cannot currently be evaluated |
| `lineage_invalid` | Required Evidence lineage is broken |

Reason codes are explanations, not scoring components.

## Section-Level Output Contract

Before H introduces a formal schema, the conceptual E result is:

```text
section_index
section_key
readiness
eligible_evidence_refs
supported_required_claims
missing_required_claims
dimension_results
reasons
audit
```

Where:

- `readiness` ∈ `READY | INSUFFICIENT | BLOCKED`;
- `eligible_evidence_refs` contains only Evidence accepted for this section;
- `supported_required_claims` records the required claim families actually supported;
- `missing_required_claims` records expected families without acceptable support;
- `dimension_results` preserves the underlying C outcomes;
- `reasons` explains the readiness state;
- `audit` identifies the readiness method/version and validation state.

This is a semantic contract at E. Formal schema changes belong to H.

## Seven-Section Baseline

The current article outline contains seven recurring sections.

E applies the same decision model to all of them:

1. Introduction
2. What You Need to Know
3. Coverage and Key Factors
4. Costs and Pricing Factors
5. How to Compare Options
6. Frequently Asked Questions
7. Sources and Editorial Methodology

The actual claim requirements are taken from D, not redefined in E.

## Expected Readiness Logic by Section

### Introduction

READY requires demonstrated support for the required Introduction claim families in D.

Intent or entity signals alone cannot satisfy substantive definition/scope requirements.

If only surface SERP/intent/entity signals exist, the section is not READY.

### What You Need to Know

READY requires the foundational claim families defined by D.

Question frequency or entity-presence Evidence alone cannot establish who needs the product/topic, its scope, or primary use.

### Coverage and Key Factors

READY requires eligible substantive Evidence for the required coverage/benefit/exclusion claim families.

Authority, entity, intent, SERP, or business signals alone cannot establish coverage terms.

### Costs and Pricing Factors

READY requires eligible substantive pricing Evidence for the required pricing/premium/cost-driver space.

Business value, CPC, search volume, affiliate potential, conversion potential, or AdSense potential cannot satisfy pricing claims.

### How to Compare Options

READY requires evidence-backed comparison criteria and factual differences between options.

Provider/entity presence or SERP ranking alone cannot satisfy comparison facts.

### Frequently Asked Questions

READY requires both:

- Evidence describing the expected question/FAQ need;
- Evidence supporting the answer itself.

Question frequency alone is not answer support.

### Sources and Editorial Methodology

READY requires traceable source/provenance/lineage support for the methodology claims defined by D.

Authority score alone does not constitute a methodology description.

## Required Claim Coverage Rule

The central E rule is:

```text
required claim family
        +
eligible supporting Evidence
        +
required quality conditions
        =
candidate for READY
```

The following is explicitly invalid:

```text
many Evidence records
        =
READY
```

Evidence quantity is never a substitute for claim coverage.

## Supporting Claim Families

Supporting claim families improve completeness but do not replace missing required families.

A section with all supporting claims but a missing required claim family remains:

```text
INSUFFICIENT
```

unless a hard prerequisite failure makes it:

```text
BLOCKED
```

## Quality Dimension Ownership

E consumes the dimensions; it does not redefine them.

| Concern | Owner |
| --- | --- |
| Canonical Evidence structure | Evidence Contract / Schema |
| Minimum Evidence acceptance | B |
| Dimension semantics | C |
| Expected claim families | D |
| Section readiness state and reasons | E |
| Source authority policy | F |
| Depth / diversity operational rules | G |
| Formal schema | H |
| Automated readiness tests | I |
| Pipeline enforcement | J |
| Regression / real article behavior | K |

This ownership prevents E from becoming a second competing Evidence architecture.

## Fail-Closed Rules

The readiness layer must fail closed when:

1. required Evidence is invalid;
2. required lineage is broken;
3. section eligibility cannot be trusted;
4. an essential evaluation input is missing;
5. a required claim family has no valid eligible support;
6. a freshness/authority/depth/diversity condition required by the active policy cannot be established.

Fail-closed means withholding the section from Writer progression.

It does not mean inventing a replacement claim or selecting unrelated Evidence.

## No Fallback Evidence

E must never implement:

```text
expected evidence missing
        ↓
pick another Evidence record
        ↓
pretend the section is ready
```

This preserves the hardening already established in Section Evidence Eligibility.

## No Composite Readiness Score

E produces a categorical state with reasons.

It does not produce a hidden weighted quality score.

A readiness state must always be reconstructable from explicit conditions.

Therefore:

```text
READY
```

means a known set of required conditions passed.

It must never mean:

```text
score >= arbitrary threshold
```

## Legacy Evidence Boundary

Legacy Evidence with non-canonical source/provenance structure must not receive implicit readiness credit merely because a matching claim happens to exist.

If the Evidence cannot satisfy the B/C requirements required by the active readiness policy, the affected section cannot be READY.

Migration is outside E.

## Protected Data and Lineage

E must not:

- modify protected research fixtures to obtain READY;
- mutate `.irl-ai-core.env`;
- replace Evidence IDs;
- fabricate lineage;
- rewrite upstream ResearchReport/Decision/Strategy/Brief artifacts to satisfy readiness;
- weaken Writer or Claim Audit safeguards.

## Auditability

A readiness result must be reproducible from:

```text
Content Brief / section context
        +
D Expected Claim Map version
        +
eligible Evidence IDs
        +
Evidence quality/dimension results
        +
readiness policy version
```

The audit trail must make clear which claim families passed, which were missing, and why the final state was chosen.

## E-Stage Invariants

1. Every current article section receives exactly one readiness state.
2. The only states are READY, INSUFFICIENT, and BLOCKED.
3. READY requires explicit satisfaction of required claim coverage and active quality requirements.
4. Missing required claim support never becomes READY because other Evidence exists.
5. Invalid or untraceable required Evidence produces a blocked path rather than silent substitution.
6. Section eligibility remains an upstream boundary.
7. Supporting claim families never replace required claim families.
8. Evidence count is never a readiness criterion by itself.
9. UNKNOWN never silently becomes PASS.
10. E does not invent Source Authority, Depth, Diversity, or Freshness thresholds; it consumes the policies established by their owning layers.
11. No composite readiness score is introduced.
12. Downstream Writer, Claim Grounding, and Claim Audit safeguards remain intact.
13. Readiness results are auditable and reproducible.
14. Protected fixtures and secret environment files remain outside the change scope.

## Definition of E Completion

E is complete when the repository has an explicit and deterministic readiness contract that:

- defines READY / INSUFFICIENT / BLOCKED;
- specifies the decision order;
- requires claim-family coverage rather than Evidence count;
- consumes section-eligible Evidence only;
- distinguishes hard prerequisite failures from insufficiency;
- preserves C dimension semantics;
- provides explainable reason codes;
- defines a conceptual section-level output;
- covers the seven current article sections without redefining D;
- fails closed when essential requirements are missing;
- does not introduce a composite quality score;
- leaves formal schema, tests, and pipeline enforcement to H, I, and J.

The next production step is F — Source Authority Model.
