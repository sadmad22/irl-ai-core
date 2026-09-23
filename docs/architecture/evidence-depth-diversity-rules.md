# Evidence Depth & Diversity Rules

Version: 1.0

## Purpose

This document defines the operational rules for evaluating Evidence Depth and Source Diversity before Section Evidence Readiness and Article Generation.

It implements G in the production Evidence Quality & Section Readiness Work Plan:

- distinguish surface signals from substantive factual Evidence;
- distinguish multiple Evidence records from multiple independent sources.

G builds on B — Evidence Quality Contract, C — Quality Dimensions, D — Expected Claim Map, E — Section Evidence Readiness, and F — Source Authority Model.

G does not replace the canonical Evidence Contract, change the Evidence identity model, create publication decisions, or introduce a composite quality score.

## Architectural Position

Research Sources → Canonical Evidence → B Quality Contract → C Dimensions → D Expected Claim Map → G Depth & Diversity → E Section Readiness → Article Writer → Claim Grounding / Audit

## Part I — Evidence Depth

### 1. Depth Principle

Depth asks whether an Evidence record contains enough factual substance to support the intended claim without requiring the Writer to invent missing facts.

Depth is not Evidence count, character count, paragraph count, confidence, authority score, SERP position, or lexical overlap.

### 2. Depth Classes

#### D0 — Surface Signal

Research information useful for discovery, prioritization, framing, or analysis but not sufficient by itself for a substantive reader-facing factual claim.

Typical examples:

- query intent;
- SERP position or distribution;
- search volume or CPC;
- commercial-value signals;
- entity presence;
- authority score;
- question frequency.

D0 may be valid canonical Evidence. D0 does not satisfy a substantive claim requirement by itself.

#### D1 — Contextual Evidence

Meaningful topic context that can support framing or explanation but does not contain enough specific factual substance for the required claim on its own.

Examples include broad scope observations, topic classifications, contextual market observations, and question themes.

#### D2 — Substantive Evidence

Specific factual material that can directly support a meaningful claim in the intended section without inventing unrecorded facts.

Typical characteristics:

- identifiable subject;
- specific claim;
- concrete value;
- understandable scope;
- reader-facing factual meaning preserved;
- traceability retained under B.

D2 is the minimum depth class eligible to satisfy a substantive claim family, subject to Relevance, Authority, Freshness, Diversity, and Lineage requirements.

### 3. D2 Qualification

An Evidence record is D2 only when:

1. the claim identifies what is actually being asserted;
2. the value contains substantive factual content;
3. subject and scope are identifiable;
4. the record supports a factual statement without inventing facts;
5. the record is relevant to the evaluated claim or section;
6. the Evidence remains traceable under the B contract.

D2 does not imply source authority, freshness, or source diversity.

### 4. Prohibited Signal Promotion

The following transformations are invalid unless additional substantive Evidence exists:

intent signal → factual product claim
entity presence → product capability
search volume → price claim
CPC → premium claim
commercial value → coverage claim
authority score → source-authority claim
question frequency → answer claim
SERP position → quality claim

A signal can identify a research need. It cannot be promoted into substantive Evidence by wording alone.

### 5. Claim-Relative Depth

Depth is evaluated against the intended claim context.

A provider appearing in a SERP may be D0 for plan coverage, while a verified source-page statement about a specific plan benefit may be D2 for that provider-specific coverage claim.

Therefore one Evidence record does not have a universal depth meaning independent of claim context.

### 6. Derived Evidence Depth

Derived Evidence is not automatically deeper than its parents.

A derived intent classification, ranking distribution, or authority score remains signal-level when used for substantive insurance facts.

Lineage proves derivation. It does not promote a signal into substantive factual support.

### 7. Editorial Source Evidence

Editorial Source Evidence is not automatically deep because an editorial artifact exists.

A title or discovery snippet is not sufficient substantive support by itself.

A verified source-page factual excerpt may qualify as D2 when its scope and verification state support the intended claim and the editorial source contract is satisfied.

### 8. Writer Safety

When an essential substantive claim lacks D2 support, the system must not instruct the Writer to fill the gap from general model knowledge.

The resulting section must remain non-ready under E until adequate Evidence exists.

