# Editorial Source Evidence Contract

Version: 1.0

## Purpose

Editorial Source Evidence is the reader-facing source-material boundary between Research Evidence and the Article Writer.

It is not a replacement for Research Evidence, and it does not create a new production stage or production-lineage identifier.

## Relationship to Research Evidence

Brave source page
  -> Editorial Source Evidence
  -> Article Writer

Research Evidence
  -> Research / Intelligence / Recommendation / Decision

Editorial Source Evidence is a reader-facing projection of an existing Research Evidence item. Its evidence_id is the same canonical Research Evidence reference. This prevents a second factual evidence identity from being introduced.

## Canonical Shape

The Article Draft contract already defines the canonical editorial_evidence shape:

- evidence_id: the underlying Research Evidence identifier.
- section_index: the Article Draft section that may use the source material.
- status: candidate or ready.
- text: verified reader-facing source material.
- source.type: serp_result.
- source.url: the source-page locator.
- source.title: source-page title.
- source.domain: source-page domain.
- provenance.artifact: serp-analysis.json.
- provenance.method: serp-snippet-editorial-v1 or serp-page-editorial-v1.
- provenance.verification: snippet_only or page_reviewed.

## Brave Boundary

Brave is the discovery mechanism. A Brave SERP result is not itself the factual source.

For page-reviewed Editorial Source Evidence:

Brave result URL
  -> source page retrieval
  -> page text / factual excerpt
  -> build_editorial_evidence(...)
  -> Article Writer input

page_reviewed is the publishable source-material state. snippet_only is candidate material and must not be treated as equivalent to page review.

## Non-Goals

Editorial Source Evidence does not:

- replace Research Evidence;
- create recommendation or decision semantics;
- add a seventh production-lineage ID;
- add a fifteenth production stage;
- rewrite ResearchReport artifacts;
- publish or deliver content.

## Six-ID Lineage

The canonical production lineage remains:

report_id
decision_id
strategy_id
brief_id
draft_id
quality_id

Editorial Source Evidence references report_id indirectly through its underlying Research Evidence item. It does not enter the six-ID production lineage.

## Determinism and Safety

The builder is deterministic for the same Research Evidence and source-page inputs. It does not call Brave, OpenAI, or WordPress. Source retrieval is an explicit upstream operation so credentials and network access remain outside the deterministic Article Draft contract.


## Production Integration Boundary

The deterministic production path consumes an explicit upstream artifact:

editorial-source-pages.json
  -> editorial_source_evidence_agent
  -> editorial-evidence.json
  -> Article Draft Agent
  -> Article Writer

editorial-source-pages.json is retrieval output, not Research Evidence. It must contain
source-page material keyed by the canonical Research Evidence `evidence_id`, including
`section_index`, source metadata, source text, and verification state.

The materialization agent performs no network access. If the upstream source-page artifact
is absent, Editorial Source Evidence remains optional and inactive. If it is present,
malformed section metadata fails closed and the resulting `editorial-evidence.json`
is deterministic for the same inputs.

The Article Draft Agent materializes Editorial Source Evidence before loading it, so the
boundary cannot be accidentally bypassed when the explicit upstream artifact is present.
