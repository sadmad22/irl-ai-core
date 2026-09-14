# O7 ↔ G-01 ↔ G-02 Reconciliation Contract v1

## Status

**Contract phase — implementation is not authorized by this document.**

This contract closes the identified integration-proof gap between O7 Controlled Production, G-01 Final Optimization, G-02 lineage binding, and the current canonical Production Orchestrator.

The purpose is to define the exact cross-layer invariants that must be proven by integration tests before the project can claim complete O7/G-01/G-02 integration verification.

No production implementation change is authorized by this contract.

## 1. Baseline

Verified baseline:

```text
main @ cb0d15101ec5179244fc5d00fe8a10f16a07812e
```

The baseline already contains the verified G-01 and G-02 work and the current O7 Controlled Production contract/tests.

## 2. Objective

Prove, with explicit integration evidence, that:

```text
Final Optimization (G-01)
        ↓
Production Orchestrator
        ↓
Production Assembly (G-02 binding)
        ↓
Article Package (G-02 preservation)
        ↓
Production Delivery Boundary
        ↓
WordPress Adapter
        ↓
O7 Controlled Production state
```

preserves canonical identity, lineage, production intent, checkpoint semantics, fail-closed behavior, and human-review control.

The integration proof MUST exercise the existing canonical engines rather than reproduce their logic inside the tests.

## 3. Canonical Production Pipeline

The Orchestrator MUST retain exactly these 14 stages, in this order:

```text
research
intelligence
configuration
structure
draft
editorial_cleanup
media
linking
optimization
qa
production_assembly
article_package
production_delivery_boundary
wordpress_delivery
```

`human_review` is a Controlled Production terminal control state and is NOT an additional Orchestrator production stage.

The reconciliation work MUST NOT add, remove, reorder, or rename a production stage.

## 4. G-01 Canonical Optimization Invariant

Final Optimization is the sole canonical optimization artifact for the production chain.

The integration path MUST consume the Final Optimization artifact produced by G-01.

The following substitution is prohibited:

```text
seo_validation → optimization
```

No article draft prose, quality artifact, SEO validation artifact, generated value, or inferred value may replace a required Final Optimization value.

The integration proof MUST demonstrate that the canonical optimization artifact reaches the production assembly path without semantic substitution.

## 5. Canonical Production Lineage

The canonical six-identifier production lineage is exactly:

```text
report_id
  ↓
decision_id
  ↓
strategy_id
  ↓
brief_id
  ↓
draft_id
  ↓
quality_id
```

G-01 Final Optimization owns and carries the first four identifiers:

```text
report_id
 decision_id
 strategy_id
 brief_id
```

`optimization_id` identifies the Final Optimization artifact. It is an artifact identity and MUST NOT replace any production lineage identifier.

## 6. G-02 Cross-Binding Invariants

### 6.1 Final Optimization → Assembly

When the canonical Final Optimization artifact reaches Production Assembly:

1. `optimization.lineage.report_id` MUST equal Assembly `report_id`.
2. `optimization.lineage.decision_id` MUST equal Assembly `decision_id`.
3. `optimization.lineage.strategy_id` MUST equal Assembly `strategy_id`.
4. `optimization.lineage.brief_id` MUST equal Assembly `brief_id`.
5. `optimization.optimization_id` MUST remain intact.
6. Assembly MUST validate and bind these values; it MUST NOT derive, rewrite, or silently replace them.
7. Missing or conflicting values MUST fail closed with deterministic lineage classification.

### 6.2 Assembly → Package

When Article Package is built from Assembly:

1. All six canonical production lineage identifiers MUST remain unchanged.
2. `optimization_id` MUST remain traceable at package lineage level.
3. Package optimization SEO values MUST remain sourced from the canonical Final Optimization artifact.
4. Package MUST NOT reconstruct or substitute Final Optimization lineage.
5. Missing or conflicting `optimization_id`, where contractually required, MUST fail closed.

The Package `optimization` object is a contracted projection of delivery SEO fields. It is not a second optimization producer.

## 7. O7 Production Checkpoint Invariants

