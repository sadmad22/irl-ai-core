# Automatic Claim Extraction

Version: 1.0

## Purpose

Automatic Claim Extraction is the first provider-backed stage after the Claim Extraction Contract. It converts an extracted source corpus into proposed Claim Candidates, but it does not grant the provider authority to create Evidence.

## Execution boundary

```
Source Documents + Extracted Passages
            ↓
     injected provider
            ↓
      Claim Candidates
            ↓
   Candidate Schema validation
            ↓
 deterministic Claim Contract validator
            ↓
 Passage-Bound Source Material
```

The provider is always injected explicitly. There is no default provider, implicit model invocation, fallback extractor, or direct HTML-to-claim path.

## Provider input boundary

The provider receives:

- project identity and corpus fingerprint;
- source-document identity metadata, final URL, provider, source type, retrieval time, content hash, and title;
- extracted passages and their source-document lineage.

Raw source HTML and normalized document text are intentionally not exposed through the provider context. Claim proposals must therefore operate on the deterministic passage layer.

## Deterministic acceptance gate

Provider output is accepted only after the existing Claim Extraction Contract validates it. The gate verifies candidate schema validity, corpus identity, source/document binding, passage existence, single-document passage binding, Expected Claim Map membership, and candidate uniqueness.

Any failure is fail-closed. The runner does not repair, reassign, infer, or replace missing bindings.

## Output artifacts

Successful runs persist:

- `claim-candidates.json` — the exact provider proposal after schema acceptance;
- `passage-bound-source-material.json` — deterministic material generated from accepted candidates.

Both artifacts preserve explicit source, source-document, and passage lineage. The second artifact is an auditable bridge and does not replace canonical Evidence.

## Idempotence and safety properties

For identical provider output and corpus inputs, the generated passage-bound material is deterministic because the underlying builder sorts documents, candidates, and passage bindings before serialization.

The provider receives deep copies. Provider-side mutation cannot alter the source corpus loaded by the runner.

No output artifacts are written until provider output has passed the deterministic acceptance gate.

## Non-goals

This stage does not:

- claim that provider-produced values are semantically correct merely because they are structurally bound to passages;
- emit canonical Evidence;
- modify Evidence Quality or Article Writer;
- modify protected fixtures or `.irl-ai-core.env`;
- hide or work around provider failures;
- introduce a default or automatic LLM connection.

Semantic evidence quality remains a separate downstream concern. The central guarantee of this phase is that accepted automatic claims cannot escape the source/document/passage contract.
