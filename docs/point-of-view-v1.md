# Point of View v1

## Purpose

Point of View is an editorial configuration layer that defines the narrative perspective an article should maintain. It is separate from Tone of Voice and Brand Voice.

## Inputs

- `content_strategy_ready`
- `article_config_ready`

The engine preserves `brief_id`, `report_id`, `decision_id`, `strategy_id`, and `config_id` lineage.

## Output

Lifecycle: `point_of_view_ready`.

The contract contains a deterministic point of view selection, editorial guidance, constraints, and audit metadata.

## Selection policy

- `guide` and `buyer_guide` use `second_person` with an `expert_explanatory` stance.
- `comparison` and commercial intent use `third_person` with an `editorial_neutral` stance.
- Other supported article types default to `third_person` and `editorial_neutral`.
- Transactional intent remains reader-directed unless an explicit article type selects the neutral comparison policy.

## Invariants

- No LLM, network, provider, or API call.
- No mutation of source documents.
- No Tone of Voice or Brand Voice content is embedded.
- Output IDs are deterministic SHA-256-derived identifiers.
- Input lineage must match between Content Strategy and Article Configuration.

## Scope boundary

This layer does not write prose, perform perspective classification on finished text, implement Brand Voice (#17), or replace Tone of Voice (#12). It produces configuration for downstream drafting/editorial stages.
