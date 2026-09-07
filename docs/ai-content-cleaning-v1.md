# AI Content Cleaning / Editorial Cleanup v1.1

## Roadmap position

This implements Final Implementation Roadmap **#15 — AI Content Cleaning / Editorial Cleanup (P1)** and closes **#25 — Humanize Text (P3)** by integrating humanization into the existing editorial-cleanup layer. Humanize Text is not a separate feature, engine, lifecycle, or schema.

## Purpose

The layer performs controlled editorial cleanup of an approved Article Draft through an explicitly injected LLM provider. It removes common AI/editorial artifacts, improves grammar and clarity, reduces redundancy, improves formatting, and can humanize formulaic or unnatural phrasing while preserving the article's factual and structural contract.

Humanization is enabled by default through the `humanize_text` editorial rule and can be explicitly disabled by the caller. It is an editorial instruction to the same cleanup provider, not a second processing pipeline.

## Inputs

- `Article Draft` with lifecycle `draft_ready`.
- Explicitly injected LLM provider exposing `clean(sections=..., editorial_rules=...)`.
- Optional `Tone of Voice` contract with lifecycle `tone_of_voice_ready`.
- Optional `Point of View` contract with lifecycle `point_of_view_ready`.
- Optional `humanize_text` boolean control; defaults to `true`.

Tone of Voice and Point of View guide cleanup only. Brand Voice remains a later roadmap capability (#17).

## Humanization rules

When `humanize_text` is enabled, the provider is instructed to:

- make phrasing more natural and less formulaic
- reduce detectable AI-style artifacts as an editorial-quality objective
- preserve claims and their meaning
- preserve evidence and citation references
- add no new facts
- avoid structural rewriting

The provider may report a `humanization` change category in its typed change log. Any declared risk flag still changes the output status to `needs_review`.

## Provider boundary

The Core does not select, instantiate, or network-call an LLM. The provider is injected by the caller. The provider receives deep copies of the section text and editorial rules.

The provider must return exactly one cleaned body for every input section. Headings and section order remain owned by the source draft.

## Editorial invariants

The cleanup layer must:

- preserve claims and their meaning
- preserve evidence/citation references
- preserve section structure and headings
- add no new facts
- avoid rewriting claims as a factual transformation
- avoid structural rewriting
- never mutate the source Article Draft

A provider can return risk flags for `claim_change`, `new_fact`, `citation_change`, `structural_change`, or `meaning_change`. Any risk flag changes the output status to `needs_review`.

## Output

Lifecycle: `editorial_cleanup_ready`

Schema version: `1.1`.

The contract records the original and cleaned body for each section, a typed change log, risk flags, fixed constraints, lineage, deterministic ID, and audit metadata. Humanization remains represented inside this same Editorial Cleanup contract.

## Change categories

- `grammar`
- `clarity`
- `redundancy`
- `formatting`
- `ai_artifact`
- `humanization`

## Status

- `cleaned`: editorial cleanup was returned without declared risk flags.
- `unchanged`: provider reports no editorial changes.
- `needs_review`: provider declares a risk flag that requires human/editorial review.

## Scope boundary

This layer does not implement Brand Voice, model selection, factual verification, source retrieval, WordPress writes, or autonomous publication. It remains one editorial transformation contract around an explicitly supplied LLM evaluator; Humanize Text does not introduce a separate pipeline.
