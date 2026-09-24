# IRL AI Core — P0 Contract & Dependency Audit

**Work Plan:** IRL AI Core — DataForSEO Replacement Work Plan v1.0  
**Phase:** P0 — Contract & Dependency Audit  
**Date:** 2026-09-24  
**Target branch:** `feat/evidence-quality-engine-integration-v1`  
**Verified branch commit:** `56c321ee9b02d732c0d7c2d6cc0dddef8f1018bb`  
**main baseline:** `ed605eef7b6cfdd11f5c40ceda7dcf3f21eac5a7`

## 1. P0 decision

**Status: CLOSED / READY FOR P1**

The audit establishes the dependency map, contract boundaries, downstream impact, and required test surface for replacing DataForSEO with:

- **Brave Search API** for SERP / search discovery.
- **Google Ads API** for keyword metrics.

No provider implementation or provider-boundary refactor was performed during P0.

The audit confirms that the current architecture is **not yet ready for a direct provider swap** because SERP and Keyword Metrics still share a single global provider configuration, and several provider-specific assumptions leak into higher layers.

## 2. Repository baseline

The target feature branch is 39 commits ahead of `main` and 0 commits behind it; its merge base is `main`. The verified branch commit is `56c321ee...`.

The relevant provider configuration remains identical on `main` and the target branch:

```python
ACTIVE_PROVIDER = "dataforseo"
BASE_URL = "https://api.dataforseo.com"
LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
LOCATION_CODES = {"US": 2840}
```

There is no Brave provider registration in the active provider factories.

## 3. Dependency map

### 3.1 SERP dependency chain

```
agents/research/agent.py
    |
    +--> connectors.serp.provider.get_provider()
            |
            +--> connectors.serp.config.ACTIVE_PROVIDER
            |
            +--> DataForSEOSERPProvider
                    |
                    +--> BASE_URL / LOGIN / PASSWORD
                    +--> /v3/serp/google/organic/live/advanced
```

The normalized SERP output is consumed by:

```
SERP
 ├─> competitor analysis
 ├─> SERP intent
 ├─> intent alignment
 ├─> SERP strategy signal
 ├─> entity analysis
 ├─> question analysis
 ├─> authority analysis
 └─> research report
```

### 3.2 Keyword Metrics dependency chain

```
agents/research/agent.py
    |
    +--> connectors.keyword_metrics.provider.get_provider()
            |
            +--> connectors.keyword_metrics.config
            |       |
            |       +--> shared ACTIVE_PROVIDER
            |
            +--> DataForSEOKeywordMetricsProvider
                    |
                    +--> BASE_URL / LOGIN / PASSWORD
                    +--> /v3/keywords_data/google_ads/search_volume/live
```

The normalized Metrics output is consumed by:

```
search-metrics
   |
   +--> business analysis
   +--> business evidence
   +--> research report
   +--> downstream recommendation / decision state
```

## 4. Contract audit

### 4.1 SERP contract

Current interface:

- input: `keyword`, `language`, `country`
- output: generic `dict`

Current normalized fields used by downstream code include:

- `keyword`
- `language`
- `country`
- `results[]`
- result `position`
- result `title`
- result `url`
- result `domain`
- result `snippet`

**Required P1 clarification:** `position` must mean **provider order**, not Google rank.

### 4.2 Keyword Metrics contract

Current interface:

- input: `keyword`, `language`, `country`
- output: generic `dict`

Current DataForSEO normalization emits:

- `keyword`
- `search_volume`
- `difficulty`
- `cpc`
- `trend`
- `language`
- `country`

**Contract mismatch discovered:**

`agents/research/analyzers/business.py` reads competition from:

- `competition`
- `keyword_difficulty`

but the DataForSEO provider emits:

- `difficulty`

Therefore the existing provider output does not map cleanly into the downstream competition signal. P1/P3 must define one canonical field rather than preserving accidental aliases.

### 4.3 Schema audit

`shared/schemas/serp-analysis.schema.json` validates only the top-level metadata and that `results` is an array. Result-item structure is not strict.

`shared/schemas/search-metrics.schema.json` is effectively empty:

```json
{
  "properties": {},
  "required": []
}
```

This means the most important provider replacement boundary currently lacks strict schema enforcement.

## 5. Provider coupling findings

### Finding P0-01 — Shared global provider selector

