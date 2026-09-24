# IRL AI Core — P4 Production Configuration

**Phase:** P4 — Production Configuration  
**Status:** implementation complete, pending local regression and PR validation

## Goal

P4 makes the DataForSEO replacement operational in production without silently falling back to Mock or legacy DataForSEO.

The production policy is:

- SERP/Search → **Brave**
- Keyword Metrics → **Google Ads**

The legacy DataForSEO and Mock providers remain available for explicit non-production use and compatibility tests.

## Environment contract

Production is enabled by:

`IRL_ENVIRONMENT=production`

Provider overrides remain capability-specific:

- `IRL_SERP_PROVIDER`
- `IRL_KEYWORD_METRICS_PROVIDER`

When `IRL_ENVIRONMENT=production`, these overrides cannot select `mock` or `dataforseo`.

The defaults are now:

- `IRL_SERP_PROVIDER` → `brave`
- `IRL_KEYWORD_METRICS_PROVIDER` → `google_ads`

## Production guards

A production provider selection is rejected when it is not the approved provider for the capability.

Examples:

- production SERP + `mock` → configuration error
- production SERP + `dataforseo` → configuration error
- production Keyword Metrics + `mock` → configuration error
- production Keyword Metrics + `dataforseo` → configuration error

There is no automatic fallback.

## Credential failure policy

The real providers fail explicitly when required credentials are absent.

### Brave
Required:
- `BRAVE_SEARCH_API_KEY`

### Google Ads
Required for the live OAuth path:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_CUSTOMER_ID`

Optional manager-account context:
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`

Credential values must remain outside Git, fixtures, snapshots, and logs.

## CI contract

The CI workflow now runs a dedicated production-configuration guard suite before the full pytest suite.

The guard suite verifies:

- approved defaults;
- rejection of Mock and DataForSEO in production;
- explicit Brave credential failure;
- explicit Google Ads credential failure.

The full test suite remains the final regression gate.

## Non-production behavior

Outside `IRL_ENVIRONMENT=production`, legacy providers may still be selected explicitly for migration compatibility and contract tests.

P4 therefore changes operational production behavior without prematurely deleting the legacy implementations. Their final removal remains governed by P7.

## Scope boundary

P4 does not:

- run credentialed Real E2E;
- remove DataForSEO code;
- remove Mock code;
- change the SERP/Keyword Metrics contracts;
- modify Source Corpus, Evidence, Readiness, Writer, or WordPress publishing policy.

Those remain controlled by the later plan stages.

## Closure conditions addressed by P4

P4 directly addresses the production requirement that DataForSEO and Mock are no longer silent operational fallbacks and that missing production credentials produce explicit failures.
