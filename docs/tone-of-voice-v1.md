# Tone of Voice v1

Roadmap item #12 (P1) implements a deterministic editorial tone configuration layer.

## Purpose

The layer converts the ready Content Strategy and Article Configuration into a stable `tone_of_voice_ready` contract for downstream writing/revision components.

It defines **how the article should sound**, not the brand's permanent voice and not the author's point of view.

## Inputs

- `content_strategy_ready`
- `article_config_ready`

The contract preserves `brief_id`, `report_id`, `decision_id`, `strategy_id`, and `config_id` lineage.

## Tone dimensions

- Primary tone: professional, conversational, educational, authoritative, reassuring, analytical.
- Formality: formal, professional, neutral, conversational.
- Directness: direct, balanced, gentle.
- Warmth: low, moderate, high.
- Technicality: plain, moderate, technical.

## Deterministic policy

- `comparison` → analytical.
- `buyer_guide` or commercial/transactional intent → authoritative.
- `guide` or informational intent → educational.
- Otherwise → professional.

The same inputs produce the same `tone_of_voice_id` using SHA-256 over the normalized contract payload.

## Editorial guidance

The v1 contract includes preferred traits, traits to avoid, sentence-level guidance, and reader address. It explicitly avoids hype, sensationalism, fear-based language, and unsupported certainty.

## Boundaries

This layer does not call an LLM, network, provider, or external API. It does not mutate source documents. It does not implement #13 Point of View or #17 Brand Voice. Those remain separate roadmap layers.
