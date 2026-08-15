# Query Intent Model

## Purpose

Classifies the search intent expressed by the keyword itself, without using SERP evidence.

## Intents

- Informational
- Commercial
- Transactional
- Navigational

## Output

- `primary_intent`
- `secondary_intent`
- `confidence`
- `scores`
- `signals`

Query intent is intentionally kept separate from SERP intent. SERP intent is inferred from the pages ranking for the query and may disagree with the query-level classification.
