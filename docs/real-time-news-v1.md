# Real-Time News v1

Roadmap item #24 (P3).

## Purpose

Real-Time News v1 selects verified, fresh news evidence for an article. It preserves provider summaries verbatim and emits a deterministic contract for downstream editorial use.

## Architecture

News API / upstream verification -> Real-Time News engine -> editorial/publication layer.

The engine does not call News API, search the web, invoke an LLM, rewrite prose, or publish content.

## Contract

Top-level fields: `real_time_news_id`, `brief_id`, `report_id`, `decision_id`, `strategy_id`, `schema_version`, `method_version`, `lifecycle_stage`, `as_of`, `freshness_hours`, `items`, and `audit`.

Each item contains `news_id`, `url`, `title`, `published_at`, `summary`, and `relevance_score`.

## Freshness

An item is eligible when its publication timestamp is within `freshness_hours` before `as_of` and is not later than `as_of`. `as_of` is explicit input so results remain deterministic.

## Summary integrity

`summary` is upstream evidence. The engine validates and carries it unchanged; it never generates, paraphrases, shortens, expands, or editorially corrects it.

## Selection

Only verified `news_api` items are eligible. HTTPS URLs are required. Items are deduplicated by `news_id`, filtered by freshness, sorted deterministically by relevance descending, publication timestamp ascending, then news ID ascending, and truncated to `max_items` (1-20).

## Versions

- Schema: `1.0`
- Method: `v1`
- Lifecycle: `real_time_news_ready`
