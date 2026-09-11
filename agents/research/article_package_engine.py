from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGES = ("production_ready", "package_assembled", "package_validated", "delivery_ready")
_REQUIRED_ARTIFACTS = (
    "article_draft", "quality", "claim_audit", "editorial_review",
    "optimization", "media", "linking", "taxonomy", "production_intent",
)
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "article-package.schema.json"


class ArticlePackageEngineError(ValueError):
    """Deterministic, fail-closed Article Package Engine error."""

    def __init__(self, code: str, message: str, details: list[str] | None = None) -> None:
        self.code = code
        self.details = tuple(details or ())
        suffix = f" ({'; '.join(self.details)})" if self.details else ""
        super().__init__(f"{code}: {message}{suffix}")


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArticlePackageEngineError("INVALID_INPUT", f"{name} must be an object")
    return value


def _require_artifacts(artifacts: dict[str, Any]) -> None:
    missing = [name for name in _REQUIRED_ARTIFACTS if name not in artifacts]
    if missing:
        raise ArticlePackageEngineError("MISSING_ARTIFACT", "Required upstream artifact is missing", missing)
    if not isinstance(artifacts.get("lineage"), dict):
        raise ArticlePackageEngineError("INVALID_INPUT", "Explicit production lineage must be an object")


def _ready(artifact: dict[str, Any], expected: str, name: str) -> None:
    if artifact.get("lifecycle_stage") != expected:
        raise ArticlePackageEngineError("UPSTREAM_NOT_READY", f"{name} must be {expected}")


def _lineage(artifacts: dict[str, Any]) -> dict[str, str]:
    draft = _object(artifacts["article_draft"], "article_draft")
    quality = _object(artifacts["quality"], "quality")
    result: dict[str, str] = {}
    mismatches: list[str] = []
    for key in ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id"):
        left, right = _clean(draft.get(key)), _clean(quality.get(key))
        if not left or not right or left != right:
            mismatches.append(key if left and right else f"{key}:missing")
        else:
            result[key] = left
    quality_id = _clean(quality.get("quality_id"))
    if not quality_id:
        mismatches.append("quality_id:missing")
    else:
        result["quality_id"] = quality_id
    supplied = artifacts["lineage"]
    for key, value in supplied.items():
        value = _clean(value)
        if not value:
            mismatches.append(f"{key}:empty")
        elif key in result and result[key] != value:
            mismatches.append(f"{key}:mismatch")
        else:
            result[key] = value
    if mismatches:
        raise ArticlePackageEngineError("LINEAGE_MISMATCH", "Production lineage is inconsistent", mismatches)
    return result


def _package_id(project_name: str, lineage: dict[str, str]) -> str:
    seed = {"project_name": project_name, "lineage": lineage, "schema_version": SCHEMA_VERSION}
    raw = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"package_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _content(draft: dict[str, Any]) -> tuple[dict[str, Any], dict[int, str]]:
    raw_sections = draft.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ArticlePackageEngineError("INVALID_CONTENT", "Article Draft sections must be a non-empty array")
    sections: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    section_ids: dict[int, str] = {}
    seen_sections: set[str] = set()
    seen_claims: set[str] = set()
    for index, raw_section in enumerate(raw_sections):
        section = _object(raw_section, f"article_draft.sections[{index}]")
        section_id = _clean(section.get("section_id")) or f"section_{index}"
        if section_id in seen_sections:
            raise ArticlePackageEngineError("DUPLICATE_ID", "Duplicate section_id", [section_id])
        heading, body, purpose = map(_clean, (section.get("heading"), section.get("body"), section.get("purpose")))
        refs = [_clean(ref) for ref in section.get("evidence_refs", [])] if isinstance(section.get("evidence_refs"), list) else []
        raw_claims = section.get("claims")
        if not heading or not body or not purpose or not refs or len(refs) != len(set(refs)) or any(not ref for ref in refs):
            raise ArticlePackageEngineError("INVALID_CONTENT", "Section content/evidence is incomplete", [section_id])
        if not isinstance(raw_claims, list) or not raw_claims:
            raise ArticlePackageEngineError("INVALID_CLAIMS", "Every section requires claims", [section_id])
        section_claim_ids: list[str] = []
        for claim_index, raw_claim in enumerate(raw_claims):
            claim = _object(raw_claim, f"sections[{index}].claims[{claim_index}]")
            claim_id, text, status = _clean(claim.get("claim_id")), _clean(claim.get("text")), _clean(claim.get("grounding_status"))
            claim_refs = [_clean(ref) for ref in claim.get("evidence_refs", [])] if isinstance(claim.get("evidence_refs"), list) else []
            if not claim_id or claim_id in seen_claims:
                raise ArticlePackageEngineError("DUPLICATE_ID", "Claim ID is missing or duplicated", [claim_id or section_id])
            if not text or status not in {"grounded", "blocked", "provisional"}:
                raise ArticlePackageEngineError("INVALID_CLAIM", "Claim text or grounding status is invalid", [claim_id])
            if len(claim_refs) != len(set(claim_refs)) or any(not ref for ref in claim_refs) or any(ref not in refs for ref in claim_refs):
                raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Claim evidence references must resolve to its section", [claim_id])
            seen_claims.add(claim_id)
            section_claim_ids.append(claim_id)
            claims.append({"claim_id": claim_id, "section_id": section_id, "text": text, "evidence_refs": claim_refs, "grounding_status": status})
        seen_sections.add(section_id)
        section_ids[index] = section_id
        sections.append({"section_id": section_id, "order": index, "heading": heading, "body": body, "purpose": purpose, "claim_ids": section_claim_ids, "evidence_refs": refs})
    article = {"title": _clean(draft.get("title")), "slug": _clean(draft.get("slug"))}
    if not article["title"] or not article["slug"]:
        raise ArticlePackageEngineError("INVALID_CONTENT", "Article title and slug are required")
    if _clean(draft.get("excerpt")):
        article["excerpt"] = _clean(draft["excerpt"])
    return {"article": article, "sections": sections, "claims": claims}, section_ids


