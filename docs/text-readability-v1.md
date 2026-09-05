# Text Readability v1

## Purpose

The Text Readability layer evaluates an approved Article Draft using deterministic local readability metrics and, when explicitly supplied, an injected LLM assessment.

## Roadmap position

This implements Final Implementation Roadmap **#14 — Text Readability (P1)**. It is intentionally separate from Tone of Voice, Point of View, and later AI Content Cleaning.

## Inputs

- `Article Draft` with lifecycle `draft_ready`.
- Optional LLM provider exposing `assess(text=..., local_metrics=...)`.

## Local analysis

The v1 local analyzer uses Python standard-library tokenization and calculates:

- word count
- sentence count
- syllable count
- average words per sentence
- average syllables per word
- Flesch Reading Ease
- Flesch-Kincaid Grade Level

The default diagnostic target is grade 10.0. The outcome is `passed` when the calculated grade is at or below the target and `needs_revision` otherwise. This is a diagnostic gate, not a publication-quality verdict; insurance content may legitimately require technical language.

## LLM boundary

The core never selects, instantiates, or calls a network LLM. An LLM evaluator may be injected explicitly through the provider interface. Without a provider, the contract records `not_requested`; with one, the returned assessment is copied into the contract as `provided`.

## Invariants

- deterministic output for identical inputs and provider results
- complete Article Draft lineage is preserved
- no source or draft mutation
- no implicit network access
- no dependency on third-party readability packages
- provider calls occur only when an explicit provider is supplied
- local metrics remain available independently of the LLM assessment

## Output lifecycle

`text_readability_ready`

## Scope boundary

This layer does not rewrite text, clean AI-generated prose, change tone, select a model, or apply brand voice. Those concerns remain separate roadmap capabilities.
