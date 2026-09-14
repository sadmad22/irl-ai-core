# O7 ↔ G-01 ↔ G-02 Integration Test Matrix v1

## Status

**Step 4 — Integration Matrix.**

This document maps every approved reconciliation invariant (R-01 through R-20) to an explicit integration test. It is a test-planning artifact only.

Step 4 does **not** authorize production implementation changes. Step 5 will add only the minimum missing tests identified here.

## Baseline

```text
main @ cb0d15101ec5179244fc5d00fe8a10f16a07812e
```

## Test Strategy

The matrix distinguishes:

- **Existing evidence** — current tests already provide the required integration evidence and should be retained/reused.
- **Step 5 required** — the invariant is covered by lower-level or partial tests, but the reconciliation contract requires an explicit O7 ↔ G-01 ↔ G-02 integration test.

Tests MUST exercise canonical engines rather than reproduce production logic. No LLM/provider runtime, external discovery, or real WordPress side effect is required for the deterministic contract-level integration matrix.

## Integration Matrix

| ID | Invariant | Explicit integration test | Evidence target | Status after Step 4 |
|---|---|---|---|---|
| R-01 | Exact 14-stage Orchestrator order remains canonical | `test_o7_g01_g02_exact_fourteen_stage_order` | `production_orchestrator.STAGES` equals the canonical 14-stage tuple; O7 does not add `human_review` as a stage | Step 5 required |
| R-02 | Canonical G-01 Final Optimization reaches production path | `test_o7_g01_g02_canonical_optimization_reaches_assembly` | Real Orchestrator production handoff supplies `final_optimization` as canonical `optimization` | Step 5 required |
| R-03 | `seo_validation` cannot substitute for optimization | `test_o7_g01_g02_seo_validation_cannot_replace_optimization` | Integrated production assembly path fails/does not accept `seo_validation` as optimization | Step 5 required |
| R-04 | First four G-01 lineage IDs match Assembly lineage | `test_o7_g01_g02_first_four_lineage_match_assembly` | `report_id`, `decision_id`, `strategy_id`, `brief_id` remain identical from Final Optimization through Assembly | Step 5 required |
| R-05 | `optimization_id` survives Assembly | `test_o7_g01_g02_optimization_id_survives_assembly` | Assembly lineage retains canonical `optimization_id` from Final Optimization | Step 5 required |
| R-06 | Six-ID lineage survives Assembly → Package | `test_o7_g01_g02_six_id_lineage_survives_package` | `report_id`, `decision_id`, `strategy_id`, `brief_id`, `draft_id`, `quality_id` remain unchanged through Package | Step 5 required |
| R-07 | `optimization_id` survives Assembly → Package | `test_o7_g01_g02_optimization_id_survives_package` | Package lineage retains the same `optimization_id` as Assembly/Final Optimization | Step 5 required |
| R-08 | Package optimization values remain sourced from canonical optimization | `test_o7_g01_g02_package_optimization_values_are_canonical` | Package SEO projection equals canonical Final Optimization values; no alternate source is accepted | Step 5 required |
| R-09 | O7 checkpoint chain assembly → package → delivery is valid | `test_o7_g01_g02_o7_checkpoint_chain_is_valid` | O7 records valid `assembly_id → package_id → delivery_id` checkpoints before controlled completion | Step 5 required |
| R-10 | O7 preserves orchestration identity | `test_o7_g01_g02_o7_preserves_orchestration_identity` | The same `orchestration_id` remains associated with the controlled production run/checkpoint chain | Step 5 required |
| R-11 | Dry-run reaches `ready_for_delivery` without WordPress side effects | `test_o7_g01_g02_dry_run_reaches_delivery_readiness_without_wordpress` | Canonical Orchestrator → Assembly → Package → Boundary path reaches readiness; WordPress adapter is not invoked and no remote post ID exists | Step 5 required |
| R-12 | Controlled WordPress delivery creates draft only | `test_o7_g01_g02_controlled_delivery_creates_draft_only` | Canonical Boundary is passed to WordPress adapter; returned remote status is `draft`; publication remains disabled | Step 5 required |
| R-13 | Successful controlled delivery resolves to `human_review` | `test_o7_g01_g02_controlled_delivery_resolves_to_human_review` | Successful controlled draft delivery ends in O7 `human_review`, not automatic approval/publication | Step 5 required |
| R-14 | `publish=false` and human approval remain enforced end-to-end | `test_o7_g01_g02_publication_intent_is_immutable` | `target=wordpress`, `mode=wordpress_draft`, `publish=false`, `human_approval_required=true` survive the integrated path | Step 5 required |
| R-15 | Lineage conflict fails closed deterministically | `test_o7_g01_g02_lineage_conflict_fails_closed_deterministically` | Conflicting canonical lineage produces the same failure classification on repeated execution and cannot reach delivery | Step 5 required |
| R-16 | Missing checkpoint fails closed | `test_o7_g01_g02_missing_checkpoint_fails_closed` | O7 cannot reach delivery readiness when a required assembly/package/delivery checkpoint is missing or invalid | Step 5 required |
| R-17 | Orchestration failure stops production | `test_o7_g01_g02_orchestration_failure_fails_closed` | Failure prevents downstream Assembly/Package/Boundary/WordPress progression and preserves failure traceability | Existing partial; Step 5 explicit integration required |
| R-18 | WordPress delivery failure stops production | `test_o7_g01_g02_wordpress_failure_fails_closed` | WordPress adapter failure leaves controlled production failed and does not transition to `human_review` as successful delivery | Existing partial; Step 5 explicit integration required |
| R-19 | No canonical lineage field disappears at any tested canonical artifact boundary | `test_o7_g01_g02_lineage_is_preserved_across_canonical_boundaries` | Assert the complete six-ID lineage plus `optimization_id` across Final Optimization → Assembly → Package → Delivery Boundary where contractually carried | Step 5 required |
| R-20 | End-to-end O7 → G-01 → G-02 traceability without requiring full lineage persistence in O7 state | `test_o7_g01_g02_end_to_end_traceability_without_o7_full_lineage_persistence` | Trace Final Optimization identity/lineage through canonical artifacts and connect the chain to O7 via `orchestration_id` and canonical checkpoints; do not require O7 to store the full lineage | Step 5 required |