SERP and Keyword Metrics both depend on the same `ACTIVE_PROVIDER`.

**Impact:** setting a future value such as `brave` would not define a valid Keyword Metrics provider; the two capabilities cannot be configured independently.

**Required:** separate provider selectors/capabilities.

Target model:

```
SERP_PROVIDER
    brave | dataforseo | mock

KEYWORD_METRICS_PROVIDER
    google_ads | dataforseo | mock
```

Exact variable names may be finalized in P1, but the semantic separation is mandatory.

### Finding P0-02 — Silent Mock fallback in Keyword Metrics

`keyword_metrics/provider.py` returns `MockKeywordMetricsProvider` for any active provider value that is not `dataforseo`.

**Impact:** an invalid or unavailable production configuration can silently produce fabricated metrics.

**Required:** production must fail closed; Mock must be explicitly selected and never reached by an accidental provider value.

### Finding P0-03 — Provider-specific utility leakage

`agents/research/agent.py` imports `normalize_serp_url` directly from:

```
connectors.serp.providers.dataforseo
```

**Impact:** the orchestration layer has a direct compile-time dependency on a specific vendor implementation.

**Required:** move shared URL normalization to a provider-neutral location or make it part of the SERP normalization contract.

### Finding P0-04 — DataForSEO-specific SERP semantics leak through implementation

The DataForSEO SERP implementation uses the Google Organic live endpoint and maps its `rank_absolute` to the generic field `position`.

**Impact:** future Brave results must not inherit Google-specific rank semantics.

**Required:** canonicalize `position` explicitly as provider order.

### Finding P0-05 — Country input is not fully authoritative in DataForSEO SERP provider

The SERP provider receives `country`, but the request payload currently uses hardcoded `location_code: 2840`.

**Impact:** the input contract suggests country-aware execution while the implementation is effectively fixed to one location code.

**Required:** provider-specific location mapping must be explicit and validated.

### Finding P0-06 — Shared credential/config boundary

The shared connector config owns:

- DataForSEO base URL
- DataForSEO login
- DataForSEO password
- location codes
- active provider

**Impact:** Google Ads and Brave credentials cannot be represented cleanly without introducing more cross-provider conditionals.

**Required:** provider-specific configuration modules or equivalent isolated credential boundaries.

## 6. Downstream impact map

### Directly affected by P1–P3

| Area | Why affected | Expected treatment |
|---|---|---|
| `connectors/config.py` | Global provider + DataForSEO credentials | Split capability configuration |
| `serp/provider.py` | Factory only knows DataForSEO/Mock | Add Brave registration + fail-closed behavior |
| `serp/providers/dataforseo.py` | Vendor-specific implementation | Retain only as optional legacy provider during migration |
| `keyword_metrics/provider.py` | Shared provider selector + silent Mock fallback | Independent provider selection + explicit failure |
| `keyword_metrics/providers/dataforseo.py` | Vendor-specific metrics mapping | Retain as optional legacy provider; canonicalize metrics |
| `agents/research/agent.py` | Direct provider calls + DataForSEO URL utility import | Remove vendor leakage; preserve artifact behavior |
| `business.py` | Consumes keyword metrics | Align with canonical Metrics contract |
| SERP analyzers | Consume `position/title/url/domain/snippet` | Preserve normalized fields; no Google-rank semantics |
| `serp-analysis.schema.json` | Weak result validation | Strengthen normalized result contract |
| `search-metrics.schema.json` | No meaningful validation | Define strict canonical Metrics contract |

### Indirectly affected; behavior must remain stable

- `competitor.py`
- `authority.py`
- `entity.py`
- `question.py`
- `serp_intent.py`
- `intent_alignment.py`
- `serp_strategy_signal.py`
- `report.py`
- evidence builders consuming SERP/metrics artifacts

These components should not be redesigned in the replacement work; they should continue to consume stable normalized artifacts.

### Explicitly outside the replacement scope

- Source Corpus architecture
- Safe Source Acquisition
- Passage-Bound Evidence
- Canonical Evidence lineage
- Evidence Quality / Section Readiness rules
- Article Writer / OpenAI boundary
- WordPress publishing policy

They are protected by regression rather than refactored as part of provider replacement.

## 7. Test impact map

The existing project history shows established coverage around:

- SERP URL normalization
- SERP intent analysis
- SERP intent evidence
- research report E2E
- core research-domain E2E
- downstream research/content lifecycle integration

