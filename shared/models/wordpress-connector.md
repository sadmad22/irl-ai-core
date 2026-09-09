# IRL AI Core — WordPress Connector v1

## Audit

The repository already contains `agents/research/wordpress_draft_delivery_client.py`, which owns the existing HTTP transport, Basic Application Password authentication, Draft-only enforcement, remote post ID extraction, and delivery response. Phase 5 must formalize that integration boundary rather than replace it.

The existing client is therefore reused as the transport implementation. This phase adds the Connector contract and a thin engine that maps the validated Article Production Contract into the existing WordPress Draft Delivery shape.

## Contract

The WordPress Connector accepts only a validated `ArticleProduction` envelope and produces a connector delivery record. Credentials and transport configuration remain outside the contract.

Required connector fields:

- `connector_id`
- `schema_version`
- `lifecycle_stage`
- `platform`
- `operation`
- `source`
- `request_payload`
- `response`
- `audit`

## Final enums

- `schema_version`: exactly `1.0`
- `lifecycle_stage`: `wordpress_connector_ready`
- `platform`: `wordpress`
- `operation`: `create_draft`
- `request_payload.status`: exactly `draft`
- `response.delivery_status`: `delivered` or `failed`

## Invariants

1. Only an Article Production Contract with `lifecycle_stage=production_ready` may enter the Connector.
2. The production publication intent must be `mode=wordpress_draft`.
3. `publish` must be `false`.
4. `human_approval_required` must be `true`.
5. The Connector never sends `status=publish`.
6. WordPress credentials are never represented in the connector contract.
7. The source `production_id` is preserved in the connector lineage.
8. The WordPress post ID belongs to the Connector response, not the Core production contract.
9. A successful remote response must confirm `status=draft` and include a post ID.
10. Delivery errors must not mutate the source Article Production Contract.
11. This phase creates/updates WordPress Drafts only; it does not publish.
12. The existing HTTP client remains the transport/authentication implementation.

## Ownership

**IRL AI Core:** production readiness, content, quality, lineage, and publication intent.

**WordPress Connector:** authentication boundary, HTTP transport invocation, field mapping, Draft creation, remote identifiers, and delivery result.

**WordPress/Hostinger:** CMS persistence, human review, and final publication.