## Part II — Source Diversity

### 9. Diversity Principle

Diversity asks whether the supporting Evidence represents materially independent underlying source origins.

Diversity is not Evidence count, claim count, number of analyzers, number of fields, or number of Evidence IDs.

### 10. Source Identity Resolution

Diversity uses the strongest available identity in this order:

1. canonical source identity using source.source_id, source.type, and source.provider;
2. explicit stable source locator such as URL or document identifier;
3. known artifact identity for legacy research records;
4. upstream lineage roots for derived Evidence.

When an exact independent source origin cannot be established, the evaluator must remain conservative.

### 11. Source Instance vs Source Family

A source instance is a concrete page, document, dataset, or equivalent source origin.

A source family is a broader origin such as an organization, provider, or publisher.

The evaluator should retain both where possible.

Multiple pages from one publisher are not automatically equivalent to multiple independent organizations.

### 12. Independence Rule

Two Evidence records are independent only when their underlying source origins are materially independent for the claim under evaluation.

The following do not establish independence by themselves:

- different Evidence IDs;
- different claim attributes;
- different analyzers;
- different timestamps for the same artifact;
- derivation from different intermediate records with the same root;
- different fields extracted from one source.

### 13. Derived Evidence Diversity

Derived Evidence does not create a new independent source.

If Source A produces A1, A2, A3 and derived A4, the source representation remains one source family unless an independent root contributes materially.

When a derived record combines independent roots, the evaluator must preserve the root set rather than counting the derived record as a new source.

### 14. Artifact Deduplication

Evidence records tied to the same underlying artifact must be grouped before diversity is assessed.

Current repository examples:

- the four Business Evidence records share search-metrics.json;
- the Entity Evidence records share serp-analysis.json.

These are multiple Evidence records, not multiple independent source artifacts.

Protected production fixtures must remain unchanged.

### 15. Legacy Metadata

Legacy source fields such as source.type, source.project, and source.artifact may reveal that records share one artifact.

They must not be used to invent a stronger independent-source identity.

When independence cannot be established, diversity is UNKNOWN rather than optimistically PASS.

### 16. Diversity States

PASS: the evaluated set demonstrates the required source independence under the active policy.

FAIL: the set is materially repetitive or lacks the independent representation required by the active policy.

UNKNOWN: source identity or lineage is insufficient to establish independence safely.

UNKNOWN must never silently become PASS.

### 17. No Universal Diversity Count

G does not define a universal rule such as two sources equals diverse.

Required diversity depends on claim type, section, claim risk, Authority policy, and the active Section Readiness policy.

## Part III — Interaction With Other Dimensions

### 18. Depth vs Authority

D2 does not imply authoritative sourcing.

An authoritative source can still provide shallow or incomplete Evidence.

### 19. Depth vs Freshness

D2 does not imply current information.

Freshness remains a separate temporal dimension.

### 20. Diversity vs Authority

Multiple authoritative records can still derive from one source.

Multiple low-authority sources do not become strong merely because they are diverse.

### 21. Diversity vs Depth

D0 + D0 + D0 does not become D2.

One D2 record does not become multiple independent sources.

### 22. Coverage

The Expected Claim Map from D determines which claim families are required.

G determines whether Evidence supporting those families is substantive enough and, where applicable, sufficiently independent.

E remains responsible for the final READY / INSUFFICIENT / BLOCKED decision.

## Part IV — Section-Level Rules

### 23. Required Substantive Claims

For a required substantive claim family, minimum depth is D2 unless a later explicit policy defines a stricter requirement.

D0 signals and D1 contextual material cannot replace required D2 support.

### 24. Supporting Claims

Supporting claims may use D1 or D2 according to section policy, but they never replace missing required claim families.

### 25. Discovery Signals

D0 evidence may remain useful for research planning and cannot be discarded merely because it is shallow.

It is simply not counted as substantive support for a claim that requires factual depth.

### 26. Comparative Claims

Where a comparison depends on more than one source origin, source independence must be evaluated rather than inferred from multiple Evidence IDs.

Provider-specific claims should retain provider-specific source scope.

### 27. FAQ Claims

question_frequency.count is discovery/context Evidence.

It does not itself provide answer depth.