P1–P3 must add or strengthen the following test families:

### Common Contract Tests

1. SERP provider input/output contract.
2. Keyword Metrics provider input/output contract.
3. Provider capability declarations.
4. Provider provenance.
5. Deterministic normalization.

### Brave-specific Tests

1. query mapping
2. country mapping
3. language mapping
4. freshness handling
5. pagination
6. response normalization
7. URL normalization
8. malformed response handling
9. authentication failures
10. rate-limit/network failures
11. explicit provider-order semantics

### Google Ads-specific Tests

1. authentication boundary
2. customer/location/language mapping
3. keyword metrics normalization
4. historical metrics mapping
5. keyword ideas mapping if exposed
6. batching
7. rate-limit handling
8. unsupported-field behavior
9. malformed response handling

### Negative Tests

1. unknown provider must fail.
2. production Metrics must never silently become Mock.
3. Brave `position` must never be converted into a Google rank.
4. missing credentials must fail explicitly.
5. unsupported capability must not produce fake values.
6. provider-specific metadata must not leak into unrelated contracts.

### Regression Tests

Full project regression remains mandatory after the boundary refactor and after each provider integration gate.

## 8. Operational findings

### Cached artifact behavior

`agents/research/agent.py` reuses existing:

- `search-metrics.json`
- `serp-analysis.json`

when present.

This behavior is valid for reproducibility, but real E2E must explicitly control whether artifacts are reused or refreshed. Provider replacement must not make a stale DataForSEO artifact look like a fresh Brave/Google Ads result.

### CI

Current CI runs the generic pytest suite and does not expose production provider credentials.

This is appropriate for ordinary CI. Real provider E2E should remain a separate controlled verification path and must never require secrets to be committed into CI artifacts or logs.

### Secrets

The repository `.gitignore` currently excludes only Python cache patterns. It does not explicitly exclude local environment files.

Before real credentials are exercised as part of the replacement, environment-file handling must be hardened so credential files cannot be accidentally committed.

## 9. P0 contract matrix

| Contract | Current state | P0 finding | P1 action |
|---|---|---|---|
| SERPProvider | Exists | Generic dict only | Stabilize normalized contract |
| KeywordMetricsProvider | Exists | Generic dict only | Stabilize normalized contract |
| Provider selection | One global selector | Coupled | Split by capability |
| SERP normalization | Exists | Vendor utility leaks upward | Make provider-neutral |
| Metrics normalization | Exists | `difficulty` mismatch | Canonicalize field names |
| SERP provenance | Partial | Provider class only in one higher layer | Add explicit normalized provenance |
| Capability declaration | None | Unsupported fields can be ambiguous | Define capability matrix |
| Error contract | Basic `raise_for_status` | Not normalized | Define typed/normalized errors |
| Production Mock policy | Unsafe | Silent fallback in Metrics | Fail closed |
| Schemas | Weak | Metrics schema empty | Strengthen both schemas |
| Country mapping | Partial | SERP hardcodes 2840 | Explicit mapping contract |
| Cache/reuse | Present | Can mask provider changes | Make E2E refresh semantics explicit |

## 10. P0 decision map for P1

P1 can start without further discovery.

### Mandatory sequence

```
P1
 ├─ 1. Freeze canonical SERP contract
 ├─ 2. Freeze canonical Keyword Metrics contract
 ├─ 3. Split capability provider configuration
 ├─ 4. Remove provider-specific utility leakage
 ├─ 5. Define provenance + capability + error semantics
 ├─ 6. Strengthen provider-facing schemas
 └─ 7. Add contract/negative tests
```

Only after P1 is green:

```
P2 → Brave Provider
P3 → Google Ads Provider
P4 → Production configuration guards
P5 → Full regression
P6 → Real E2E
P7 → DataForSEO removal / optionalization
```

## 11. P0 closure criteria

All P0 deliverables are now defined:

- [x] Dependency map
- [x] Contract inventory
- [x] Provider coupling findings
- [x] Downstream impact map
- [x] Test impact map
- [x] P1 decision map
- [x] No provider refactor started before audit closure
- [x] No shell.cloud execution required for P0

**P0 result:** `decision-map-ready`

The project may proceed to **P1 — Provider Boundary Refactor** without guessing about the affected architecture.
