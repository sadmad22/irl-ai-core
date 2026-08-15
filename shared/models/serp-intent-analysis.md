# SERP Intent Analysis Model

## Purpose

Infers the dominant search intent represented by the current organic SERP and assigns an intent classification to each organic result.

## Intent Types

- Informational
- Commercial
- Transactional
- Navigational

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| keyword | string | Yes | Target search query |
| country | string | Yes | SERP country |
| language | string | Yes | SERP language |
| dominant_intent | string/null | Yes | Intent dominating the SERP |
| dominant_confidence | number | Yes | Confidence from 0 to 1 |
| intent_distribution | object | Yes | Weighted distribution by intent |
| intent_counts | object | Yes | Result count by intent |
| mixed_intent | boolean | Yes | Whether the SERP contains materially mixed intent |
| results | array | Yes | Per-result intent classification |

## Method

Intent is inferred from normalized SERP title, snippet, URL, domain, and position. Higher-ranking results receive greater weight when determining the dominant SERP intent.
