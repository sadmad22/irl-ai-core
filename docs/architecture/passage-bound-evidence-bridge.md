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

## Non-Goals

- changing \`evidence.schema.json\`;
- changing Article Writer or Evidence Quality gates;
- making the provider an Evidence authority;
- publishing to WordPress;
- replacing the legacy substantive source-material path when E output does not exist.
