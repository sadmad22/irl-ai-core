# Image Placement / Media Strategy v1

## Scope
Final Implementation Roadmap #11 — Image Placement / Media Strategy (P1).

This layer transforms an `image_style_ready` artifact into a deterministic media-planning artifact. It decides placement, editorial media role, and image density. It does not generate, upload, publish, or render media.

## Input
- `image_style_ready`
- Preserves article/research lineage and `image_spec_id` / `image_style_id`.
- Consumes each `styled_images` entry exactly once.

## Output
- Lifecycle: `image_media_strategy_ready`
- Deterministic `media_strategy_id`
- Strategy: density, max_images, hero requirement, repetition avoidance, visual breaks
- Per-image placement and editorial media role
- Explicit non-execution constraints

## Enums
- Placement: `hero`, `section`, `inline`
- Media role: `hero`, `explain`, `illustrate`, `compare`, `break`, `support`
- Density: `low`, `moderate`, `high`

## Boundaries
- No network access
- No image provider calls
- No WordPress writes
- No media upload
- No HTML generation
- No source mutation
- No #12 Tone of Voice or later roadmap behavior

## Determinism
The `media_strategy_id` is derived from lineage, strategy, and placements using SHA-256. Identical inputs produce identical output.
