# IRL AI Core — P1 Provider Boundary Refactor

**Phase:** P1 — Provider Boundary Refactor  
**Branch:** `feat/dataforseo-replacement-p1-provider-boundary`  
**Scope:** DataForSEO replacement architecture only

## P1 outcome

P1 establishes an explicit, capability-based provider boundary while keeping DataForSEO available as the current legacy provider.

Target architecture:

```
SERP capability
    -> SERP_PROVIDER
    -> SERPProvider contract
    -> provider adapter

Keyword Metrics capability
    -> KEYWORD_METRICS_PROVIDER
    -> KeywordMetricsProvider contract
    -> provider adapter
```

Current defaults remain `dataforseo` until P4. This preserves the existing operational provider while removing the shared-provider coupling.

## Implemented invariants

- SERP and Keyword Metrics no longer share `ACTIVE_PROVIDER`.
- Unknown provider names fail explicitly.
- Mock is selectable only by the explicit `mock` provider name.
- Provider responses expose normalized provenance through `provider`.
- SERP `position` is explicitly `provider_order`; it is not a Google-rank contract.
- DataForSEO Google rank values are not exposed as canonical `position`; normalized results are re-indexed by provider order.
- DataForSEO country selection uses an explicit location-code map rather than a hard-coded SERP location.
- SERP URL normalization is provider-neutral.
- DataForSEO credentials live in a vendor-specific configuration namespace.
- Keyword Metrics uses canonical `competition`; `difficulty` remains accepted only for legacy stored research artifacts.
- Provider boundary errors are normalized into explicit error types.
- Fresh provider responses are validated before entering the Research Agent artifact pipeline.
- Strict provider-response schemas were added for SERP and Keyword Metrics.

## Compatibility rule

Existing historical `search-metrics.json` and `serp-analysis.json` artifacts are not silently reinterpreted. Cached artifacts may remain in their historical shape; newly fetched provider responses must satisfy the new provider contracts.

## Deliberately not implemented in P1

- Brave Search provider
- Google Ads provider
- production provider switch to Brave/Google Ads
- production Mock prohibition/credential guards
- Real provider E2E
- DataForSEO removal

Those belong to P2–P7.

## Verification gate

P1 closes only after:

1. provider contract tests pass;
2. provider-specific normalization/error tests pass;
3. Research/SERP integration tests pass;
4. full project regression passes in CI;
5. no unintended downstream contract changes are detected.

**P1 state before CI:** implementation-complete, verification-pending.
