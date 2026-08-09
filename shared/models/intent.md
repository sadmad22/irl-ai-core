# Search Intent Model

## Purpose

Defines search intent.

## Fields

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| type | string | Yes | Informational, Commercial, Transactional, Navigational |
| confidence | number | Yes | Confidence score |

## Validation

- type is required
- confidence between 0 and 1

## Example

```json
{
  "type": "Commercial",
  "confidence": 0.94
}
```