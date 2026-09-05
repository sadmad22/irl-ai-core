# Outline Editor v1

## Purpose

The Outline Editor converts the approved IRL Content Strategy into a deterministic, editable article outline. It is an editorial planning contract, not a writer.

## Inputs

- Content Strategy (`content_strategy_ready`): source of section sequence and primary keyword.
- Article Configuration (`article_config_ready`): article type and configuration lineage.
- Article Structure (`article_structure_ready`): H3, table, list, FAQ, hook, and conclusion constraints.
- Details to Include (`details_to_include_ready`): downstream editorial inclusion constraints.
- Optional `outline`: explicit editor overrides for section order, heading, level, required status, purpose, and notes.

## Output

`outline_editor_ready` with stable lineage, an ordered editable `sections` list, and preserved upstream structural/details constraints.

## Invariants

1. All upstream lifecycle stages must be correct.
2. `report_id`, `decision_id`, and `strategy_id` must remain aligned across upstream contracts.
3. `brief_id` must match Article Configuration and Article Structure.
4. `article_type` must match Content Strategy `content_type`.
5. Section order is unique, contiguous, and starts at 1.
6. Only H2 and H3 are allowed.
7. H3 count must satisfy the Article Structure bounds.
8. Inputs are never mutated.
9. The engine is deterministic and makes no network, provider, or LLM calls.
10. #19 does not implement Italics (#19.1, P2).

## Architectural boundary

```text
Content Strategy ─┐
Article Config ────┼─> Outline Editor ─> Writer / Editorial Formatter
Article Structure ─┤
Details to Include ┘
```

The Outline Editor does not generate prose, perform SERP analysis, select models, or replace upstream contracts.