def _tables(draft: dict[str, Any], section_ids: dict[int, str]) -> list[dict[str, Any]]:
    raw_tables = draft.get("tables", [])
    if not isinstance(raw_tables, list):
        raise ArticlePackageEngineError("INVALID_TABLES", "Article Draft tables must be an array")
    tables: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_tables:
        table = _object(raw, "article_draft.table")
        table_id = _clean(table.get("table_id")); section_index = table.get("section_index")
        if not table_id or table_id in seen or not isinstance(section_index, int) or isinstance(section_index, bool) or section_index not in section_ids:
            raise ArticlePackageEngineError("INVALID_TABLE", "Table identity or section reference is invalid", [table_id or "unknown"])
        columns = [_clean(v) for v in table.get("columns", [])] if isinstance(table.get("columns"), list) else []
        rows = table.get("rows")
        refs = [_clean(v) for v in table.get("evidence_refs", [])] if isinstance(table.get("evidence_refs"), list) else []
        if not _clean(table.get("title")) or not columns or not isinstance(rows, list) or not rows or any(len(row) != len(columns) or any(not _clean(cell) for cell in row) for row in rows) or len(refs) != len(set(refs)) or any(not ref for ref in refs):
            raise ArticlePackageEngineError("INVALID_TABLE", "Table structure is invalid", [table_id])
        seen.add(table_id)
        tables.append({"table_id": table_id, "title": _clean(table["title"]), "section_id": section_ids[section_index], "columns": columns, "rows": [[_clean(cell) for cell in row] for row in rows], "evidence_refs": refs})
    if draft.get("content_type") in {"comparison", "buyer_guide"} and not tables:
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "Comparison and buyer_guide packages require a table")
    return tables


def _media(media: dict[str, Any], section_ids: dict[int, str]) -> dict[str, Any]:
    raw_images = media.get("images")
    if not isinstance(raw_images, list) or not raw_images:
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "Media artifact requires at least one image")
    images: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_images:
        image = _object(raw, "media.image")
        image_id = _clean(image.get("image_id")); section_id = _clean(image.get("section_id"))
        if not section_id and isinstance(image.get("section_index"), int) and not isinstance(image.get("section_index"), bool):
            section_id = section_ids.get(image["section_index"], "")
        status = _clean(image.get("materialization_status")); alt_text = _clean(image.get("alt_text"))
        if not image_id or image_id in seen or section_id not in section_ids.values():
            raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Image identity or section reference is invalid", [image_id or "unknown"])
        if status not in {"specified", "materialized"} or not _clean(image.get("placement")) or not _clean(image.get("prompt")) or not alt_text:
            raise ArticlePackageEngineError("INVALID_MEDIA", "Image media contract is incomplete", [image_id])
        item = {"image_id": image_id, "section_id": section_id, "placement": _clean(image["placement"]), "prompt": _clean(image["prompt"]), "alt_text": alt_text, "materialization_status": status}
        if status == "materialized":
            asset_ref = _clean(image.get("asset_ref"))
            if not asset_ref:
                raise ArticlePackageEngineError("MEDIA_NOT_MATERIALIZED", "Materialized image requires asset_ref", [image_id])
            item["asset_ref"] = asset_ref
        seen.add(image_id); images.append(item)
    result: dict[str, Any] = {"images": images}
    featured = media.get("featured_image")
    if featured is not None:
        featured = _object(featured, "media.featured_image")
        featured_id = _clean(featured.get("image_id")); image_map = {item["image_id"]: item for item in images}
        if featured_id not in image_map:
            raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Featured image does not reference a package image", [featured_id])
        result["featured_image"] = {"image_id": featured_id}
    return result


