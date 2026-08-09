# Metadata Model

## Purpose

Stores general information about the research session.

## Inputs

None

## Outputs

Metadata object.

## Fields

| Field | Type | Required | Description |
|------|------|----------|-------------|
| id | string | Yes | Research ID |
| keyword | string | Yes | Target keyword |
| language | string | Yes | Language |
| country | string | Yes | Target country |
| created_at | datetime | Yes | Creation time |
| updated_at | datetime | Yes | Last update |
| version | string | Yes | Engine version |
| status | string | Yes | draft / completed |

## Validation Rules

- id required
- keyword required
- version required

## Example

research-2026-001

## Notes

Shared across every module.