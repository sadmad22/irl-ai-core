from __future__ import annotations
import hashlib, json
from typing import Any
from .wordpress_publishing_adapter import build_wordpress_publishing_request

SCHEMA_VERSION="1.0"; METHOD_VERSION="v1"

def _id(payload: dict[str, Any]) -> str:
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    return "wp_draft_"+hashlib.sha256(raw.encode()).hexdigest()[:16]

def build_wordpress_draft_delivery(*, publisher: dict[str,Any], article_draft: dict[str,Any], execution_mode: str="dry_run") -> dict[str,Any]:
    """Prepare a WordPress post that is unconditionally a Draft. Never performs network I/O."""
    if execution_mode not in {"dry_run","live"}: raise ValueError("execution_mode must be dry_run or live")
    # Always call the underlying adapter in dry_run mode: the delivery contract owns the
    # publication status and deliberately provides no path for a caller to request publish.
    adapter=build_wordpress_publishing_request(publisher=publisher,article_draft=article_draft,execution_mode="dry_run")
    payload=dict(adapter["request_payload"])
    payload["status"]="draft"
    identity={"adapter_id":adapter["adapter_id"],"publisher_id":adapter["publisher_id"],"publication_id":adapter["publication_id"],"draft_id":adapter["draft_id"],"execution_mode":execution_mode,"request_payload":payload}
    return {"delivery_id":_id(identity),**identity,"platform":"wordpress","api_version":"v2","endpoint":"/wp-json/wp/v2/posts","method":"POST","lifecycle_stage":"wordpress_draft_ready","delivery_status":"ready","evidence_refs":adapter["evidence_refs"],"audit":{"method":"wordpress_draft_delivery","version":METHOD_VERSION,"validation_status":"validated"}}