A substantive FAQ answer requires supporting factual Evidence appropriate to the answer claim.

### 28. Cost Claims

Business and SEO signals are not pricing Evidence.

Affiliate potential, commercial value, CPC, search volume, and conversion signals cannot satisfy a substantive premium or cost-driver claim.

## Part V — Evaluation Outputs

### 29. Conceptual Depth Result

Before H formalizes schemas, the conceptual result is:

evidence_id
depth_class
substantive_support
claim_context
reason_codes
policy_version
audit

depth_class is D0, D1, or D2.

### 30. Conceptual Diversity Result

Before H formalizes schemas, the conceptual result is:

section_or_claim_context
source_instances
source_families
independent_root_sources
diversity_state
reason_codes
policy_version
audit

The output must preserve enough grouping information to explain why records were treated as one source or several independent sources.

### 31. Reason Codes

Depth reason codes:

- surface_signal;
- contextual_only;
- substantive_support;
- scope_incomplete;
- value_non_substantive;
- depth_unknown.

Diversity reason codes:

- same_evidence_id;
- same_source_origin;
- same_artifact;
- derived_same_root;
- independent_source;
- independence_unknown;
- diversity_insufficient;
- diversity_unknown.

Reason codes are explanations, not numerical penalties.

## Part VI — Safety Rules

### 32. No Depth Inflation

The system must not inflate depth by concatenating signal records, counting characters, averaging confidence, averaging authority scores, converting search metrics to factual prose, or treating Writer output as Evidence.

### 33. No Diversity Inflation

The system must not inflate diversity by splitting one artifact into many records, assigning new Evidence IDs, using multiple analyzers on one source, treating derived Evidence as a new source, or using different timestamps as independence.

### 34. Lineage Preservation

Depth and Diversity evaluation must preserve evidence_id, source identity, provenance, derived_from, and report lineage.

No evaluator may replace a source root with an inferred or fabricated parent.

### 35. Fail-Closed

The following prevent a positive Depth or Diversity conclusion when the missing information is essential:

- missing required source identity;
- broken lineage needed to identify roots;
- malformed Evidence needed for the claim;
- inability to distinguish potentially shared source origins.

If the issue is inability to evaluate rather than a proven failure, the dimension is UNKNOWN.

E decides whether UNKNOWN becomes INSUFFICIENT or BLOCKED.

## Part VII — Current Repository Compatibility

The current repository contains both canonical-looking records and legacy source/provenance shapes.

G therefore uses conservative classification and does not repair or rewrite transitional Evidence artifacts.

The Business Evidence example demonstrates repeated records from one artifact.

The Entity Evidence example demonstrates many records from one artifact.

These cases are intentionally preserved as evidence of the need for grouping rather than modified to manufacture diversity.

## G-Stage Invariants

1. D0 signals do not satisfy substantive D2 requirements.
2. D1 contextual Evidence is not automatically substantive.
3. D2 is claim-relative and requires substantive factual support.
4. Multiple shallow records do not become deep Evidence.
5. Evidence count does not measure Depth.
6. Different Evidence IDs do not establish Diversity.
7. Same artifact does not establish source independence.
8. Derived Evidence does not automatically create a new source.
9. Independent upstream roots must remain traceable.
10. Authority, Freshness, Depth, and Diversity remain distinct dimensions.
11. UNKNOWN never silently becomes PASS.
12. Missing source identity is not invented.
13. Legacy metadata is not silently upgraded into stronger source identity.
14. No composite quality score is introduced.
15. G does not modify the canonical Evidence object model.
16. Protected fixtures and secret environment files remain untouched.

## Definition of G Completion

G is complete when the repository defines an operational and explainable policy for:

- D0/D1/D2 depth classification;
- claim-relative substantive support;
- prohibition of signal-to-fact promotion;
- source-origin grouping;
- source instance vs source family distinction;
- derived-root handling;
- repeated-artifact detection;
- PASS / FAIL / UNKNOWN diversity semantics;
- lineage preservation;
- conservative legacy-data treatment;
- separation from Authority, Freshness, and Evidence confidence;
- no composite score;
- explicit hand-off to Section Evidence Readiness.

The next production step is H — Schema.