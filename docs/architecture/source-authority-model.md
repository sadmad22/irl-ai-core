# Source Authority Model

Version: 1.0

## Purpose

The Source Authority Model defines how the Evidence Quality layer evaluates whether an underlying source is appropriate and authoritative for the claim being supported.

It implements F in the production Evidence Quality & Section Readiness Work Plan:

> Add a clear source model where needed, without mixing source metadata with provenance.

The model is claim-relative.

It does not assume that one source is universally authoritative for every claim.

## Architectural Position

```text
Underlying Source
      ↓
Canonical Evidence
      ↓
B — Evidence Quality Contract
      ↓
C — Quality Dimensions
      ↓
F — Source Authority Model
      ↓
E — Section Evidence Readiness
      ↓
Article Writer
```

F is a policy layer over the canonical `source` information.

It does not replace:

- the canonical Evidence Contract;
- the Evidence schema;
- provenance;
- Section Eligibility;
- Expected Claim Map;
- Section Readiness;
- Claim Grounding / Audit.

## Core Principle

Authority is a property of the relationship:

```text
source + claim + context
```

not a universal property of a domain name, provider, or Evidence record.

The same source may be highly authoritative for one claim and insufficient for another.

Examples:

- a government regulator may be authoritative for a regulatory requirement;
- an insurer's policy document may be authoritative for that insurer's own plan terms;
- an independent professional organization may be suitable for professional guidance;
- a search result snippet may be useful for discovery but is not automatically authoritative support for a substantive claim.

## Separation of Source, Provenance, and Evidence Confidence

These concepts remain distinct.

### Source

Answers:

> Where did the underlying information come from?

Canonical Evidence currently records source metadata such as:

- `source.type`;
- `source.source_id`;
- `source.provider`;
- `source.retrieved_at`.

### Provenance

Answers:

> Which analyzer, version, and method transformed source material into this Evidence record?

Canonical Evidence records:

- `provenance.analyzer`;
- `provenance.analyzer_version`;
- `provenance.method`.

### Evidence confidence

Answers:

> How confident is the system in this Evidence record?

`confidence` is normalized to 0..1.

### Authority

Answers:

> Is this underlying source appropriate and sufficiently authoritative for this particular claim?

Authority must not be inferred from:

- Evidence confidence alone;
- analyzer identity;
- analyzer version;
- provenance method;
- retrieval timestamp.

## Authority Classes

The model uses source classes rather than a universal numeric ranking.

### Class A — Primary / Official

The source is the authoritative origin of the information or directly controls the subject matter.

Typical examples:

- government agencies and regulators;
- statutory or official regulatory publications;
- an insurer's official policy, certificate, benefit schedule, or plan documentation for that insurer's own product terms;
- an organization's official contractual or procedural documentation for its own services.

Typical claim suitability:

- regulations and legal requirements;
- official policy terms;
- official eligibility rules;
- official product features when the source directly owns the product.

### Class B — Authoritative Institutional / Professional

The source is a recognized institution or professional body with domain competence, but is not necessarily the legal or contractual origin of every fact.

Typical examples:

- professional associations;
- recognized medical/professional institutions;
- established academic or institutional publications.

Typical claim suitability:

- professional guidance;
- explanatory standards;
- domain practices;
- general educational context.

### Class C — Reputable Secondary

The source provides secondary reporting, comparison, analysis, or explanatory material from an identifiable publisher with a meaningful editorial process.

Typical examples:

- established specialist publications;
- reputable independent comparison/research organizations;
- professionally edited industry analysis.

Typical claim suitability:

- comparative context;
- secondary analysis;
- market explanations;
- contextual background when primary material is unavailable or insufficiently accessible.

Class C should not silently override a directly applicable Class A source for contractual, regulatory, or product-specific facts.

### Class D — Community / User-Generated / Informal

The source is based primarily on individual experiences, community discussion, informal commentary, or other user-generated material.

Typical examples:

- forums;
- social communities;
- user reviews;
- informal discussion threads.

Typical claim suitability:

- identifying reader questions;
- surfacing possible experiences or issues for further research;
- discovery of topics requiring verification.

Class D is not sufficient by itself for high-stakes factual claims about legal requirements, policy terms, coverage, pricing, or regulatory obligations.

### Class E — Discovery / Search-Derived Surface

The source is a search-result surface or discovery artifact rather than a reviewed source page.

Typical examples:

- SERP result titles;
- SERP snippets;
- search-result distributions;
- search ranking observations.

Typical claim suitability:

- search landscape;
- topic/entity discovery;
- query intent and SERP analysis;
- identifying candidate source pages.

Class E is not treated as equivalent to the underlying source page.

## Source-Suitability Matrix

Authority is claim-dependent.

