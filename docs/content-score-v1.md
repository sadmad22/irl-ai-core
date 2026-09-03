# Content Score v1

Content Score v1 is a deterministic editorial quality signal derived from the P0 Integration contract.

## Scored inputs

- Article Draft Quality: 65%
- SEO Validation: 35%

The SEO component scores only `primary_keyword`, `title`, and `headings`. `evidence_lineage` and `structure` are intentionally excluded because those dimensions are already represented by Article Draft Quality; this avoids double-counting.

## Context-only inputs

Semantic SEO, SERP/competitive analysis, and Article Configuration are preserved as context but are not scored in v1. The current contracts expose counts, competitor analysis structures, and targets, but do not yet define normalized quality metrics against which a defensible 0–100 score can be calculated.

## Formula

`score = (quality_score × 0.65) + (seo_score × 0.35)`

Each component is the percentage of its selected boolean checks that pass. The final score is rounded to two decimal places.

No network access, rewriting, publication decision, or upstream mutation occurs in the Content Score engine.
