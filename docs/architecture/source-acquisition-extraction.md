# Source Acquisition and Extraction

Version: 1.0

## Purpose

The Research Agent previously had a substantive Evidence conversion boundary that started from a prepared source-material.json. That boundary is intentionally preserved.

This layer adds the missing upstream path:

    source URLs
        ↓
    safe source acquisition
        ↓
    Source Document
        ↓
    deterministic content extraction
        ↓
    Extracted Passages
        ↓
    source-backed claim extraction (separate boundary)
        ↓
    source-material.json
        ↓
    substantive canonical Evidence

The implementation therefore makes the system capable of retrieving and preserving source content without pretending that page text is already a verified claim.

## Input

Projects may declare research/<project>/source-urls.json.

Each source declares:

- URL.
- Authority class: official, institutional, or secondary.
- Optional stable source_id.
- Optional provider label.

No SERP result, ranking, snippet, question-frequency record, entity record, or business signal is accepted as a substitute for a declared source URL.

## Safe Acquisition

Acquisition is fail-closed.

The v1 boundary:

- accepts only HTTP(S);
- rejects URL credentials;
- rejects local/private destinations during real network acquisition;
- manually handles redirects so each destination can be validated;
- accepts only HTML/XHTML content types;
- applies request timeout, response byte, and redirect limits;
- records requested URL, final URL, redirect chain, HTTP status, retrieval time, content type, content hash, and raw HTML;
- aborts the corpus when any declared source fails.

The default transport is requests. Tests inject a transport so network behavior is deterministic and does not require shell.cloud.

## Source Document

source-documents.json is the immutable retrieval boundary for the run.

source_document_id is deterministic from the final URL and retrieved content hash. The same source content therefore maps to the same document identity, while changed content produces a new identity.

The document retains raw HTML and a normalized text representation. No factual claim is emitted at this stage.

## Content Extraction

The extractor uses Python's standard-library HTML parser.

It:

- prefers main/article content when available;
- excludes common navigation, footer, header, form, script, style, and similar non-content regions;
- captures headings, paragraphs, list items, and table cells;
- preserves heading context;
- removes duplicate blocks deterministically;
- binds each passage to its source document;
- records passage text hashes and character ranges in normalized text.

The result is extracted-passages.json.

## Claim Boundary

This layer does not convert arbitrary extracted text into canonical Evidence.

The next boundary must be:

    Extracted Passage → source-backed Claim Candidate → passage references → source-material.json

A future claim extractor may use an injected model/provider, deterministic domain rules, or another reviewed method, but every emitted fact must point back to one or more extracted passage IDs and remain constrained by the Expected Claim Map.

There is deliberately no path:

    HTML → LLM interpretation → canonical Evidence

and no path that upgrades SERP or business signals into substantive facts.

## Integration

When source-urls.json exists, the Research Agent invokes the source corpus builder before the existing source-material.json conversion.

Cached source documents/passages are reused when the source manifest fingerprint is unchanged. This prevents repeated Research/Content-Brief invocations from silently refetching the same corpus.

The existing substantive Evidence layer remains authoritative for the transition into canonical Evidence. A project without source-urls.json keeps its prior behavior.

## Failure Semantics

- Invalid manifest: stop.
- Unsafe URL: stop.
- Redirect to unsafe destination: stop.
- Non-HTML response: stop.
- Oversized response: stop.
- Missing/empty body: stop.
- Unextractable document: stop.
- Any source failure: do not write a partial source corpus.
- No fallback to SERP snippets, rankings, search metrics, entity presence, question frequency, or business data.

## Production Boundary After v1

After this layer, the remaining substantive acquisition gap is explicit and measurable:

    Source Document + Extracted Passages
        ↓
    Source-Backed Claim Extraction
        ↓
    Passage-Bound Source Material
        ↓
    Substantive Evidence
        ↓
    Evidence Quality / Section Readiness
        ↓
    Article Writer

This keeps acquisition, extraction, fact extraction, evidence construction, quality assessment, and writing as separate auditable stages.
