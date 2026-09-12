# Final Optimization Artifact v1 — Contract, Boundary & Invariants

## 1. Purpose

The Final Optimization Artifact v1 is the canonical production artifact for the `optimization` stage.

Its single responsibility is:

> Produce and bind the final SEO delivery values required by downstream production assembly from explicitly supplied upstream inputs, with deterministic identity, explicit lineage, truthful lifecycle state, and no downstream regeneration.

The Final Optimization Artifact is a production decision artifact. It is not a content-generation, validation, recovery, discovery, linking, media, taxonomy, platform, or publication component.

## 2. Canonical identity

The canonical artifact name is:

```text
Final Optimization Artifact v1
```

The canonical identifier is:

```text
optimization_id
```

The canonical lifecycle stage is:

```text
optimization_ready
```

The artifact must carry its contract and method versions explicitly.

Required root fields:

```text
optimization_id
schema_version
method_version
lifecycle_stage
seo_title
meta_description
primary_keyword
slug
lineage
```

Optional root fields:

```text
canonical_url
source_refs
audit
```

## 3. Boundary

```text
Explicit Upstream Inputs
        |
        v
+--------------------------------+
| Final Optimization Artifact v1 |
|                                |
| bind final SEO values          |
| validate required values       |
| bind lineage                   |
| enforce lifecycle truth        |
| produce deterministic identity |
+--------------------------------+
        |
        v
optimization_ready
        |
        v
SEO Validation / QA / Assembly
```

The artifact is the authoritative source for final SEO delivery values consumed by downstream production stages.

Downstream stages may validate and bind these values, but must not regenerate, infer, score, rewrite, or replace them.

## 4. Required final values

The artifact must provide the following final values:

| Field | Requirement | Role |
|---|---|---|
| `seo_title` | required, non-empty | authoritative final SEO title |
| `meta_description` | required, non-empty | authoritative final meta description |
| `primary_keyword` | required, non-empty | authoritative primary keyword |
| `slug` | required, non-empty | authoritative final slug |
| `canonical_url` | optional | authoritative canonical URL when explicitly supplied |

A required value is not valid merely because a related upstream artifact exists.

The actual value must be explicitly present in the Final Optimization Artifact or in the explicit upstream input used to construct it.

## 5. Lineage contract

The minimum required lineage is:

```text
report_id
decision_id
strategy_id
brief_id
```

Lineage identifies the actual upstream production artifacts from which the final optimization decision is produced or bound.

Rules:

1. Every required lineage ID must be present.
2. Each lineage ID must identify the corresponding actual upstream artifact.
3. Conflicting lineage must fail.
4. Missing lineage must fail.
5. Lineage must never be fabricated to satisfy validation.
6. One artifact must not silently substitute another artifact's lineage.
7. Optional lineage extensions may be present only when they correspond to actual supplied artifacts.

The Final Optimization Artifact must not silently merge lineage from unrelated production runs.

## 6. Responsibilities

The Final Optimization Artifact stage has exactly these responsibilities:

1. Produce or bind the final SEO title.
2. Produce or bind the final meta description.
3. Produce or bind the final primary keyword.
4. Produce or bind the final slug.
5. Bind an explicitly supplied canonical URL when applicable.
6. Bind required upstream lineage.
7. Declare `optimization_ready` only when its contract is satisfied.
8. Produce deterministic artifact identity and output for identical canonical inputs.
9. Preserve explicit source references and audit information when supplied.

The stage may perform deterministic normalization required by the contract, but normalization must not change the semantic decision represented by the supplied final values.

## 7. Explicit non-responsibilities

The Final Optimization Artifact stage MUST NOT:

- rewrite or generate the article body;
- rewrite or generate article sections;
- create, modify, or ground claims;
- create or modify tables;
- discover or replace internal links;
- discover or replace external links;
- generate or materialize images;
- select or resolve WordPress media IDs;
- infer or assign WordPress taxonomy IDs;
- publish content;
- authorize publication;
- call WordPress APIs;
- perform WordPress authentication;
- assemble the Article Package;
- act as the SEO validator;
- act as the SEO recovery executor;
- silently repair missing upstream production artifacts;
- use `seo_validation` as a substitute for a final optimization artifact;
- use article prose as an implicit source for missing required final values;
- introduce network, web-search, DataForSEO, or other external discovery as a hidden fallback;
- fabricate defaults for required values.

## 8. Separation from Content Optimization

`Content Optimization` and `Final Optimization` are separate production concepts.

Content Optimization may analyze keyword, semantic, topic, heading, coverage, entity, and question gaps and may provide recommendations.

Final Optimization is the canonical production artifact containing the final SEO delivery values.

Therefore:

```text
Content Optimization
        |
        | analysis / recommendations
        v
Final Optimization
        |
        | final authoritative values
        v
SEO Validation / QA / Assembly
```

The existing Content Optimization artifact must not be renamed, repurposed, or treated as the Final Optimization Artifact solely to avoid creating the new contract.

## 9. Separation from SEO Validation

SEO Validation is a validator, not the final optimization producer.

The following shortcut is invalid:

```text
seo_validation exists
        -> optimization artifact exists
```

A validation result may validate final optimization values, but it cannot become the canonical optimization artifact.

The production pipeline must preserve the distinction:

```text
optimization -> produces final SEO values
seo_validation -> validates SEO state
```

## 10. Separation from SEO Recovery

The SEO recovery executor remains a bounded recovery mechanism.

Recovery may revise only the fields explicitly permitted by its own contract.

Recovery execution does not redefine the Final Optimization Artifact contract and does not turn recovery state into a substitute for the canonical optimization artifact.

The Final Optimization Artifact remains the authoritative downstream source after the production optimization decision has been established.

