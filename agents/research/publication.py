from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA_VERSION="1.0"; METHOD_VERSION="v1"

def _id(payload: dict[str, Any]) -> str:
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    return "pub_"+hashlib.sha256(raw.encode()).hexdigest()[:16]

def build_publication_gate(*, article_draft: dict[str,Any], seo_validation: dict[str,Any], editorial_review: dict[str,Any]) -> dict[str,Any]:
    if article_draft.get("lifecycle_stage") != "draft_ready": raise ValueError("Publication requires a draft_ready Article Draft")
    if seo_validation.get("lifecycle_stage") != "seo_validation_ready": raise ValueError("Publication requires an seo_validation_ready SEO Validation")
    if editorial_review.get("lifecycle_stage") != "editorial_review_ready": raise ValueError("Publication requires an editorial_review_ready Editorial Review")
    keys=("draft_id","brief_id","report_id","decision_id","strategy_id")
    ids={k:str(article_draft.get(k,"")).strip() for k in keys}
    if not all(ids.values()): raise ValueError("Publication requires complete draft lineage")
    if str(seo_validation.get("draft_id","")) != ids["draft_id"] or str(editorial_review.get("draft_id","")) != ids["draft_id"]: raise ValueError("Publication draft lineage mismatch")
    for k in keys[1:]:
        if str(seo_validation.get(k,"")) != ids[k] or str(editorial_review.get(k,"")) != ids[k]: raise ValueError(f"Publication {k} lineage mismatch")
    seo_ok=seo_validation.get("outcome")=="passed"
    editorial_ok=editorial_review.get("outcome")=="approved"
    refs=list(dict.fromkeys(str(x).strip() for x in article_draft.get("evidence_refs",[]) if str(x).strip()))
    if not refs: raise ValueError("Publication requires explicit evidence_refs")
    gate="allowed" if seo_ok and editorial_ok else "blocked"
    payload={"gate_status":gate,"publication_status":"ready" if gate=="allowed" else "blocked","evidence_refs":refs}
    return {"publication_id":_id({**ids,"seo_validation_id":seo_validation.get("seo_validation_id"),"review_id":editorial_review.get("review_id"),**payload}),**ids,"seo_strategy_id":str(seo_validation.get("seo_strategy_id","")),"seo_validation_id":str(seo_validation.get("seo_validation_id","")),"review_id":str(editorial_review.get("review_id","")),"schema_version":SCHEMA_VERSION,"lifecycle_stage":"publication_ready",**payload,"audit":{"method":"seo_and_editorial_publication_gate","version":METHOD_VERSION,"validation_status":"validated"}}