## Required Boundary Test

At least one Step 5 test MUST exercise the actual canonical chain:

```text
Final Optimization
        ↓
Production Orchestrator
        ↓
Production Assembly
        ↓
Article Package
        ↓
Production Delivery Boundary
        ↓
O7 Controlled Production
```

The WordPress adapter is exercised through the controlled delivery path. The test MUST capture the exact Boundary object passed to the adapter rather than reconstructing it in the test.

## Dry-Run Gate Coverage

The dry-run integration evidence MUST establish all of the following in one coherent controlled path where practical:

1. canonical Final Optimization is consumed;
2. G-02 first-four lineage binding is preserved;
3. six-ID lineage and `optimization_id` remain intact through Package;
4. canonical Delivery Boundary is produced;
5. O7 checkpoints are valid;
6. state reaches `ready_for_delivery`;
7. WordPress delivery side effects do not occur;
8. no remote post ID is produced;
9. publication intent remains draft-only.

## Controlled Draft Gate Coverage

The controlled live integration evidence MUST establish:

1. canonical Delivery Boundary reaches the WordPress adapter;
2. only draft delivery is accepted;
3. remote status is `draft`;
4. `publish=false` remains enforced;
5. human approval remains required;
6. `orchestration_id` and O7 checkpoint identities remain traceable;
7. successful delivery resolves to `human_review`;
8. automatic publication does not occur.

## Failure Matrix Coverage

The Step 5 suite MUST explicitly cover:

| Failure class | Matrix ID | Expected behavior |
|---|---|---|
| Missing G-01 lineage | R-03/R-04 | Fail closed; no downstream delivery |
| Conflicting first-four lineage | R-04/R-15 | Deterministic lineage failure |
| Conflicting draft/quality lineage | R-06/R-15 | Deterministic lineage failure |
| Missing/conflicting `optimization_id` | R-05/R-07/R-15 | Fail closed |
| Missing O7 checkpoint | R-09/R-16 | Fail closed; no delivery readiness |
| Invalid O7 transition | R-16 | Fail closed |
| Orchestration failure | R-17 | Stop production; preserve failure state |
| WordPress delivery failure | R-18 | Stop at delivery; no successful `human_review` transition |
| Invalid publication intent | R-14 | Fail closed; no publication |

## State Persistence Boundary

The matrix MUST NOT assert that O7 persists:

```text
report_id
decision_id
strategy_id
brief_id
draft_id
quality_id
optimization_id
```

Those identifiers are verified as canonical artifact-chain lineage. O7-specific persistence is limited by this reconciliation to:

```text
orchestration_id
assembly_id
package_id
delivery_id
controlled production state
publication/human-review controls
```

This preserves the approved distinction:

```text
Canonical lineage preservation ≠ O7 state persistence
```

## Step 5 Entry Criteria

Step 5 may begin only after this matrix is accepted as the implementation test map.

Step 5 MUST:

- add only the minimum missing tests;
- avoid changing production code initially;
- avoid modifying O7/G-01/G-02 contracts;
- avoid modifying preserved production artifacts;
- avoid duplicating engine logic;
- keep the exact canonical 14-stage sequence;
- keep draft-only/human-review invariants unchanged.

Any failing test discovered in Step 5 MUST first be classified under Step 6 as:

1. test-contract issue;
2. existing implementation defect; or
3. architectural contradiction.

No production fix is authorized merely because a new matrix test fails.