| Claim family | Preferred source class | Supporting classes | Classes not sufficient alone |
| --- | --- | --- | --- |
| Regulation / legal requirement | A | B, selected C | D, E |
| Official program / eligibility rule | A | B, selected C | D, E |
| Insurer's own policy / plan term | A | B, selected C | D, E |
| General professional guidance | B | A, C | D, E |
| General educational fact | A, B | C | D, E |
| Market comparison | C | A, B | D, E |
| Product/provider comparison | A for each provider-specific fact; C for comparative synthesis | B | D, E |
| Reader questions / topic discovery | E, D | C | — |
| User experience / anecdotal concern | D | C | D is inherently anecdotal and must not be presented as a general fact |
| Search intent / SERP behavior | E | C | — |

The matrix is a suitability policy, not a universal winner/loser ranking.

## First-Party Rule

First-party evidence is authoritative for claims about the first party's own offering when the source actually contains the relevant information.

For example:

```text
insurer official policy document
        ↓
that insurer's plan term
        ↓
appropriate first-party authority
```

This does not mean:

```text
insurer official page
        ↓
authoritative for every claim about the entire insurance market
```

The claim must remain within the source's actual scope.

## Regulatory / Legal Rule

Claims about law, regulation, mandatory requirements, or regulator policy should prefer the applicable official source.

A secondary article may provide context but must not silently replace the primary regulatory source when the primary source is available and material to the claim.

When the official source cannot be established, the authority result must not be upgraded by assumption.

## Product-Specific Rule

For plan-specific claims, the best authority is the provider's own applicable documentation for that exact plan, product, jurisdiction, or contract version.

Generic provider marketing pages may be less specific than policy/benefit documentation.

Authority evaluation therefore considers not only source class but also scope match.

## Scope Match

A source can fail authority despite belonging to a strong class if the source does not cover the claim being asserted.

Authority should consider:

- subject match;
- jurisdiction match where applicable;
- product/plan match where applicable;
- temporal/version match where material;
- claim-specific scope.

This prevents a strong source from being treated as evidence for an unrelated claim.

## Source Identity Requirements

F consumes the canonical source identity.

At minimum, the authority evaluator should be able to identify:

- source type;
- source ID / locator;
- provider;
- retrieval time.

Where an explicit source URL, publication metadata, or source classification becomes necessary, those additions belong to the formal source schema work in H.

F must not silently manufacture missing source identity.

## Authority Evaluation States

F may evaluate source authority using explicit states:

### PASS

The source is appropriate and sufficiently authoritative for the claim under the applicable authority policy.

### FAIL

The source is explicitly unsuitable or materially inadequate for the claim under the policy.

### UNKNOWN

Authority cannot be established because required source classification, scope, or policy context is missing.

UNKNOWN must not become PASS by default.

## Authority Is Not a Score

The model deliberately avoids a universal numeric authority score in the F-stage contract.

A number such as:

```text
authority = 0.87
```

does not explain whether the source is appropriate for:

- a regulation;
- a plan term;
- a general educational statement;
- a market comparison.

Later implementation may retain domain-specific scores already present in research artifacts, but such scores do not automatically establish source authority for a claim.

Existing Evidence such as:

- `authority.authority_score`;
- `authority.topic_fit`;

remains Evidence about the analyzed research landscape.

It is not automatically a Source Authority classification.

## Authority vs Evidence Confidence

These are independent.

```text
high Evidence confidence
        ≠
high source authority
```

An analyzer can be highly confident that a low-authority community statement exists.

Likewise, a highly authoritative source can have incomplete or ambiguously extracted Evidence.

F must therefore evaluate authority separately from `confidence`.

## Authority vs Provenance

These are also independent.

```text
provenance.analyzer = trusted_analyzer
        ≠
source is authoritative
```

Provenance tells us how the system produced the Evidence.

It does not upgrade the underlying source.

## Authority vs Freshness

A source may be highly authoritative but stale.

```text
authority
   ≠
freshness
```

Freshness remains the C/G concern.

F may require a current source for a claim when the applicable authority policy explicitly makes recency part of source suitability, but it does not replace the Freshness dimension.

## Authority vs Diversity

Several highly authoritative Evidence records can still derive from the same underlying source.

```text
authority
   ≠
source diversity
```

Diversity remains governed by G.

## Authority and Search Results

Search-result position, ranking, or appearance on a SERP does not constitute source authority.

```text
SERP position
   ≠
authority
```

A high-ranking result may point to an authoritative source, but the authority judgment belongs to the underlying source and claim scope.

## Authority and Community Sources

Community sources are useful for discovering questions, concerns, and potential user experiences.

They should not be silently converted into general factual assertions.

Where a community source surfaces a substantive issue:

