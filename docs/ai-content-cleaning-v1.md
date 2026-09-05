# AI Content Cleaning / Editorial Cleanup v1

## Roadmap position

This implements Final Implementation Roadmap **#15 — AI Content Cleaning / Editorial Cleanup (P1)**. Humanize Text is not implemented as a separate feature; it is folded into this editorial-cleanup layer.

## Purpose

The layer performs controlled editorial cleanup of an approved Article Draft through an explicitly injected LLM provider. It is intended to remove common AI/editorial artifacts, improve grammar and clarity, reduce redundancy, and improve formatting without changing the article's factual or structural contract.

## Inputs

- `Article Draft` with lifecycle `draft_ready`.
- Explicitly injected LLM provider exposing `clean(sections=..., editorial_rules=...)`.
- Optional `Tone of Voice` contract with lifecycle `tone_of_voice_ready`.
- Optional `Point of View` contract with lifecycle `point_of_view_ready`.

Tone of Voice and Point of View guide cleanup only. Brand Voice remains a later roadmap capability (#17).

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

The contract records the original and cleaned body for each section, a typed change log, risk flags, fixed constraints, lineage, deterministic ID, and audit metadata.

## Change categories

- `grammar`
- `clarity`
- `redundancy`
- `formatting`
- `ai_artifact`

## Status

- `cleaned`: editorial cleanup was returned without declared risk flags.
- `unchanged`: provider reports no editorial changes.
- `needs_review`: provider declares a risk flag that requires human/editorial review.

## Scope boundary

This layer does not implement Brand Voice, model selection, factual verification, source retrieval, WordPress writes, or autonomous publication. It is an editorial transformation contract around an explicitly supplied LLM evaluator.
