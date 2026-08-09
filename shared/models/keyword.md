# Keyword Model

## Purpose

Represents the primary keyword.

## Fields

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| keyword | string | Yes | Primary keyword |
| search_volume | integer | No | Monthly search volume |
| difficulty | integer | No | Keyword difficulty |
| cpc | number | No | Cost per click |
| trend | array | No | Search trend history |
| language | string | Yes | ISO language code |
| country | string | Yes | ISO country code |

## Validation

- keyword is required

## Example

```json
{
  "keyword": "expat health insurance",
  "language": "en",
  "country": "US"
}
```