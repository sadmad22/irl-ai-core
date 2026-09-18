# I-08 — Orchestrator Integration Review

## 1. Scope

Review the integration of the Intelligence layer with the existing production orchestrator without changing the canonical 14 stages, the six-ID production lineage, O7/G-01/G-02, or protected research artifacts.

## 2. Reviewed Components

- `agents/research/production_orchestrator.py`
- `tests/test_production_orchestrator.py`
- `agents/research/content_research_pipeline.py`
- `agents/research/content_brief_agent.py`
- `agents/research/article_draft_agent.py`
- Intelligence Contract v0.2
- Intelligence Engine and Research→Intelligence traceability boundary

## 3. Findings

### I-08-ORCH-01 — Stage exists and order is correct

The orchestrator already declares the canonical 14 stages, including `intelligence` in the existing position:

Research → Intelligence → Configuration → Structure → Draft → Editorial Cleanup → Media → Linking → Optimization → QA → Production Assembly → Article Package → Production Delivery Boundary → WordPress Delivery.

**Result: PASS.**

No new stage is required or permitted.

### I-08-ORCH-02 — Intelligence completion is currently indirect

The current `_completed_stages()` implementation detects `content_brief` and then marks all three stages below as completed:

- `intelligence`
- `configuration`
- `structure`

This means `content_brief` is currently acting as an indirect completion signal for Intelligence.

**Result: CONTRACT MISMATCH CONFIRMED.**

The Intelligence Contract requires an independent Intelligence Artifact with:

- `intelligence_id`
- `report_id`
- `lifecycle_stage = intelligence_ready`

Therefore the presence of `content_brief` cannot remain the canonical completion criterion for Intelligence.

### I-08-ORCH-03 — Current upstream pipeline has no independent Intelligence artifact handoff

The current content pipeline invokes the existing Research/Content Brief path and ultimately consumes `content_brief`, while the Research Agent itself currently proceeds from ResearchReport into Recommendation, Decision, and Content Strategy.

The new Intelligence Engine exists independently, but the production pipeline does not yet materialize and hand off its Intelligence Artifact as a distinct stage output.

**Result: INTEGRATION NOT YET COMPLETE.**

### I-08-ORCH-04 — Do not apply a partial Orchestrator-only fix

Changing only `_completed_stages()` to require an Intelligence Artifact would be insufficient at this point because the current production path does not yet produce that artifact as a canonical stage output.

Such a partial change would make the stage detector stricter without establishing the producer/consumer boundary required by the architecture.

**Decision: DEFER IMPLEMENTATION TO I-09.**

I-09 is the appropriate gate for wiring the already-implemented Intelligence Engine into a real topic flow and validating the resulting stage checkpoint end-to-end.

## 4. Boundary Decision

The following boundaries remain unchanged:

- No new production stage.
- No change to the canonical 14-stage order.
- No change to the six-ID production lineage.
- `intelligence_id` remains a Domain Artifact ID and is not added to the six-ID lineage.
- `ResearchReport.search_intent` remains canonical.
- Intelligence does not own Recommendation, Decision, or Content Strategy.
- O7/G-01/G-02 are not modified.
- No external provider is introduced.
- No auto-publish behavior is introduced.

## 5. I-08 Gate Result

**I-08 PASS — ORCHESTRATOR REVIEW COMPLETE; INTEGRATION IMPLEMENTATION DEFERRED TO I-09.**

The review establishes that an Orchestrator integration change is necessary, but it should be implemented together with the real-topic Intelligence stage integration rather than as an isolated detector change.

## 6. Required I-09 Acceptance Criteria

Before I-09 can pass:

1. A real ResearchReport must produce a canonical Intelligence Artifact.
2. The Intelligence Artifact must validate against schema, lifecycle, lineage, and evidence traceability rules.
3. The Orchestrator must recognize Intelligence completion from the canonical Intelligence Artifact, not from `content_brief`.
4. Configuration and Structure must retain distinct stage boundaries.
5. Recommendation and Decision ownership must remain downstream and independent.
6. The six-ID production lineage must remain unchanged.
7. Existing O7/G-01/G-02 behavior must remain intact.
8. Full regression must remain green.
