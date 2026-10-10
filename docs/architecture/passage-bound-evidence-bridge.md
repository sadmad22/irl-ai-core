# Passage-Bound Source Material → Canonical Evidence Bridge

Version: 1.0

## Purpose

This bridge converts accepted \`passage-bound-source-material.json\` into canonical Evidence without changing the canonical Evidence schema.

## Boundary

\`\`\`
Passage-Bound Source Material
        ↓
corpus / lineage re-validation
        ↓
deterministic canonical Evidence builder
        ↓
substantive-evidence.json
        +
passage-bound-evidence-lineage.json
\`\`\`

The source-document and passage bindings remain authoritative inputs. The bridge does not infer missing passages, rewrite claims, substitute sources, or use legacy source material when the passage-bound artifact is present.

## Canonical Evidence

Each accepted fact becomes one canonical \`observation\` Evidence record.

The record preserves:

- report lineage;
- source identity;
- source provider/type/retrieval timestamp;
- structured claim and value;
- confidence;
- relation;
- canonical status and provenance.

The canonical Evidence schema is not weakened or replaced.

## Detailed Lineage Sidecar

The canonical Evidence contract currently does not contain structured \`source_document_id\` or \`passage_ids\`.

Therefore the bridge emits \`passage-bound-evidence-lineage.json\`, keyed by \`evidence_id\`, containing:

- \`candidate_id\`;
- \`source_id\`;
- \`source_document_id\`;
- one or more \`passage_ids\`.

This sidecar is a deterministic audit index, not a second Evidence model.

## Fail-Closed Rules

The bridge rejects:

- missing or malformed Passage-Bound Source Material;
- corpus identity mismatches;
- unknown source documents;
- source/document metadata mismatches;
- unknown passages;
- cross-document passage bindings;
- duplicate candidate IDs;
- duplicate Evidence IDs;
- claims outside the substantive Expected Claim Map.

A missing corpus required to verify lineage is a hard error. There is no fallback to \`source-material.json\`.

## Evidence Identity

Evidence IDs include the report ID, candidate ID, source-document identity, passage binding, claim, and value so distinct source bindings cannot collapse into the same canonical identifier merely because claim/value text is identical.

## Research Agent Integration

For a project containing \`passage-bound-source-material.json\`, the Research Agent uses this bridge to produce \`substantive-evidence.json\`.

For a project without the Passage-Bound artifact, the legacy \`source-material.json\` producer remains available for pre-E projects.

If the Passage-Bound artifact exists but bridge validation fails, the Research Agent fails closed and does not fall back to legacy source material.

## Downstream Boundary

The existing Article Draft loader already consumes \`substantive-evidence.json\`. This bridge therefore feeds canonical Evidence into Section Readiness and Article Writer without changing their contracts.

## Pipeline-Owned Methodology Evidence

External source passages must not be asked to prove the internal mechanics of IRL AI Core. When the passage-bound bridge is active, the Research Agent also writes \`pipeline-methodology-evidence.json\` as a separate set of deterministic, code-owned Evidence records.

That sidecar is built only after the canonical Evidence and lineage sidecar have been written. It verifies project/corpus identity, exact canonical evidence-ID agreement, source-document identity, and passage bindings before recording internal source identity, provider, method, analyzer, analyzer version, and lineage metadata.

The Expected Claim Map classifies the methodology families as \`evidence_kind: "pipeline"\`, distinct from source-backed \`substantive\` claims and discovery \`signal\` claims. Section Readiness accepts these records only when their artifact identity and provenance match the trusted pipeline contract. They are added to Content Strategy's evidence references without changing the already-made Decision's evidence references.

This split prevents a source extraction provider from fabricating claims about the internal editorial pipeline, while keeping the canonical passage-bound Evidence IDs and lineage sidecar unchanged.

## Downstream Boundary

The Article Draft builder uses the Content Brief's \`evidence_refs\` as its authoritative upstream lineage. Pipeline-owned methodology references are added to Content Strategy separately from the Decision's evidence references, so internal process metadata does not alter the earlier decision.

## Non-Goals

- changing \`evidence.schema.json\`;
- changing Article Writer or Evidence Quality gates;
- making the provider an Evidence authority;
- publishing to WordPress;
- replacing the legacy substantive source-material path when E output does not exist.