def _links(linking: dict[str, Any], section_ids: dict[int, str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"internal": [], "external": []}; seen: set[str] = set()
    for kind in result:
        raw_links = linking.get(kind)
        if not isinstance(raw_links, list):
            raise ArticlePackageEngineError("INVALID_LINKS", f"linking.{kind} must be an array")
        for raw in raw_links:
            link = _object(raw, f"linking.{kind}"); link_id = _clean(link.get("link_id")); section_id = _clean(link.get("section_id"))
            if not section_id and isinstance(link.get("section_index"), int) and not isinstance(link.get("section_index"), bool):
                section_id = section_ids.get(link["section_index"], "")
            if not link_id or link_id in seen or section_id not in section_ids.values():
                raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Link identity or section reference is invalid", [link_id or "unknown"])
            item = {"link_id": link_id, "section_id": section_id, "target_url": _clean(link.get("target_url")), "anchor_text": _clean(link.get("anchor_text")), "placement": _clean(link.get("placement"))}
            if not all(item.values()):
                raise ArticlePackageEngineError("INVALID_LINKS", "Link target, anchor text, and placement are required", [link_id])
            seen.add(link_id); result[kind].append(item)
    return result


def _optimization(artifact: dict[str, Any]) -> dict[str, str]:
    result = {"seo_title": _clean(artifact.get("seo_title")), "meta_description": _clean(artifact.get("meta_description"))}
    if not result["seo_title"] or not result["meta_description"]:
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "Final SEO values are required")
    canonical = _clean(artifact.get("canonical_url"))
    if canonical:
        result["canonical_url"] = canonical
    return result


def _taxonomy(artifact: dict[str, Any]) -> dict[str, list[str]]:
    categories = [_clean(v) for v in artifact.get("categories", [])] if isinstance(artifact.get("categories"), list) else []
    tags = [_clean(v) for v in artifact.get("tags", [])] if isinstance(artifact.get("tags"), list) else []
    if not categories or len(categories) != len(set(categories)) or any(not v for v in categories):
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "At least one explicit taxonomy category is required")
    if len(tags) != len(set(tags)) or any(not v for v in tags):
        raise ArticlePackageEngineError("INVALID_TAXONOMY", "Taxonomy tags must be unique and non-empty")
    return {"categories": categories, "tags": tags}


def _schema_errors(package: dict[str, Any]) -> list[str]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(package), key=lambda e: (list(e.path), e.message))
    return [f"{'.'.join(str(p) for p in e.path) or 'root'}: {e.message}" for e in errors]


