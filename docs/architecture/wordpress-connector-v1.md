# IRL AI Core — WordPress Connector v1

## 1. Audit

Phase 5 is the first production phase that crosses the Core/CMS integration boundary.

The repository already contains `agents/research/wordpress_draft_delivery_client.py`. It is retained as the low-level transport/authentication implementation because it already enforces the critical Draft-only behavior: the request payload must contain `status=draft`, and a remote response must confirm `status=draft` before delivery is accepted.

Phase 5 therefore adds a formal Connector contract and a thin mapping/delivery engine. It does not create a second HTTP client or a second publishing mechanism.

## 2. Contract

```text
Article Production Contract
        ↓
WordPress Connector Contract
        ↓
Existing WordPress Draft Delivery Client
        ↓
WordPress REST API
        ↓
WordPress Draft
```

The Connector contract is an integration record. It preserves `production_id`, records the exact Draft request payload, and records the remote WordPress identifier and status after delivery.

Credentials are intentionally absent from the contract. They enter only through `WordPressConnection.from_env()` at runtime.

## 3. Final Fields

```text
connector_id
schema_version
lifecycle_stage
platform
operation
source.production_id
request_payload.title
request_payload.content
request_payload.status
response.delivery_status
response.post_id
response.edit_url
response.remote_status
response.error
audit
```

## 4. Final Enums

- `schema_version`: `1.0`
- `lifecycle_stage`: `wordpress_connector_ready`
- `platform`: `wordpress`
- `operation`: `create_draft`
- `request_payload.status`: `draft`
- `response.delivery_status`: `delivered | failed`

## 5. Invariants

1. Input must be `production_ready`.
2. Publication mode must be `wordpress_draft`.
3. `publish` must be `false`.
4. Human approval must remain required.
5. The Connector cannot request WordPress publication.
6. The source production ID is preserved.
7. WordPress post IDs are remote identifiers and never replace Core lineage IDs.
8. Successful delivery requires a remote Draft status and a post ID.
9. Credentials never appear in the Connector contract.
10. Delivery errors do not mutate the source production package.
11. WordPress final publication remains a human-controlled action.

## 6. Mapping

The Core Article Draft title maps to WordPress `title`.

Article Draft sections are rendered into the WordPress `content` payload using an HTML `h2` for each section heading followed by its existing section body. No new content generation occurs in the Connector.

Evidence, claims, quality, and lineage remain owned by the Core production package; the Connector only carries the production identifier needed to trace the hand-off.

## 7. Authentication and Transport

Runtime configuration uses:

- `WORDPRESS_BASE_URL`
- `WORDPRESS_USERNAME`
- `WORDPRESS_APPLICATION_PASSWORD`

These values are not stored in Git and are not serialized into the Connector contract.

The Connector delegates the actual HTTP request to the existing Draft Delivery Client.

## 8. Publication Safety

Phase 5 supports **Draft creation only**.

The engine rejects invalid publication intent before network transport. The underlying client also rejects non-Draft payloads and rejects a remote response that is not Draft.

No `publish` operation is implemented.

## 9. Non-Goals

- automatic publishing
- WordPress media upload pipeline beyond the existing Draft delivery boundary
- categories/taxonomies not represented by the current Core contract
- scheduling
- dashboard
- database selection
- retry policy redesign
- a second HTTP client
- new dependencies
- changes to the Production Orchestrator or Production Job state machine

## 10. Phase 5 Completion Criteria

- Connector contract locked.
- JSON Schema validates the contract structure.
- Mapping engine converts validated production output into a Draft request.
- Existing transport/authentication client is reused.
- Unit tests cover boundary rejection, Draft-only behavior, deterministic connector ID, remote validation, and credential exclusion.
- Targeted and full regression pass in GitHub Codespaces.
- `git diff --check` clean.
- Working tree clean.
- PR reviewed and squash-merged only after regression is confirmed.