## 11. Downstream consumption boundary

Downstream production stages consume the Final Optimization Artifact as an explicit artifact.

### SEO Validation

May:

- validate final SEO values;
- report SEO validation state;
- retain references to `optimization_id`.

Must not:

- replace final optimization values;
- create a different canonical optimization artifact.

### Quality / QA

May:

- validate the optimization artifact as part of production quality gates;
- retain its identity and lineage.

Must not:

- regenerate final SEO values.

### Article Package Assembly

May:

- consume the Final Optimization Artifact;
- validate required final values;
- bind those values into the canonical Article Package;
- preserve `optimization_id` lineage.

Must not:

- generate, score, rewrite, infer, or replace SEO values;
- reconstruct missing values from article prose;
- substitute `seo_validation` for the optimization artifact.

## 12. Lifecycle

The canonical lifecycle state for a valid Final Optimization Artifact is:

```text
optimization_ready
```

The artifact must not claim `optimization_ready` unless all required fields, required lineage, and contract invariants pass validation.

The artifact must not claim downstream states such as:

```text
package_assembled
package_validated
delivery_ready
delivered_as_draft
human_review
```

Those states belong to later production boundaries.

Lifecycle truthfulness rule:

> An artifact may claim only the stage represented by its own contract and completed responsibilities.

## 13. Production intent boundary

The Final Optimization Artifact does not authorize publication.

It must not introduce or mutate publication intent.

The production path remains governed by the canonical controlled-production intent:

```text
{
  "target": "wordpress",
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

Optimization must not set `publish=true`, bypass human approval, or encode platform transport behavior.

## 14. Determinism

For the same canonical inputs, contract version, and method version, the Final Optimization Artifact must produce the same artifact content and deterministic `optimization_id`.

The artifact must not depend on:

- current time for identity;
- random IDs;
- unordered filesystem discovery;
- mutable external search results;
- WordPress state;
- publication state;
- downstream package state.

If external research or an optimization engine is used upstream to determine final values, the resulting Final Optimization Artifact must still expose the final values and explicit lineage required by this contract.

## 15. Input discipline

The implementation must accept explicit structured inputs rather than an unrestricted project directory.

Required logical upstream context:

```text
report
 decision
 strategy
 brief
```

The exact transport representation is an implementation concern, but the contract requires the corresponding identities to be explicitly available for lineage binding.

If a required final value cannot be produced from an explicit contracted upstream input, the pipeline must stop and classify the missing producer or boundary.

It must not add hidden discovery, inference, article parsing, or generation to compensate.

## 16. Validation rules

The Final Optimization Artifact is invalid when any of the following occurs:

- `optimization_id` is missing or invalid;
- `schema_version` is missing;
- `method_version` is missing;
- `lifecycle_stage` is missing or not `optimization_ready`;
- `seo_title` is missing or empty;
- `meta_description` is missing or empty;
- `primary_keyword` is missing or empty;
- `slug` is missing or empty;
- required lineage is missing;
- lineage conflicts with supplied upstream artifacts;
- a required value is inferred rather than explicitly supplied or deterministically produced by the contracted optimization stage;
- unsupported downstream fields are inserted into the artifact;
- publication authorization is introduced;
- platform-specific transport data is introduced;
- placeholder or fabricated values are used.

Invalid artifacts must fail closed.

## 17. Fail-closed rules

The stage must fail rather than silently repair any of the following:

- missing required final SEO value;
- missing required lineage;
- conflicting lineage;
- invalid lifecycle claim;
- malformed structured input;
- unsupported field mutation;
- fabricated default;
- hidden fallback to `seo_validation`;
- hidden fallback to article prose;
- hidden external discovery;
- publication intent mutation.

No best-effort artifact marked `optimization_ready` is valid.

## 18. Boundary protection

The Final Optimization Artifact must remain narrow.

It must not become a second Article Package Engine or a general production orchestrator.

The following domains remain outside this artifact:

```text
Article content
Claims / evidence
Editorial state
Media
Internal links
External links
Taxonomy
Article Package assembly
Production Delivery Boundary
WordPress adapter
Publication
```

If a future requirement needs one of these domains, it must be handled by its own explicit producer or contract rather than being added to Final Optimization v1.

## 19. Artifact identity and traceability

Every valid artifact must be traceable through:

```text
optimization_id
    |
    +-- report_id
    +-- decision_id
    +-- strategy_id
    +-- brief_id
```

Downstream consumers must preserve `optimization_id` when binding final optimization into later production artifacts.

Traceability must survive:

```text
Final Optimization
        -> SEO Validation
        -> QA
        -> Article Package
        -> Production Delivery Boundary
        -> WordPress Adapter
```

The Final Optimization Artifact must never be detached from its production lineage during downstream normalization.

## 20. Contract acceptance criteria

Final Optimization Artifact v1 is contract-complete only when all are true:

- one canonical human-readable contract exists at `shared/models/final-optimization.md`;
- `optimization_id` is the canonical artifact identity;
- `optimization_ready` is the canonical lifecycle state;
- required final SEO values are explicit and non-empty;
- required lineage is explicit and internally consistent;
- Content Optimization remains a separate artifact;
- SEO Validation remains a validator;
- SEO Recovery remains a recovery mechanism;
- Article Package Assembly consumes rather than regenerates final optimization values;
- missing values fail closed rather than triggering hidden discovery or inference;
- publication remains `publish=false` with human approval required;
- the artifact remains platform-neutral;
- downstream traceability is preserved.

## 21. Implementation rule

Do not expand Final Optimization Artifact v1 while implementing it.

If a required value, lineage element, or behavior is not explicitly defined by this contract, stop and classify the missing contract or producer rather than silently adding functionality.
