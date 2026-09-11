from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

from .production_delivery_boundary_engine import validate_production_delivery_boundary
from .wordpress_draft_delivery_client import WordPressConnection, deliver_wordpress_draft

METHOD_VERSION = "v1"
TARGET = "wordpress"
PUBLICATION = {
    "mode": "wordpress_draft",
    "publish": False,
    "human_approval_required": True,
}


class WordPressDeliveryAdapterError(ValueError):
    """Deterministic, fail-closed WordPress adapter error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _adapter_id(boundary: dict[str, Any]) -> str:
    seed = {
        "delivery_id": boundary["delivery_id"],
        "adapter": "wordpress_delivery_adapter_v1",
    }
    raw = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"wp_adapter_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _taxonomy_ids(taxonomy: dict[str, Any], *, live: bool) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {"categories": [], "tags": []}
    for kind in ("categories", "tags"):
        for item in taxonomy[kind]:
            platform_id = item.get("platform_id")
            if platform_id is None:
                if live:
                    raise WordPressDeliveryAdapterError(
                        "TAXONOMY_NOT_RESOLVED",
                        f"Taxonomy {kind} item '{item['name']}' has no platform_id",
                    )
                continue
            if isinstance(platform_id, bool):
                raise WordPressDeliveryAdapterError("TAXONOMY_INVALID", "Resolved taxonomy platform_id is invalid")
            try:
                numeric_id = int(platform_id)
            except (TypeError, ValueError) as exc:
                raise WordPressDeliveryAdapterError(
                    "TAXONOMY_INVALID", "Resolved taxonomy platform_id is not numeric"
                ) from exc
            if numeric_id < 1:
                raise WordPressDeliveryAdapterError("TAXONOMY_INVALID", "Resolved taxonomy platform_id must be positive")
            result[kind].append(numeric_id)
        if kind == "categories" and live and not result[kind]:
            raise WordPressDeliveryAdapterError(
                "TAXONOMY_NOT_RESOLVED", "At least one category must resolve to a WordPress ID"
            )
    return result


def _seo_meta(
    optimization: dict[str, Any],
    *,
    seo_meta_keys: dict[str, str] | None,
    live: bool,
) -> dict[str, str]:
    if not seo_meta_keys:
        if live:
            raise WordPressDeliveryAdapterError(
                "SEO_METADATA_UNSUPPORTED",
                "Explicit WordPress SEO metadata field mapping is required for live delivery",
            )
        return {}

    title_key = str(seo_meta_keys.get("seo_title", "")).strip()
    description_key = str(seo_meta_keys.get("meta_description", "")).strip()
    if not title_key or not description_key:
        raise WordPressDeliveryAdapterError(
            "SEO_METADATA_UNSUPPORTED",
            "Both seo_title and meta_description field mappings are required",
        )

    result = {
        title_key: optimization["seo_title"],
        description_key: optimization["meta_description"],
    }
    if optimization.get("canonical_url"):
        canonical_key = str(seo_meta_keys.get("canonical_url", "")).strip()
        if not canonical_key:
            raise WordPressDeliveryAdapterError(
                "SEO_METADATA_UNSUPPORTED",
                "canonical_url mapping is required when the package provides canonical_url",
            )
        result[canonical_key] = optimization["canonical_url"]
    return result


def _media_for_request(media: list[dict[str, Any]], *, live: bool) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for image in media:
        item = copy.deepcopy(image)
        platform_id = item.get("platform_asset_id")
        if platform_id is not None:
            if isinstance(platform_id, bool):
                raise WordPressDeliveryAdapterError("MEDIA_INVALID", "platform_asset_id is invalid")
            try:
                platform_id = int(platform_id)
            except (TypeError, ValueError) as exc:
                raise WordPressDeliveryAdapterError("MEDIA_INVALID", "platform_asset_id is not numeric") from exc
            if platform_id < 1:
                raise WordPressDeliveryAdapterError("MEDIA_INVALID", "platform_asset_id must be positive")
            item["platform_asset_id"] = platform_id
        elif live and item.get("featured"):
            raise WordPressDeliveryAdapterError(
                "MEDIA_NOT_RESOLVED",
                f"Featured image '{item['image_id']}' must resolve to a WordPress media ID",
            )
        result.append(item)

    featured = [item["platform_asset_id"] for item in result if item.get("featured") and item.get("platform_asset_id")]
    if len(featured) > 1:
        raise WordPressDeliveryAdapterError("MEDIA_INVALID", "Multiple featured media identities are not allowed")
    return result


def build_wordpress_delivery_request(
    *,
    boundary: dict[str, Any],
    execution_mode: str | None = None,
    seo_meta_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a WordPress-specific request from the canonical Delivery Boundary only."""
    candidate = validate_production_delivery_boundary(boundary)
    mode = execution_mode or candidate["execution_mode"]
    if mode not in {"dry_run", "live"} or mode != candidate["execution_mode"]:
        raise WordPressDeliveryAdapterError("INVALID_EXECUTION_MODE", "Execution mode must match the validated boundary")
    if candidate["target"] != TARGET or candidate["publication"] != PUBLICATION:
        raise WordPressDeliveryAdapterError("PUBLICATION_POLICY_VIOLATION", "Only WordPress draft delivery is supported")

    request = candidate["request"]
    media = _media_for_request(request["media"], live=mode == "live")
    taxonomy = _taxonomy_ids(request["taxonomy"], live=mode == "live")
    meta = _seo_meta(request["optimization"], seo_meta_keys=seo_meta_keys, live=mode == "live")

    payload: dict[str, Any] = {
        "title": request["title"],
        "content": request["content"],
        "status": "draft",
    }
    for field in ("slug", "excerpt"):
        if field in request:
            payload[field] = request[field]
    if taxonomy["categories"]:
        payload["categories"] = taxonomy["categories"]
    if taxonomy["tags"]:
        payload["tags"] = taxonomy["tags"]
    if meta:
        payload["meta"] = meta

    featured = [item["platform_asset_id"] for item in media if item.get("featured") and item.get("platform_asset_id")]
    if featured:
        payload["featured_media"] = featured[0]

    return {
        "adapter_id": _adapter_id(candidate),
        "delivery_id": candidate["delivery_id"],
        "package_id": candidate["package_id"],
        "platform": TARGET,
        "execution_mode": mode,
        "lifecycle_stage": "request_ready",
        "request_payload": payload,
        "media": media,
        "links": copy.deepcopy(request["links"]),
        "optimization": copy.deepcopy(request["optimization"]),
        "taxonomy": copy.deepcopy(request["taxonomy"]),
        "audit": {
            "method": "wordpress_delivery_adapter",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }


def deliver_wordpress_delivery_boundary(
    *,
    boundary: dict[str, Any],
    connection: WordPressConnection | None = None,
    transport: Callable[..., Any] | None = None,
    seo_meta_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Deliver a canonical Delivery Boundary as a WordPress Draft and stop at human review."""
    candidate = validate_production_delivery_boundary(boundary)
    adapter = build_wordpress_delivery_request(
        boundary=candidate,
        seo_meta_keys=seo_meta_keys,
    )
    if candidate["execution_mode"] == "dry_run":
        return adapter

    delivery = {
        "delivery_id": candidate["delivery_id"],
        "platform": TARGET,
        "lifecycle_stage": "wordpress_draft_ready",
        "request_payload": adapter["request_payload"],
        "evidence_refs": [candidate["package_id"]],
    }
    result = deliver_wordpress_draft(
        delivery=delivery,
        connection=connection,
        transport=transport,
    )

    delivered = copy.deepcopy(candidate)
    delivered["adapter_id"] = adapter["adapter_id"]
    delivered["lifecycle_stage"] = "human_review"
    delivered["delivery_status"] = "delivered"
    delivered["response"] = {
        "platform_post_id": result["post_id"],
        "remote_status": "draft",
        "edit_url": result["edit_url"],
    }
    return delivered


# Explicit alias used by the connector integration layer.
build_wordpress_adapter_request = build_wordpress_delivery_request
