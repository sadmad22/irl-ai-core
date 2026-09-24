# Source Acquisition and Extraction

Version: 1.1

## Purpose

The Research Agent previously had a substantive Evidence conversion boundary that started from a prepared source-material.json. That boundary is intentionally preserved.

This layer adds the upstream path:

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

The implementation therefore retrieves and preserves source content without treating page text as a verified claim.

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

The boundary:

- accepts only HTTP(S);
- rejects URL credentials;
- rejects local/private destinations during real network acquisition;
- manually handles redirects so each destination can be validated;
- accepts only HTML/XHTML content types;
- applies request timeout, response byte, and redirect limits;
- records requested URL, final URL, redirect chain, retrieval time, cache-check time, content type, content hash, raw HTML, ETag, and Last-Modified when supplied;
- aborts the corpus when any declared source fails.

SSRF hardening additionally:

- validates each hostname before its request and validates every redirect destination independently;
- rejects local/private, reserved, ULA, link-local, loopback, and other non-global IPv4/IPv6 addresses;
- rejects malformed URLs and malformed/out-of-range ports with the same fail-closed acquisition error boundary;
- blocks HTTPS-to-HTTP redirects unless a future explicit policy changes that behavior;
- performs two DNS resolutions immediately before a hostname request and rejects a changed resolution set. This is a consistency check, not a complete defense against DNS TOCTOU/rebinding when the HTTP transport performs its own later resolution.

Conditional requests use \`If-None-Match\` and/or \`If-Modified-Since\` only while the current destination matches the cached final URL. Redirects revalidate their destination before any reuse; validator metadata is not forwarded to an unrelated redirected host. A \`304 Not Modified\` response reuses the prior source document body and identity only when the final URL still matches the cached document.

The default transport is requests. The acquisition layer accepts an injectable DNS resolver as well as a transport, so tests can keep both HTTP and DNS behavior deterministic without depending on shell.cloud.

## Source Document

source-documents.json is the retrieval boundary for the run.

\`source_document_id\` is deterministic from the final URL and retrieved content hash. The content identity therefore remains stable across revalidation when the URL and bytes are unchanged, while changed content produces a new identity.

The document now retains:

- \`retrieved_at\`: the time the current content identity was first retrieved;
- \`cache_checked_at\`: the time the cached content was last checked against the source;
- \`etag\`: the server ETag when available;
- \`last_modified\`: the server Last-Modified value when available;
- acquisition and extraction policy versions used for the corpus identity.

A \`304\` keeps the original \`retrieved_at\`, content hash, source-document ID, HTML, and passages. A changed \`200\` produces a new content identity and re-runs deterministic extraction.

## Freshness / Cache

The corpus cache identity is derived from:

    normalized source manifest
        +
    acquisition policy version
        +
    extraction policy version
        ↓
    request_fingerprint

The default freshness window is 24 hours and is configurable through \`cache_max_age_seconds\`.

Behavior:

- Fresh cache → reuse without network access.
- Stale cache → conditional revalidation using available validators.
- \`304\` → preserve document and passage lineage, update \`cache_checked_at\`.
- \`200\` with unchanged content identity → preserve document and passages, refresh cache metadata.
- \`200\` with changed content → create a new source document and re-extract passages.
- \`force_refresh=True\` → revalidate even when the cache is fresh.
- Failed revalidation → fail closed; the stale corpus is not silently accepted as current.

The cache is written only after the complete requested source set succeeds, preserving all-or-nothing corpus writes.

## Content Extraction

The extractor uses Python's standard-library HTML parser.

It:

- prefers main/article content when available;
- excludes common navigation, footer, header, form, script, style, and similar non-content regions;
- captures headings, paragraphs, list items, and table cells;
- preserves heading context;
- removes duplicate blocks deterministically;
- binds each passage to its source document;
- records passage text hashes and character ranges in normalized text;
- exposes an explicit extraction policy version used by cache identity.

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

The existing substantive Evidence layer remains authoritative for the transition into canonical Evidence. A project without source-urls.json keeps its prior behavior.

## Failure Semantics

- Invalid manifest: stop.
- Unsafe URL: stop.
- Redirect to unsafe destination: stop.
- Non-HTML response: stop.
- Oversized response: stop.
- Missing/empty body: stop.
- \`304\` without a valid cached source document: stop.
- Invalid or incompatible cache metadata: do not reuse the cache; acquire a fresh corpus.
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

This keeps acquisition, freshness, extraction, fact extraction, evidence construction, quality assessment, and writing as separate auditable stages.