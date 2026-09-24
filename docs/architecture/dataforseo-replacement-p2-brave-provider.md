# IRL AI Core — P2 Brave Provider

**Phase:** P2 — Brave Provider
**Status:** implementation in progress

## Scope

P2 implements Brave Search API as a real SERP/Search provider behind the P1 `SERPProvider` contract.

Included:
- Brave Web Search connector;
- provider-specific configuration;
- authentication and normalized provider errors;
- URL normalization through the provider-neutral SERP normalizer;
- country/language mapping;
- configurable result count, pagination offset, freshness, and timeout;
- Brave-specific contract and negative tests;
- explicit `provider_order` semantics.

Not included:
- Google Ads / Keyword Metrics (P3);
- production provider switch or Mock prohibition (P4);
- real credentialed E2E (P6);
- DataForSEO removal (P7).

## Brave API boundary

The implementation uses the Brave Web Search endpoint and sends the API key through `X-Subscription-Token`. Brave supports country and search-language parameters, result count up to 20 for Web Search, pagination through `offset` up to 9, and freshness filters such as `pd`, `pw`, `pm`, and `py`.

The normalized IRL response does not expose Brave-specific ranking fields as Google ranking semantics. Positions are assigned strictly as `provider_order` after the Brave result list is received.

## Configuration

- `BRAVE_SEARCH_API_KEY`
- `BRAVE_SEARCH_BASE_URL`
- `BRAVE_SEARCH_COUNT`
- `BRAVE_SEARCH_OFFSET`
- `BRAVE_SEARCH_FRESHNESS`
- `BRAVE_SEARCH_TIMEOUT_SECONDS`

Secrets must remain local and must not enter Git, fixtures, logs, or snapshots.

## Architectural invariant

The downstream pipeline remains unchanged:

`Brave SERP → normalized SERP contract → Research → Evidence → Readiness → Article Draft`

Adding Brave requires no redesign of downstream Research/Evidence/Writer stages.
