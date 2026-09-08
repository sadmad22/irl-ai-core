# IRL AI Core — Article Production Contract v1

Version: 1.0  
Status: **Contract Locked for Phase 2**

## 1. Purpose

This contract defines the exact Core-to-WordPress hand-off for a validated article production result.

The contract is intentionally an integration envelope. It does not replace the existing ResearchReport, Content Brief, Article Draft, Article Draft Quality, image, linking, optimization, or other capability contracts.

## 2. Contract Boundary

```text
Existing Core artifacts
        ↓
Article Production Contract
        ↓
Future WordPress Connector
```

Only a production result that satisfies this contract may cross the WordPress boundary.

## 3. Top-Level Structure

```text
ArticleProduction
├── production_id
├── schema_version
├── lifecycle_stage
├── lineage
├── article
├── quality
├── publication
└── audit
```

### `production_id`
Deterministic identifier with the form `production_<16 lowercase hex characters>`.

### `schema_version`
Exactly `1.0`.

### `lifecycle_stage`
Exactly `production_ready`.

## 4. Lineage Contract

The following six identifiers are mandatory:

```text
report_id
 decision_id
 strategy_id
 brief_id
 draft_id
 quality_id
```

Optional identifiers may be attached only when the corresponding upstream artifact exists:

```text
config_id
semantic_id
optimization_id
image_spec_id
alt_text_id
external_links_id
internal_links_id
news_id
```

No identifier may be invented by the production envelope.

## 5. Article Contract

`article` embeds the existing **Article Draft v1** contract unchanged.

The production contract therefore reuses the existing article fields rather than creating a second article representation.

The minimum article lineage invariants are:

```text
article.draft_id   == lineage.draft_id
article.brief_id   == lineage.brief_id
article.report_id  == lineage.report_id
article.decision_id == lineage.decision_id
article.strategy_id == lineage.strategy_id
```

## 6. Quality Contract

`quality` embeds the existing **Article Draft Quality v1** contract unchanged.

Production readiness requires:

```text
quality.lifecycle_stage == article_draft_quality_ready
quality.outcome == passed
quality.audit.validation_status == validated
```

And:

```text
quality.quality_id == lineage.quality_id
quality.draft_id  == lineage.draft_id
```

## 7. Publication Contract

Initial production is strictly controlled WordPress Draft delivery:

```json
{
  "mode": "wordpress_draft",
  "publish": false,
  "human_approval_required": true
}
```

The contract contains no WordPress credentials, tokens, passwords, or transport configuration.

## 8. Invariants

A valid production package must satisfy all of the following:

1. Required top-level fields exist.
2. Schema version is `1.0`.
3. Lifecycle stage is `production_ready`.
4. All mandatory lineage identifiers are non-empty.
5. Article and quality lineage match the envelope lineage.
6. Quality outcome is `passed`.
7. Quality validation status is `validated`.
8. Publication mode is `wordpress_draft`.
9. `publish` is `false`.
10. `human_approval_required` is `true`.
11. Production ID is deterministic for the same draft/quality pair.
12. No credentials are represented in the contract.
13. Historical ResearchReport data is not mutated by this contract.

## 9. Ownership

**IRL AI Core owns:** production readiness, validation, lineage, and content-production decisions.

**WordPress Connector owns:** authentication, transport, field mapping, draft creation/update, media transfer, and WordPress identifiers.

**WordPress/Hostinger owns:** CMS persistence, review UI, and final publication.

## 10. Explicit Non-Goals

Phase 2 does not implement:

- Production Job State
- retry/resume orchestration
- WordPress API transport
- WordPress authentication
- automatic publishing
- dashboard or scheduling
- a second content-generation engine
- duplicate capability contracts

Those belong to later production phases.

## 11. Next Phase

After this contract is validated, implementation proceeds to **Phase 3 — Production Orchestrator**, which will consume this contract rather than redefine it.
