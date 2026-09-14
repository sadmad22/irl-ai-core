# G-02 — Final Optimization Lineage Binding Contract v1

## Status

**Contract phase only — implementation is not authorized by this document.**

G-02 closes the verified Gate 5 gap: Final Optimization contains the upstream lineage `report_id → decision_id → strategy_id → brief_id`, while Production Assembly and Article Package independently carry the full production lineage `report_id → decision_id → strategy_id → brief_id → draft_id → quality_id`. The missing guarantee is explicit cross-binding between those representations.

## 1. Objective

Guarantee that Final Optimization lineage is preserved, bound, and validated across:

`Final Optimization → Orchestrator → Production Assembly → Article Package`

No lineage identifier may be silently replaced, inferred, dropped, or merged when crossing a boundary.

## 2. Canonical lineage

The canonical production lineage is exactly:

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

Final Optimization owns and must carry the first four identifiers:

```text
report_id
 decision_id
 strategy_id
 brief_id
```

Production Assembly owns the complete six-identifier production lineage.

Article Package owns the complete six-identifier production lineage.

`optimization_id` identifies the Final Optimization Artifact. It is an artifact identity, not a replacement for any production lineage identifier.

## 3. Binding rules

### 3.1 Final Optimization → Assembly

When Assembly receives `artifacts.optimization`:

- `optimization.lineage.report_id` MUST equal `assembly.lineage.report_id`.
- `optimization.lineage.decision_id` MUST equal `assembly.lineage.decision_id`.
- `optimization.lineage.strategy_id` MUST equal `assembly.lineage.strategy_id`.
- `optimization.lineage.brief_id` MUST equal `assembly.lineage.brief_id`.
- `optimization.optimization_id` MUST remain intact.
- Assembly MUST NOT derive, rewrite, or replace those four values from another source.
- Any missing or conflicting value MUST fail closed with a deterministic lineage error.

### 3.2 Assembly → Package

When Article Package is built from Assembly artifacts:

- the six canonical production lineage identifiers MUST remain unchanged;
- `optimization_id` MUST remain traceable in the package-level lineage;
- the Final Optimization SEO values MUST remain sourced from the canonical `optimization` artifact;
- Package MUST NOT silently reconstruct or substitute Final Optimization lineage;
- a missing or conflicting `optimization_id`, where the Assembly contract provides one, MUST fail closed.

The Package `optimization` projection may contain only the contracted delivery SEO fields. It is not a second Final Optimization artifact and must not become one.

### 3.3 No silent substitution

The following substitutions are prohibited:

- `seo_validation` → `optimization`;
- `article_draft` lineage → Final Optimization lineage when the values conflict;
- `quality` lineage → Final Optimization lineage when the values conflict;
- generated/inferred IDs replacing explicit upstream IDs;
- dropping `optimization_id` without an explicit contract rule.

A conflict is an error, not a merge opportunity.

## 4. Ownership boundaries

### Final Optimization

Produces the canonical Final Optimization Artifact v1 and its four upstream lineage identifiers.

### Production Orchestrator

Transports the canonical Final Optimization artifact to Assembly. It does not reinterpret lineage.

### Production Assembly

Validates cross-artifact lineage consistency and binds the Final Optimization lineage to the six-ID production lineage. It does not generate SEO values or lineage identifiers.

### Article Package

Preserves the six-ID production lineage and the traceability of `optimization_id`. It projects only the contracted optimization delivery fields. It does not become a new optimization producer.

## 5. Fail-closed behavior

The following conditions MUST fail:

1. Final Optimization missing any of `report_id`, `decision_id`, `strategy_id`, or `brief_id`.
2. Final Optimization lineage conflicts with Assembly lineage on any of those four IDs.
3. Assembly lineage conflicts with `article_draft` or `quality` lineage on any of the six canonical IDs.
4. Package loses or changes any canonical production lineage ID.
5. Package cannot preserve the Final Optimization artifact identity `optimization_id` when that identity is part of the contracted upstream lineage.
6. Any implementation attempts to repair a conflict by copying a value from another artifact.

## 6. Determinism

For identical valid upstream artifacts and identical lineage, the resulting Assembly and Package lineage must be identical.

A lineage conflict must produce the same failure classification for the same conflicting inputs.

## 7. Scope of G-02 implementation

### Files permitted to change

1. `agents/research/production_assembly_engine.py`
2. `agents/research/article_package_engine.py` — only if required to preserve `optimization_id` at the package lineage boundary.
3. `tests/test_production_assembly_engine.py`
4. `tests/test_article_package_engine.py`
5. `tests/test_orchestrator_integration_v1.py` — only if required for end-to-end lineage assertions.

### Files explicitly not to change

- `agents/research/final_optimization.py`
- `agents/research/production_orchestrator.py` unless a proven transport defect is discovered
- `agents/research/content_optimization.py`
- `agents/research/recovery_executor.py`
- `shared/models/final-optimization.md`
- `shared/schemas/final-optimization.schema.json`
- production artifacts

No new production stage, provider runtime, network behavior, or discovery logic is permitted.

## 8. Test Matrix

| ID | Test | Expected result |
|---|---|---|
| G02-A1 | Valid Final Optimization lineage matches Assembly lineage | PASS |
| G02-A2 | `report_id` mismatch | `LINEAGE_MISMATCH` |
| G02-A3 | `decision_id` mismatch | `LINEAGE_MISMATCH` |
| G02-A4 | `strategy_id` mismatch | `LINEAGE_MISMATCH` |
| G02-A5 | `brief_id` mismatch | `LINEAGE_MISMATCH` |
| G02-B1 | Assembly lineage remains identical to draft/quality six-ID lineage | PASS |
| G02-B2 | `draft_id` mismatch between draft and quality/Assembly | `LINEAGE_MISMATCH` |
| G02-B3 | `quality_id` mismatch between quality and Assembly | `LINEAGE_MISMATCH` |
| G02-C1 | `optimization_id` survives Assembly | PASS |
| G02-C2 | `optimization_id` survives Assembly → Package lineage | PASS |
| G02-C3 | Missing `optimization_id` where contract requires it | Fail-Closed |
| G02-D1 | Package six-ID lineage equals Assembly six-ID lineage | PASS |
| G02-D2 | Package cannot replace lineage from a conflicting optimization artifact | Fail-Closed |
| G02-E1 | `seo_validation` cannot substitute for Final Optimization | Fail-Closed |
| G02-E2 | Final Optimization SEO fields remain the package optimization source | PASS |
| G02-F1 | Identical valid inputs produce identical lineage | PASS |
| G02-F2 | Identical conflicting inputs produce deterministic failure classification | PASS |
| G02-G1 | End-to-end Orchestrator → Assembly → Package preserves lineage | PASS |
| G02-G2 | No canonical lineage field disappears at Assembly/Package boundary | PASS |

## 9. Regression requirement

Before G-02 can be closed:

1. All G-02 targeted tests MUST pass.
2. Existing Production Assembly tests MUST pass.
3. Existing Article Package tests MUST pass.
4. Existing Orchestrator integration tests MUST pass.
5. Full project regression MUST pass.
6. No production artifact may be modified.
7. No change may introduce a new production stage or duplicate optimization engine.

## 10. Gate criteria

G-02 is **PASS** only when every binding rule and every applicable test-matrix item passes.

Until then, Gate 5 remains open and the project must not claim complete lineage verification.

## 11. Explicit implementation stop

This document defines the boundary and tests only. **No implementation is implied or authorized until the G-02 contract and Test Matrix are reviewed and approved.**
