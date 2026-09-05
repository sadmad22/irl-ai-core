# IRL Brand Voice v1

## Roadmap

Final Implementation Roadmap #17 — Brand Voice (P1).

## Purpose

Brand Voice defines the stable editorial identity of Insurance Review Lab. It is distinct from Tone of Voice (#12), Point of View (#13), and editorial cleanup (#15).

- Tone of Voice defines **how the writing sounds**.
- Point of View defines **the perspective from which the writing speaks**.
- Brand Voice defines **who Insurance Review Lab is when it communicates**.
- Editorial Cleanup improves an existing draft without changing its claims or structure.

## Contract

`build_brand_voice()` consumes `content_strategy_ready` and `article_config_ready` documents and emits `brand_voice_ready`.

The contract preserves the upstream lineage and provides a structured IRL Brand Voice definition intended for downstream LLM drafting, revision, and editorial tasks.

## Master definition

Core identity:

- Insurance Review Lab
- independent insurance research and education platform
- archetype: `trusted_research_advisor`
- reader relationship: `advisor_not_salesperson`

Core traits:

- calm
- confident
- clear
- practical
- evidence-aware
- human

The definition also specifies expression style, vocabulary, confidence and uncertainty policy, editorial principles, promotional boundaries, insurance-specific language rules, human-writing rules, audience, and mission.

## LLM boundary

The Brand Voice layer provides structured guidance for an LLM but does not invoke an LLM itself.

The intended separation is:

`Brand Voice Schema → Model Router → Provider Adapter → External API`

Core does not import provider SDKs, access credentials, make network calls, or mutate source documents.

## Invariants

- Input lifecycle stages must be ready.
- `report_id`, `decision_id`, and `strategy_id` must match across Content Strategy and Article Configuration.
- Article Configuration must provide `brief_id` and `config_id`.
- Content Strategy and Article Configuration must use the same article/content type.
- The emitted Brand Voice is deterministic for the same inputs.
- Inputs are not mutated.
- Brand Voice does not redefine Tone of Voice or Point of View.
- Brand Voice does not invoke an LLM or provider.
- The output schema is strict (`additionalProperties: false`).
