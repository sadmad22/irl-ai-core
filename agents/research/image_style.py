from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
_BRAND = "Insurance Review Lab"
_COLORS = {"deep_navy":"#0F172A","modern_blue":"#2563EB","cyan_accent":"#06B6D4","white":"#FFFFFF"}
_LANGUAGE = ["professional","editorial","research-oriented","clean","modern","trustworthy"]
_COMPOSITION = ["clear focal point","structured composition","generous whitespace","restrained visual hierarchy"]
_ILLUSTRATION = ["premium editorial illustration","clean geometric elements","subtle analytical/data motifs"]
_RESTRICTIONS = ["no watermark","no unnecessary text","no logos","no visual clutter","no off-brand colors","no misleading imagery"]

def _clean(v: Any) -> str: return v.strip() if isinstance(v,str) else ""

def build_image_style(*, ai_image_spec: dict[str,Any]) -> dict[str,Any]:
    if ai_image_spec.get("lifecycle_stage") != "ai_image_spec_ready":
        raise ValueError("Image Style requires a ai_image_spec_ready AI Image Specification")
    fields=("brief_id","report_id","decision_id","strategy_id","config_id","draft_id","image_spec_id")
    lineage={f:_clean(ai_image_spec.get(f)) for f in fields}
    missing=next((f for f,v in lineage.items() if not v),None)
    if missing: raise ValueError(f"Image Style requires {missing} in AI Image Specification")
    images=ai_image_spec.get("images")
    if not isinstance(images,list) or not images: raise ValueError("AI Image Specification.images must be a non-empty list")
    styled=[]
    for image in images:
        if not isinstance(image,dict): raise ValueError("AI Image Specification.images must contain objects")
        image_id=_clean(image.get("image_id")); heading=_clean(image.get("section_heading")); prompt=_clean(image.get("prompt")); image_type=_clean(image.get("image_type")); idx=image.get("section_index")
        if not image_id or not heading or not prompt or not image_type: raise ValueError("Each AI Image Specification image requires image_id, image_type, section_heading, and prompt")
        if not isinstance(idx,int) or isinstance(idx,bool) or idx<0: raise ValueError("Each AI Image Specification image requires a valid section_index")
        if image_type not in {"hero","section","infographic","comparison"}: raise ValueError("AI Image Specification contains an unsupported image_type")
        styled.append({"image_id":image_id,"section_index":idx,"section_heading":heading,"image_type":image_type,"styled_prompt":f"{prompt} Apply {_BRAND} visual style: {', '.join(_LANGUAGE)}. Use the brand palette {', '.join(_COLORS.values())}. Composition: {', '.join(_COMPOSITION)}. Illustration direction: {', '.join(_ILLUSTRATION)}. Restrictions: {', '.join(_RESTRICTIONS)}."})
    style={"brand":_BRAND,"color_palette":copy.deepcopy(_COLORS),"visual_language":list(_LANGUAGE),"composition":list(_COMPOSITION),"illustration_direction":list(_ILLUSTRATION),"restrictions":list(_RESTRICTIONS)}
    seed=json.dumps({**lineage,"visual_style":style,"styled_images":styled},sort_keys=True,separators=(",",":"))
    return {"image_style_id":f"imgstyle_{hashlib.sha256(seed.encode()).hexdigest()[:16]}",**lineage,"schema_version":SCHEMA_VERSION,"lifecycle_stage":"image_style_ready","visual_style":style,"styled_images":copy.deepcopy(styled),"constraints":{"network_access":False,"provider_call":False,"image_analysis_call":False,"media_strategy_included":False,"source_mutation":False},"audit":{"method":"ai_image_spec_to_brand_visual_style","version":METHOD_VERSION,"validation_status":"validated"}}
