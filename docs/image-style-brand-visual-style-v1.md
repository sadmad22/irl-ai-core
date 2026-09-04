# Image Style / Brand Visual Style v1

## Audit

Roadmap scope: Final Implementation Roadmap #10 — Image Style / Brand Visual Style (P1).

### Input boundary
- Consumes the ready AI Image Specification (`ai_image_spec_ready`).
- Preserves `brief_id`, `report_id`, `decision_id`, `strategy_id`, `config_id`, `draft_id`, and `image_id` lineage/identity.

### Output boundary
- Produces a separate `image_style_ready` artifact.
- Adds a deterministic Insurance Review Lab visual system to every image specification.
- Does not mutate the AI Image Specification.

### Brand system
- Colors: Deep Navy `#0F172A`, Modern Blue `#2563EB`, Cyan Accent `#06B6D4`, White `#FFFFFF`.
- Visual language: professional, editorial, research-oriented, clean, modern, trustworthy.
- Composition: clear focal point, structured composition, generous whitespace, restrained visual hierarchy.
- Illustration direction: premium editorial illustration, clean geometric elements, subtle analytical/data motifs.
- Restrictions: no watermark, no unnecessary text, no logos, no visual clutter, no off-brand colors, no misleading imagery.

### Explicit exclusions
- No image generation API/provider call.
- No network access.
- No image analysis/Vision call.
- No image placement or media strategy (#11).
- No automatic alt-text generation (#9 is already upstream).
- No Model Router invocation.

## Contract

Lifecycle: `image_style_ready`.

The artifact contains a global `visual_style` contract plus one `styled_images` entry for each upstream image. Each entry preserves the original `image_id` and carries a deterministic `styled_prompt` derived from the upstream prompt and approved brand rules.

## Determinism and validation

The style artifact ID is derived from lineage, image specification identity, and the style contract. Repeated identical inputs must produce identical output. Inputs are copied rather than mutated.

## Non-goals

This layer defines brand governance for image generation; it does not generate or upload images. A later provider may consume this contract.
