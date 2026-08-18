from __future__ import annotations
import hashlib,json
from typing import Any

SCHEMA_VERSION="1.0"; METHOD_VERSION="v1"

def _id(payload:dict[str,Any])->str:
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    return "publisher_"+hashlib.sha256(raw.encode()).hexdigest()[:16]

def build_publisher(*, article_draft:dict[str,Any], publication:dict[str,Any])->dict[str,Any]:
    """Prepare a deterministic dry-run publication result. No external publish occurs."""
    if article_draft.get("lifecycle_stage")!="draft_ready": raise ValueError("Publisher requires a draft_ready Article Draft")
    if publication.get("lifecycle_stage")!="publication_ready": raise ValueError("Publisher requires a publication_ready Publication")
    if publication.get("gate_status")!="allowed" or publication.get("publication_status")!="ready": raise ValueError("Publisher requires an allowed Publication Gate")
    keys=("draft_id","brief_id","report_id","decision_id","strategy_id")
    ids={k:str(article_draft.get(k,"")).strip() for k in keys}
    if not all(ids.values()): raise ValueError("Publisher requires complete Article Draft lineage")
    for k in keys:
        if str(publication.get(k,""))!=ids[k]: raise ValueError(f"Publisher {k} lineage mismatch")
    refs=list(dict.fromkeys(str(x).strip() for x in article_draft.get("evidence_refs",[]) if str(x).strip()))
    if not refs: raise ValueError("Publisher requires explicit evidence_refs")
    payload={"publication_id":str(publication.get("publication_id","")),"publish_status":"ready","execution_mode":"dry_run","evidence_refs":refs}
    return {"publisher_id":_id({**ids,**payload}),**payload,**ids,"seo_strategy_id":str(publication.get("seo_strategy_id","")),"seo_validation_id":str(publication.get("seo_validation_id","")),"review_id":str(publication.get("review_id","")),"schema_version":SCHEMA_VERSION,"lifecycle_stage":"publisher_ready","audit":{"method":"publication_gate_publisher_dry_run","version":METHOD_VERSION,"validation_status":"validated"}}