O7 Controlled Production MUST preserve the canonical checkpoint chain:

```text
assembly_id
    ↓
package_id
    ↓
delivery_id
```

The O7 production state MUST retain `orchestration_id` and these checkpoint identities without silent replacement.

A production run MUST NOT become delivery-ready unless the required canonical checkpoints are valid and present.

A delivered run MUST have a valid delivery checkpoint and the corresponding controlled delivery state.

## 8. O7 Production Intent Invariants

The immutable production intent is:

```json
{
  "target": "wordpress",
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

The integration path MUST preserve these values.

The following are prohibited:

- `publish=true`;
- a non-draft WordPress publication mode;
- bypassing human approval;
- treating `human_review` as an automatic publication step.

## 9. Controlled Production State Invariants

The successful controlled delivery path MUST resolve to:

```text
human_review
```

with:

```text
human_review.required = true
human_review.status = pending
publication.mode = wordpress_draft
publication.publish = false
publication.human_approval_required = true
delivery.remote_status = draft
```

Human approval/rejection remains a terminal control action after the draft has been delivered.

## 10. Dry-Run Invariants

The O7 dry-run integration path MUST:

1. execute the canonical production preparation path;
2. validate the required production checkpoints;
3. preserve G-01/G-02 identity and lineage;
4. reach `ready_for_delivery` when the controlled pre-delivery conditions are satisfied;
5. avoid WordPress side effects;
6. produce no remote post ID;
7. preserve draft-only publication intent.

Dry-run MUST NOT be treated as evidence of a successful WordPress API delivery. It proves readiness and controlled boundary behavior only.

## 11. Controlled WordPress Draft Invariants

The controlled live path MUST:

1. use the canonical Production Delivery Boundary;
2. pass the canonical delivery object to the WordPress adapter;
3. create/update only a WordPress draft under the controlled publication intent;
4. preserve `delivery_id`, `package_id`, `assembly_id`, and `orchestration_id` traceability;
5. record the remote draft identity/status when delivery succeeds;
6. resolve the O7 state to `human_review`;
7. never publish automatically.

The integration proof MUST NOT claim publication success merely because draft delivery succeeded.

## 12. Fail-Closed Invariants

The integrated path MUST fail closed for at least these classes:

1. Missing G-01 Final Optimization lineage field.
2. Conflicting `report_id`, `decision_id`, `strategy_id`, or `brief_id` between Final Optimization and Assembly.
3. Conflicting `draft_id` or `quality_id` within the canonical six-ID production lineage.
4. Missing or conflicting `optimization_id` where G-02 requires it.
5. Attempted substitution of `seo_validation` for canonical optimization.
6. Missing required O7 production checkpoint before delivery readiness.
7. Invalid O7 state transition.
8. Orchestration failure.
9. WordPress delivery failure.
10. Any publication intent that violates draft-only/human-approval invariants.

A conflict is an error, not a merge or repair opportunity.

## 13. Determinism

For identical valid upstream artifacts and identical lineage, the integrated O7 production result MUST preserve identical canonical lineage and optimization identity.

For identical conflicting inputs, the integration path MUST produce the same failure classification.

The tests MUST not depend on uncontrolled external discovery, timing-sensitive behavior, or nondeterministic generated identifiers as evidence of lineage correctness.

## 14. Ownership Boundaries

### Final Optimization (G-01)

Owns production of the canonical Final Optimization artifact, its optimization identity, and its four upstream lineage identifiers.

### Production Orchestrator

Owns sequencing and transport of canonical artifacts through the 14-stage production chain. It does not reinterpret lineage, perform HTTP, resolve WordPress taxonomy IDs, upload media, discover links, or generate/rewrite article content.

### Production Assembly

Owns cross-artifact validation and binding of the canonical lineage and canonical optimization projection.

### Article Package

Owns canonical delivery package construction while preserving six-ID production lineage and `optimization_id` traceability.

### Production Delivery Boundary

Owns the delivery-ready contract consumed by the WordPress adapter. It does not invent or rewrite upstream lineage.

### WordPress Adapter

Owns external WordPress delivery mechanics. It consumes the canonical Delivery Boundary output and MUST honor draft-only publication intent.

### O7 Controlled Production

Owns production-run state, checkpoint/state-transition enforcement, controlled delivery status, and human-review gating. It does not become a second content-production engine.

## 15. Prohibited Changes During Reconciliation

The reconciliation implementation MUST NOT:

- add a production stage;
- reorder the canonical 14 stages;
- create a second optimization engine;
- introduce an LLM/provider runtime;
- add external discovery logic;
- move HTTP or credentials into the Orchestrator;
- bypass Assembly, Package, Delivery Boundary, or WordPress adapter ownership;
- introduce auto-publishing;
- permit `publish=true` across the production path;
- modify preserved production artifacts;
- duplicate production logic inside integration tests.

## 16. Required Integration Evidence

Before the gap can be closed, the integration test layer MUST explicitly prove:

| ID | Integration invariant | Expected result |
|---|---|---|
| R-01 | Exact 14-stage Orchestrator order remains canonical | PASS |
| R-02 | Canonical G-01 Final Optimization reaches production path | PASS |
| R-03 | `seo_validation` cannot substitute for optimization | Fail-Closed |
| R-04 | First four G-01 lineage IDs match Assembly lineage | PASS / mismatch fails |
| R-05 | `optimization_id` survives Assembly | PASS |
| R-06 | Six-ID lineage survives Assembly → Package | PASS |
| R-07 | `optimization_id` survives Assembly → Package | PASS |
| R-08 | Package optimization values remain sourced from canonical optimization | PASS |
| R-09 | O7 checkpoint chain assembly → package → delivery is valid | PASS |
| R-10 | O7 preserves orchestration identity | PASS |
| R-11 | Dry-run reaches `ready_for_delivery` without WordPress side effects | PASS |
| R-12 | Controlled WordPress delivery creates draft only | PASS |
| R-13 | Successful controlled delivery resolves to `human_review` | PASS |
| R-14 | `publish=false` and human approval remain enforced end-to-end | PASS |
| R-15 | Lineage conflict fails closed deterministically | Fail-Closed |
| R-16 | Missing checkpoint fails closed | Fail-Closed |
| R-17 | Orchestration failure stops production | Fail-Closed |
| R-18 | WordPress delivery failure stops production | Fail-Closed |
| R-19 | No canonical lineage field disappears at any tested boundary | PASS |
| R-20 | End-to-end O7 → G-01 → G-02 traceability is preserved | PASS |

This matrix defines required evidence for the next phase. It does not authorize implementation until reviewed and approved.

## 17. Acceptance Criteria

The reconciliation gate is PASS only when:

1. Every applicable R-series invariant has an explicit integration test.
2. At least one test exercises the real Orchestrator → Assembly → Package → Delivery Boundary handoff.
3. G-01 `optimization_id` and first-four lineage are preserved into O7 production state.
4. The six-ID production lineage remains unchanged through package/delivery.
5. Dry-run proves readiness without WordPress side effects.
6. Controlled WordPress delivery proves draft-only behavior and `human_review`.
7. Negative cases fail closed deterministically.
8. The existing full regression remains green.
9. No preserved production artifact is modified or staged.
10. No unrelated feature work appears in the final diff.
11. Canonical ownership boundaries remain unchanged.

## 18. Stop Conditions

Stop immediately if:

- any invariant contradicts the current canonical architecture;
- satisfying an invariant requires redesigning an existing engine;
- an integration test must duplicate production logic instead of exercising the canonical engine;
- `publish=true` can cross the production path;
- `human_review` can be bypassed;
- a preserved production artifact becomes modified or staged;
- a provider/runtime implementation becomes necessary to establish the architecture contract rather than merely execute an already-supported boundary.

## 19. Implementation Gate

This contract is the sole Step-2 deliverable.

**No production implementation changes are authorized yet.**

After review and approval, Step 4 may proceed to the Integration Matrix/Test implementation phase described by the Gap Closure Plan.

The next action after approval is to build the focused integration tests for the R-series matrix, beginning with the canonical happy path and then deterministic negative cases.
