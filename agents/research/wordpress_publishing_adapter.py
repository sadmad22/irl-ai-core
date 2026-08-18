from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA_VERSION="1.0"; METHOD_VERSION="v1"

def _id(payload:dict[str,Any])->str:
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    return "wp_adapter_"+hashlib.sha256(raw.encode()).hexdigest()[:16]

def build_wordpress_publishing_request(*, publisher:dict[str,Any], article_draft:dict[str,Any], execution_mode:str="dry_run") -> dict[str,Any]:
    """Prepare a WordPress REST API request. This engine never performs network I/O."""
    if publisher.get("lifecycle_stage")!="publisher_ready": raise ValueError("WordPress Adapter requires a publisher_ready Publisher result")
    if publisher.get("publish_status")!="ready": raise ValueError("WordPress Adapter requires a ready Publisher result")
    if execution_mode not in {"dry_run","live"}: raise ValueError("execution_mode must be dry_run or live")
    if article_draft.get("lifecycle_stage")!="draft_ready": raise ValueError("WordPress Adapter requires a draft_ready Article Draft")
    draft_id=str(article_draft.get("draft_id","")).strip()
    if not draft_id or str(publisher.get("draft_id",""))!=draft_id: raise ValueError("WordPress Adapter draft lineage mismatch")
    refs=list(dict.fromkeys(str(x).strip() for x in article_draft.get("evidence_refs",[]) if str(x).strip()))
    if not refs: raise ValueError("WordPress Adapter requires explicit evidence_refs")
    title=str(article_draft.get("title","")).strip()
    sections=article_draft.get("sections",[]) or []
    content_parts=[]
    for section in sections:
        if not isinstance(section,dict): continue
        heading=str(section.get("heading","")).strip(); body=str(section.get("body","")).strip()
        if heading: content_parts.append(f"<h2>{heading}</h2>")
        if body: content_parts.append(body)
    content="\n".join(content_parts).strip()
    if not title or not content: raise ValueError("WordPress Adapter requires draft title and content")
    payload={"title":title,"content":content,"status":"publish" if execution_mode=="live" else "draft"}
    if str(article_draft.get("slug","")).strip(): payload["slug"]=str(article_draft["slug"]).strip()
    if str(article_draft.get("excerpt","")).strip(): payload["excerpt"]=str(article_draft["excerpt"]).strip()
    identity={"publisher_id":str(publisher.get("publisher_id","")),"publication_id":str(publisher.get("publication_id","")),"draft_id":draft_id,"execution_mode":execution_mode,"request_payload":payload}
    return {"adapter_id":_id(identity),**identity,"platform":"wordpress","api_version":"v2","endpoint":"/wp-json/wp/v2/posts","method":"POST","lifecycle_stage":"wordpress_publish_ready","publish_status":"ready","evidence_refs":refs,"audit":{"method":"wordpress_rest_publish_adapter","version":METHOD_VERSION,"validation_status":"validated"}}

# Backward-compatible singular-name alias for callers created during the adapter rollout.
build_wordpress_publish_request = build_wordpress_publishing_request
