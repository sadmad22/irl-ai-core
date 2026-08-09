# Metadata Model

## Purpose

Stores general information about the research session.

## Fields

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| id | string | Yes | Unique research identifier |
| keyword | string | Yes | Target keyword |
| language | string | Yes | ISO language code |
| country | string | Yes | ISO country code |
| created_at | string | Yes | Creation timestamp |
| updated_at | string | Yes | Last update timestamp |
| version | string | Yes | Engine version |
| status | string | Yes | Research status |

## Validation

- id is required
- keyword is required
- language is required
- country is required

## Example

```json
{
  "id": "research-001",
  "keyword": "expat health insurance",
  "language": "en",
  "country": "US",
  "created_at": "2026-08-09T10:00:00Z",
  "updated_at": "2026-08-09T10:30:00Z",
  "version": "0.4",
  "status": "draft"
}
```