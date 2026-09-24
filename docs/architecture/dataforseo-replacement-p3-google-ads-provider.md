# IRL AI Core — P3 Google Ads Provider

**Phase:** P3 — Google Ads Provider  
**Status:** implementation complete, pending local regression and PR review

## Scope

P3 adds Google Ads as the real Keyword Metrics provider behind the P1 capability-specific boundary.

Included:
- Google Ads REST connector for historical keyword metrics;
- OAuth refresh-token authentication boundary;
- developer-token and customer-context configuration;
- country/language resource-name mapping;
- canonical normalization to search volume, competition index, CPC, and historical trend;
- fail-closed handling when a required metric is unavailable;
- batch requests with the Google Ads historical-metrics maximum of 10,000 keywords per request;
- normalized authentication, network, rate-limit, and response errors;
- provider-specific tests for mapping, authentication, normalization, missing metrics, errors, and batching.

## API boundary

The provider calls:

`POST /v25/customers/{customer_id}:generateKeywordHistoricalMetrics`

The current Google Ads API release family is v25; Google published v25.2 on September 23, 2026. The implementation therefore targets the v25 major REST endpoint by default and keeps the version configurable. Google documents `GenerateKeywordHistoricalMetrics` for historical search volume, competition, competition index, average CPC, and monthly search volumes.

Authentication requires OAuth 2.0 credentials plus a developer token. When access is through a manager account, `login-customer-id` is sent as the request context.

## Normalization

Google Ads values are normalized as follows:

- `avgMonthlySearches` → `search_volume`
- `competitionIndex` → canonical `competition` in the existing 0–100 contract
- `averageCpcMicros` → `cpc` in major currency units
- `monthlySearchVolumes[]` → `trend` entries with year, month, and search volume

No Google-specific ranking semantics are introduced. This provider is Keyword Metrics only.

Google may return no competition index when insufficient data exists. P3 does not substitute zero or another synthetic value; the provider fails closed with a normalized provider error.

## Supported mapping

The application currently declares explicit mappings only for:

- country `US` → geo target constant `2840`
- language `en` → language constant `1000`

Unsupported mappings fail closed rather than guessing.

## Credentials and environment

Expected environment variables:

- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_CUSTOMER_ID`
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (optional)
- `GOOGLE_ADS_API_VERSION` (default `v25`)
- `GOOGLE_ADS_BASE_URL`
- `GOOGLE_ADS_TOKEN_URL`
- `GOOGLE_ADS_TIMEOUT_SECONDS`
- `GOOGLE_ADS_MAX_KEYWORDS_PER_REQUEST` (default `10000`)

Secrets must not enter Git, fixtures, logs, or snapshots.

## Batch behavior

`get_metrics()` preserves the existing single-keyword provider contract.

`get_metrics_batch()` is an additive provider capability for higher-throughput research workloads. The implementation chunks input keywords according to the configured maximum and normalizes each returned Google result.

Google's Keyword Planning service is subject to a 1-request-per-second-per-CID limit. P3 does not silently retry or downgrade to Mock when this limit is reached; a normalized rate-limit error is returned.

## Explicit non-scope

P3 does not:
- change SERP behavior or Brave semantics;
- switch production defaults away from DataForSEO;
- remove Mock;
- remove DataForSEO;
- execute credentialed Real E2E;
- enable WordPress publishing;
- implement separate keyword-idea generation or forecast metrics.

Those remain governed by the later stages of the DataForSEO Replacement Work Plan.

## Pipeline invariant

`Google Ads Keyword Metrics → normalized Keyword Metrics contract → Research → Evidence → Readiness → Article Draft`

Downstream Research/Evidence/Writer stages are not redesigned in P3.
