# Details to Include v1

## Purpose

Details to Include is a deterministic Content Configuration contract for downstream editorial stages. It defines whether and how many **Key Takeaways**, **Quotes**, and **Bold** formatting elements should be included.

It is configuration, not generated article content.

## Inputs

The engine consumes:

- `Content Strategy` at `content_strategy_ready`
- `Article Configuration` at `article_config_ready`
- optional editorial overrides under `details`

`report_id`, `decision_id`, and `strategy_id` must match across both upstream contracts. `brief_id` and `config_id` are inherited from Article Configuration.

## Output

The engine emits `details_to_include_ready` with a deterministic `details_to_include_id`.

### Key Takeaways

Default policy:

- enabled: `true`
- required: `true`
- count: `3–5`, target `4`

The engine specifies the quantity only. The downstream Writer creates the actual takeaways.

### Quotes

Default policy:

- enabled: `true`
- required: `false`
- count: `0–2`, target `1`
- source requirement: `verified_source_evidence`
- attribution: required
- evidence gate: `verified_evidence_required`

The Core never invents or generates quote text. A downstream rendering stage must block a quote when verified source evidence is unavailable.

### Bold

Default policy:

- enabled: `true`
- required: `false`
- maximum: `3` per section
- policy: `editorial_emphasis_only`

Bold is an editorial formatting mechanism, not an SEO keyword-stuffing mechanism.

## Invariants

1. `min <= target <= max` for all count ranges.
2. A required feature must be enabled.
3. A disabled feature must have zero count.
4. A required count must have `min >= 1`.
5. Quotes must always declare verified-source evidence and attribution requirements.
6. Bold must remain governed by `editorial_emphasis_only`.
7. No prose, quote text, provider calls, network access, or LLM invocation occurs in this engine.

## Architectural boundary

```text
Content Strategy + Article Configuration
                  |
                  v
       Details to Include Contract
                  |
                  v
          Writer / Formatter
```

The contract does not duplicate Tone of Voice, Point of View, Editorial Cleanup, Model Router, or Brand Voice.
