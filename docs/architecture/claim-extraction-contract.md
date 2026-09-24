# Claim Extraction Contract

Version: 1.0

## Purpose

The Claim Extraction Contract is the architectural gate between deterministic source extraction and any future automatic claim extraction provider.

The contract is intentionally split into two stages:

```
Source Document
    ↓
Extracted Passage
    ↓
Claim Candidate
    ↓
Claim↔Passage Binding
    ↓
Claim Map Validation
    ↓
Passage-Bound Source Material
```

No automatic provider is invoked by this layer.

## Candidate Contract

A Claim Candidate must contain:

- a unique `candidate_id`;
- a `source_id`;
- exactly one `source_document_id`;
- one or more `passage_ids`;
- a claim family and attribute;
- subject and structured value;
- confidence;
- a supported relation.

The binding is part of the candidate object, not an external side table. This makes the minimum audit path explicit at the contract boundary.

## Acceptance Gate

The deterministic validator checks:

1. Candidate schema validity.
2. Candidate project identity matches the source corpus.
3. Source Documents and Extracted Passages belong to the same corpus fingerprint and policy versions.
4. The referenced `source_document_id` exists.
5. The candidate `source_id` matches that Source Document.
6. Every referenced `passage_id` exists.
7. Every referenced passage belongs to the candidate's single `source_document_id`.
8. `claim_type + attribute` exists in Expected Claim Map as a substantive claim.
9. Candidate IDs are unique.

Failure at any gate raises an error. No fallback, inference, or reassignment is performed.

## Provider Boundary

A future smart provider may propose Claim Candidates, but provider output is not accepted directly as Evidence.

The provider boundary is:

```
provider output
      ↓
Claim Candidate schema
      ↓
deterministic validator
      ↓
accepted / rejected
```

The provider is therefore a proposal mechanism, while the validator is the acceptance authority.

This PR does not create, configure, or call an LLM provider.

## Passage-Bound Source Material

Accepted candidates are converted deterministically into `passage-bound-source-material`.

Each fact preserves:

- `candidate_id`;
- `source_id`;
- `source_document_id`;
- one or more `passage_ids`;
- claim family and attribute;
- subject and value;
- confidence and relation.

The material also preserves the corpus `request_fingerprint`, acquisition policy version, extraction policy version, source URL, provider, source class, retrieval timestamp, and title.

This artifact is an auditable bridge to the next phase. It does not replace the canonical Evidence schema and it does not bypass Evidence Quality or Article Writer gates.

## Explicit Non-Goals

This contract does not:

- extract claims from HTML;
- interpret passages with an LLM;
- invent or rewrite source facts;
- emit canonical Evidence;
- modify the protected research fixtures;
- change Article Writer or Evidence Quality behavior.

Automatic Claim Extraction remains a separate phase after this contract is accepted.