```text
community signal
      ↓
candidate research question
      ↓
authoritative verification
      ↓
reader-facing factual claim
```

This protects both the Evidence boundary and the editorial claim boundary.

## F Output Concept

Before H defines formal schema changes, the conceptual Source Authority result is:

```text
source_id
source_class
authority_state
scope_match
claim_context
reason_codes
policy_version
audit
```

Where:

- `source_id` identifies the evaluated source;
- `source_class` identifies the applicable authority class;
- `authority_state` is PASS / FAIL / UNKNOWN;
- `scope_match` records whether the source actually covers the claim context;
- `claim_context` identifies the type of claim being evaluated;
- `reason_codes` explain the result;
- `policy_version` identifies the authority policy;
- `audit` records evaluation method/version.

This is a conceptual contract only. Formal fields belong to H.

## Recommended Reason Codes

| Code | Meaning |
| --- | --- |
| `source_identity_missing` | Source identity cannot be established |
| `source_class_unknown` | Authority class cannot be established |
| `claim_scope_mismatch` | Source does not cover the asserted claim scope |
| `jurisdiction_mismatch` | Source jurisdiction does not match the claim |
| `product_scope_mismatch` | Source does not match the relevant product/plan |
| `primary_source_preferred` | A primary/official source is required or materially preferred |
| `secondary_only` | Current support is secondary for a claim needing stronger authority |
| `community_only` | Support is based only on community/user-generated material |
| `search_surface_only` | Support comes only from a search-result surface |
| `authority_policy_missing` | Applicable policy is not available |
| `authority_unknown` | Available information is insufficient to classify authority safely |

Reason codes are explanations, not scoring components.

## Integration With Section Readiness

E consumes the Authority result.

Examples:

```text
required regulatory claim
      ↓
only Class D/E support
      ↓
authority FAIL
      ↓
section cannot become READY
```

And:

```text
provider-specific plan claim
      ↓
matching provider documentation
      ↓
Class A + scope match
      ↓
authority PASS
```

The final section state remains owned by E.

## Handling Missing Authority Inputs

When authority cannot be evaluated:

- do not invent a source class;
- do not infer authority from provider name alone;
- do not convert Evidence confidence into authority;
- do not treat SERP rank as authority;
- do not silently assume that legacy source metadata is sufficient.

The result is UNKNOWN until the missing information is supplied or an explicit policy determines that authority is not required for the claim.

## Legacy Source Metadata

Current repository Evidence artifacts include legacy source/provenance structures in addition to the current canonical target.

F must not silently treat legacy metadata as a successful canonical authority classification.

Migration to the formal Source model is separate from F.

Where the source class cannot be established from actual source information, authority remains UNKNOWN or FAIL according to the applicable claim requirement.

## Current Repository Boundary

The current `shared/schemas/source.schema.json` is intentionally minimal and does not yet define a formal Source object.

Therefore F defines the authority semantics now, while H will introduce only the minimum formal source fields necessary to encode those semantics.

This prevents F from prematurely expanding the canonical schema.

## No New Evidence Identity

Authority classification does not create a second Evidence item.

The same Evidence record remains the factual unit.

The authority evaluation is metadata/policy about the underlying source and claim context.

No new production-lineage identifier is introduced.

## F-Stage Invariants

1. Authority is evaluated relative to a claim and context.
2. Source metadata remains distinct from provenance.
3. Evidence confidence remains distinct from source authority.
4. Search-result position is never treated as source authority.
5. Provider identity alone does not establish universal authority.
6. A strong source class does not compensate for scope mismatch.
7. Regulatory/legal claims prefer applicable official primary sources.
8. Provider-specific product claims prefer matching first-party documentation.
9. Community/user-generated material is discovery/support context, not automatic high-authority factual support.
10. Authority is not a universal numeric score.
11. Authority does not replace Freshness or Diversity.
12. UNKNOWN never silently becomes PASS.
13. Missing source identity is not repaired by inference.
14. F does not modify the canonical Evidence object model.
15. Formal source schema changes are deferred to H.
16. Protected production fixtures and secret environment files remain outside the F-stage scope.

## Definition of F Completion

F is complete when the repository has an explicit Source Authority Model that:

- distinguishes source metadata from provenance;
- defines claim-relative authority classes;
- provides a source-suitability matrix;
- defines PASS / FAIL / UNKNOWN semantics;
- defines scope matching;
- separates authority from confidence, freshness, and diversity;
- handles primary, institutional, secondary, community, and search-surface sources;
- provides explainable reason codes;
- defines the hand-off to Section Readiness;
- avoids a universal opaque authority score;
- leaves formal Source schema changes to H.

The next production step is G — Evidence Depth & Diversity Rules.