def _cross_errors(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []; sections = package["content"]["sections"]; section_ids = {s["section_id"] for s in sections}
    if [s["order"] for s in sections] != list(range(len(sections))):
        errors.append("sections.order must be contiguous from 0")
    claim_ids = {c["claim_id"] for c in package["content"]["claims"]}
    for section in sections:
        if any(cid not in claim_ids for cid in section["claim_ids"]): errors.append(f"section {section['section_id']} has unresolved claim reference")
    for claim in package["content"]["claims"]:
        if claim["section_id"] not in section_ids: errors.append(f"claim {claim['claim_id']} has unresolved section")
    image_ids = {i["image_id"] for i in package["media"]["images"]}
    for image in package["media"]["images"]:
        if image["section_id"] not in section_ids: errors.append(f"image {image['image_id']} has unresolved section")
    featured = package["media"].get("featured_image")
    if featured and featured["image_id"] not in image_ids: errors.append("featured image has unresolved image reference")
    link_ids = [l["link_id"] for kind in ("internal", "external") for l in package["linking"][kind]]
    if len(link_ids) != len(set(link_ids)): errors.append("link IDs must be unique across both link domains")
    for table in package["content"]["tables"]:
        if table["section_id"] not in section_ids: errors.append(f"table {table['table_id']} has unresolved section")
        if any(len(row) != len(table["columns"]) for row in table["rows"]): errors.append(f"table {table['table_id']} has invalid row cardinality")
    return errors


def validate_article_package(*, package: dict[str, Any], target_stage: str = "package_validated") -> dict[str, Any]:
    """Validate an assembled package and return a deep-copied validated package."""
    if target_stage not in {"package_validated", "delivery_ready"}: raise ValueError("target_stage must be package_validated or delivery_ready")
    candidate = copy.deepcopy(package); candidate["identity"]["lifecycle_stage"] = target_stage; candidate["audit"]["validation_status"] = "validated"
    errors = _cross_errors(candidate) + _schema_errors(candidate)
    if target_stage == "delivery_ready":
        errors.extend(f"image {image['image_id']} is not materialized" for image in candidate["media"]["images"] if image["materialization_status"] != "materialized" or not _clean(image.get("asset_ref")))
        errors.extend(f"claim {claim['claim_id']} is not grounded" for claim in candidate["content"]["claims"] if claim["grounding_status"] != "grounded")
    if errors: raise ArticlePackageEngineError("PACKAGE_INVALID", "Article Package validation failed", errors)
    return candidate


def build_article_package(*, project_name: str, artifacts: dict[str, Any], target_stage: str = "delivery_ready") -> dict[str, Any]:
    """Assemble a deterministic Article Package from explicit upstream artifacts only."""
    if not _clean(project_name): raise ArticlePackageEngineError("INVALID_INPUT", "project_name must be non-empty")
    if target_stage not in {"package_assembled", "package_validated", "delivery_ready"}: raise ValueError("Unsupported target_stage")
    artifacts = _object(artifacts, "artifacts"); _require_artifacts(artifacts)
    draft = _object(artifacts["article_draft"], "article_draft"); quality = _object(artifacts["quality"], "quality")
    _ready(draft, "draft_ready", "Article Draft"); _ready(quality, "article_draft_quality_ready", "Article Draft Quality")
    if quality.get("outcome") != "passed" or quality.get("audit", {}).get("validation_status") != "validated":
        raise ArticlePackageEngineError("UPSTREAM_NOT_READY", "Article Draft Quality must be passed and validated")
    claim_audit = _object(artifacts["claim_audit"], "claim_audit"); editorial = _object(artifacts["editorial_review"], "editorial_review"); intent = _object(artifacts["production_intent"], "production_intent")
    if claim_audit.get("outcome") != "passed" or claim_audit.get("audit", {}).get("validation_status") != "validated": raise ArticlePackageEngineError("UPSTREAM_NOT_READY", "Claim Audit must be passed and validated")
    if editorial.get("outcome") != "approved" or editorial.get("audit", {}).get("validation_status") != "validated": raise ArticlePackageEngineError("UPSTREAM_NOT_READY", "Editorial Review must be approved and validated")
    if intent != {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True}: raise ArticlePackageEngineError("UNSAFE_PUBLICATION_INTENT", "Production intent is not the immutable draft-only v1 intent")
    lineage = _lineage(artifacts)
    content, section_ids = _content(draft); content["tables"] = _tables(draft, section_ids)
    package = {
        "identity": {"package_id": _package_id(project_name, lineage), "project_name": project_name, "schema_version": SCHEMA_VERSION, "lifecycle_stage": "package_assembled", "content_type": _clean(draft.get("content_type")), "primary_keyword": _clean(draft.get("primary_keyword"))},
        "lineage": lineage,
        "content": content,
        "media": _media(_object(artifacts["media"], "media"), section_ids),
        "linking": _links(_object(artifacts["linking"], "linking"), section_ids),
        "optimization": _optimization(_object(artifacts["optimization"], "optimization")),
        "taxonomy": _taxonomy(_object(artifacts["taxonomy"], "taxonomy")),
        "delivery": copy.deepcopy(intent),
        "audit": {"method": "article_package_contract", "version": "v1", "validation_status": "pending"},
    }
    errors = _cross_errors(package) + _schema_errors(package)
    if errors: raise ArticlePackageEngineError("PACKAGE_INVALID", "Assembled Article Package violates its contract", errors)
    if target_stage == "package_assembled": return package
    return validate_article_package(package=package, target_stage=target_stage)
