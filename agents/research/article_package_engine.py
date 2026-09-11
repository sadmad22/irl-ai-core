from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGES = (
    "production_ready",
    "package_assembled",
    "package_validated",
    "delivery_ready",
)
_REQUIRED_ARTIFACTS = (
    "article_draft",
    "quality",
    "optimization",
    "media",
    "linking",
    "taxonomy",
)
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "article-package.schema.json"


class ArticlePackageEngineError(ValueError):
    """Deterministic, fail-closed Article Package Engine error."""

    def __init__(self, code: str, message: str, details: list[str] | None = None) -> None:
        self.code = code
        self.details = tuple(details or ())
        detail_text = f" ({'; '.join(self.details)})" if self.details else ""
        super().__init__(f"{code}: {message}{detail_text}")


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArticlePackageEngineError("INVALID_INPUT", f"{name} must be an object")
    return value


def _require_artifacts(artifacts: dict[str, Any]) -> None:
    missing = [name for name in _REQUIRED_ARTIFACTS if name not in artifacts]
    if missing:
        raise ArticlePackageEngineError("MISSING_ARTIFACT", "Required upstream artifact is missing", missing)
    if not isinstance(artifacts.get("lineage", {}), dict):
        raise ArticlePackageEngineError("INVALID_INPUT", "lineage must be an object")


def _require_ready(artifact: dict[str, Any], field: str, value: str, name: str) -> None:
    if artifact.get(field) != value:
        raise ArticlePackageEngineError("UPSTREAM_NOT_READY", f"{name} must be {value}")


def _lineage(artifacts: dict[str, Any]) -> dict[str, str]:
    draft = _require_object(artifacts["article_draft"], "article_draft")
    quality = _require_object(artifacts["quality"], "quality")
    required = ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id")
    result: dict[str, str] = {}
    mismatches: list[str] = []
    for key in required:
        draft_value = _clean(draft.get(key))
        quality_value = _clean(quality.get(key))
        if not draft_value or not quality_value:
            mismatches.append(key)
        elif draft_value != quality_value:
            mismatches.append(f"{key}:mismatch")
        else:
            result[key] = draft_value
    quality_id = _clean(quality.get("quality_id"))
    if not quality_id:
        mismatches.append("quality_id")
    else:
        result["quality_id"] = quality_id
    supplied = artifacts.get("lineage") or {}
    for key, value in supplied.items():
        value = _clean(value)
        if not value:
            raise ArticlePackageEngineError("INVALID_LINEAGE", f"lineage.{key} must be non-empty")
        if key in result and result[key] != value:
            mismatches.append(f"{key}:supplied_mismatch")
        result[key] = value
    if mismatches:
        raise ArticlePackageEngineError("LINEAGE_MISMATCH", "Upstream lineage is inconsistent", mismatches)
    return result


def _package_id(project_name: str, lineage: dict[str, str]) -> str:
    seed = {"project_name": project_name, "lineage": lineage, "schema_version": SCHEMA_VERSION}
    raw = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"package_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _sections_and_claims(draft: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, str]]:
    raw_sections = draft.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ArticlePackageEngineError("INVALID_CONTENT", "Article Draft sections must be a non-empty array")
    sections: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    section_ids: dict[int, str] = {}
    seen_section_ids: set[str] = set()
    seen_claim_ids: set[str] = set()
    for index, raw_section in enumerate(raw_sections):
        section = _require_object(raw_section, f"article_draft.sections[{index}]")
        section_id = _clean(section.get("section_id")) or f"section_{index}"
        if section_id in seen_section_ids:
            raise ArticlePackageEngineError("DUPLICATE_ID", "Duplicate section_id", [section_id])
        seen_section_ids.add(section_id)
        section_ids[index] = section_id
        refs = [_clean(ref) for ref in section.get("evidence_refs", [])] if isinstance(section.get("evidence_refs"), list) else []
        if not refs or any(not ref for ref in refs) or len(refs) != len(set(refs)):
            raise ArticlePackageEngineError("INVALID_EVIDENCE_REFS", "Section evidence_refs must be non-empty and unique", [f"section_{index}"])
        raw_claims = section.get("claims")
        if not isinstance(raw_claims, list) or not raw_claims:
            raise ArticlePackageEngineError("INVALID_CLAIMS", "Every Article Draft section must contain claims", [f"section_{index}"])
        claim_ids: list[str] = []
        for claim_index, raw_claim in enumerate(raw_claims):
            claim = _require_object(raw_claim, f"sections[{index}].claims[{claim_index}]")
            claim_id = _clean(claim.get("claim_id"))
            text = _clean(claim.get("text"))
            claim_refs = [_clean(ref) for ref in claim.get("evidence_refs", [])] if isinstance(claim.get("evidence_refs"), list) else []
            status = _clean(claim.get("grounding_status"))
            if not claim_id or claim_id in seen_claim_ids:
                raise ArticlePackageEngineError("DUPLICATE_ID", "Claim ID is missing or duplicated", [claim_id or f"section_{index}:{claim_index}"])
            if not text:
                raise ArticlePackageEngineError("INVALID_CLAIM", "Claim text must be non-empty", [claim_id])
            if len(claim_refs) != len(set(claim_refs)) or any(not ref for ref in claim_refs):
                raise ArticlePackageEngineError("INVALID_EVIDENCE_REFS", "Claim evidence_refs must be unique and non-empty when supplied", [claim_id])
            if any(ref not in refs for ref in claim_refs):
                raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Claim evidence_refs must belong to its section evidence_refs", [claim_id])
            seen_claim_ids.add(claim_id)
            claim_ids.append(claim_id)
            claims.append({
                "claim_id": claim_id,
                "section_id": section_id,
                "text": text,
                "evidence_refs": claim_refs,
                "grounding_status": status,
            })
        sections.append({
            "section_id": section_id,
            "order": index,
            "heading": _clean(section.get("heading")),
            "body": _clean(section.get("body")),
            "purpose": _clean(section.get("purpose")),
            "claim_ids": claim_ids,
            "evidence_refs": refs,
        })
    return sections, claims, section_ids


def _tables(draft: dict[str, Any], section_ids: dict[int, str]) -> list[dict[str, Any]]:
    raw_tables = draft.get("tables", [])
    if not isinstance(raw_tables, list):
        raise ArticlePackageEngineError("INVALID_TABLES", "Article Draft tables must be an array")
    tables: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_table in enumerate(raw_tables):
        table = _require_object(raw_table, f"article_draft.tables[{index}]")
        table_id = _clean(table.get("table_id"))
        if not table_id or table_id in seen:
            raise ArticlePackageEngineError("DUPLICATE_ID", "Table ID is missing or duplicated", [table_id or str(index)])
        section_index = table.get("section_index")
        if isinstance(section_index, bool) or not isinstance(section_index, int) or section_index not in section_ids:
            raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Table section_index does not resolve", [table_id])
        columns = [_clean(value) for value in table.get("columns", [])] if isinstance(table.get("columns"), list) else []
        rows = table.get("rows")
        if not columns or not isinstance(rows, list) or not rows:
            raise ArticlePackageEngineError("INVALID_TABLES", "Table columns and rows are required", [table_id])
        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != len(columns) or any(not _clean(cell) for cell in row):
                raise ArticlePackageEngineError("INVALID_TABLE", "Every table row must match column cardinality", [f"{table_id}:{row_index}"])
        refs = [_clean(ref) for ref in table.get("evidence_refs", [])] if isinstance(table.get("evidence_refs"), list) else []
        if len(refs) != len(set(refs)) or any(not ref for ref in refs):
            raise ArticlePackageEngineError("INVALID_EVIDENCE_REFS", "Table evidence_refs must be unique", [table_id])
        seen.add(table_id)
        tables.append({
            "table_id": table_id,
            "title": _clean(table.get("title")),
            "section_id": section_ids[section_index],
            "columns": columns,
            "rows": [[_clean(cell) for cell in row] for row in rows],
            "evidence_refs": refs,
        })
    if draft.get("content_type") in {"comparison", "buyer_guide"} and not tables:
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "Comparison and buyer_guide packages require a table")
    return tables


def _media(media_artifact: dict[str, Any], section_ids: dict[int, str]) -> tuple[dict[str, Any], str | None]:
    raw_images = media_artifact.get("images")
    if not isinstance(raw_images, list) or not raw_images:
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "Media artifact requires at least one image")
    images: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_image in enumerate(raw_images):
        image = _require_object(raw_image, f"media.images[{index}]")
        image_id = _clean(image.get("image_id"))
        if not image_id or image_id in seen:
            raise ArticlePackageEngineError("DUPLICATE_ID", "Image ID is missing or duplicated", [image_id or str(index)])
        section_id = _clean(image.get("section_id"))
        if not section_id:
            section_index = image.get("section_index")
            if isinstance(section_index, int) and not isinstance(section_index, bool):
                section_id = section_ids.get(section_index, "")
        if not section_id or section_id not in section_ids.values():
            raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Image section reference does not resolve", [image_id])
        status = _clean(image.get("materialization_status"))
        if status not in {"specified", "materialized"}:
            raise ArticlePackageEngineError("INVALID_MEDIA", "Unsupported media materialization_status", [image_id])
        alt_text = _clean(image.get("alt_text"))
        if not alt_text:
            raise ArticlePackageEngineError("INVALID_MEDIA", "Image alt_text is required", [image_id])
        item = {
            "image_id": image_id,
            "section_id": section_id,
            "placement": _clean(image.get("placement")),
            "prompt": _clean(image.get("prompt")),
            "alt_text": alt_text,
            "materialization_status": status,
        }
        if status == "materialized":
            asset_ref = _clean(image.get("asset_ref"))
            if not asset_ref:
                raise ArticlePackageEngineError("MEDIA_NOT_MATERIALIZED", "Materialized image requires asset_ref", [image_id])
            item["asset_ref"] = asset_ref
        seen.add(image_id)
        images.append(item)
    featured = media_artifact.get("featured_image")
    featured_id = None
    if featured is not None:
        featured = _require_object(featured, "media.featured_image")
        featured_id = _clean(featured.get("image_id"))
        image_map = {image["image_id"]: image for image in images}
        if featured_id not in image_map:
            raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Featured image does not reference an image", [featured_id])
    result = {"images": images}
    if featured_id:
        result["featured_image"] = {"image_id": featured_id}
    return result, featured_id


def _links(linking: dict[str, Any], section_ids: dict[int, str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"internal": [], "external": []}
    seen: set[str] = set()
    for kind in ("internal", "external"):
        raw_links = linking.get(kind)
        if not isinstance(raw_links, list):
            raise ArticlePackageEngineError("INVALID_LINKS", f"linking.{kind} must be an array")
        for index, raw_link in enumerate(raw_links):
            link = _require_object(raw_link, f"linking.{kind}[{index}]")
            link_id = _clean(link.get("link_id"))
            section_id = _clean(link.get("section_id"))
            if not section_id:
                section_index = link.get("section_index")
                if isinstance(section_index, int) and not isinstance(section_index, bool):
                    section_id = section_ids.get(section_index, "")
            if not link_id or link_id in seen:
                raise ArticlePackageEngineError("DUPLICATE_ID", "Link ID is missing or duplicated", [link_id or f"{kind}:{index}"])
            if section_id not in section_ids.values():
                raise ArticlePackageEngineError("REFERENCE_INTEGRITY", "Link section reference does not resolve", [link_id])
            target_url = _clean(link.get("target_url"))
            anchor_text = _clean(link.get("anchor_text"))
            placement = _clean(link.get("placement"))
            if not target_url or not anchor_text or not placement:
                raise ArticlePackageEngineError("INVALID_LINKS", "Link target, anchor_text, and placement are required", [link_id])
            result[kind].append({"link_id": link_id, "section_id": section_id, "target_url": target_url, "anchor_text": anchor_text, "placement": placement})
            seen.add(link_id)
    return result


def _optimization(optimization: dict[str, Any]) -> dict[str, str]:
    seo_title = _clean(optimization.get("seo_title"))
    meta_description = _clean(optimization.get("meta_description"))
    if not seo_title or not meta_description:
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "Final SEO title and meta description are required")
    result = {"seo_title": seo_title, "meta_description": meta_description}
    canonical = _clean(optimization.get("canonical_url"))
    if canonical:
        result["canonical_url"] = canonical
    return result


def _taxonomy(taxonomy: dict[str, Any]) -> dict[str, list[str]]:
    categories = [_clean(value) for value in taxonomy.get("categories", [])] if isinstance(taxonomy.get("categories"), list) else []
    tags = [_clean(value) for value in taxonomy.get("tags", [])] if isinstance(taxonomy.get("tags"), list) else []
    if not categories or any(not value for value in categories) or len(categories) != len(set(categories)):
        raise ArticlePackageEngineError("REQUIRED_ASSET_MISSING", "At least one unique non-empty taxonomy category is required")
    if any(not value for value in tags) or len(tags) != len(set(tags)):
        raise ArticlePackageEngineError("INVALID_TAXONOMY", "Taxonomy tags must be unique and non-empty")
    return {"categories": categories, "tags": tags}


def _schema_errors(package: dict[str, Any]) -> list[str]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(package), key=lambda error: (list(error.path), error.message))
    return [f"{'.'.join(str(part) for part in error.path) or 'root'}: {error.message}" for error in errors]


def _validate_cross_domain(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sections = package["content"]["sections"]
    section_ids = {section["section_id"] for section in sections}
    if [section["order"] for section in sections] != list(range(len(sections))):
        errors.append("sections.order must start at 0 and increment by 1")
    claim_ids = {claim["claim_id"] for claim in package["content"]["claims"]}
    for section in sections:
        if any(claim_id not in claim_ids for claim_id in section["claim_ids"]):
            errors.append(f"section {section['section_id']} contains an unresolved claim reference")
    for claim in package["content"]["claims"]:
        if claim["section_id"] not in section_ids:
            errors.append(f"claim {claim['claim_id']} references an unknown section")
        if claim["grounding_status"] == "grounded" and not claim["evidence_refs"]:
            errors.append(f"claim {claim['claim_id']} is grounded without evidence")
    table_ids = {table["table_id"] for table in package["content"]["tables"]}
    if len(table_ids) != len(package["content"]["tables"]):
        errors.append("table IDs must be unique")
    for table in package["content"]["tables"]:
        if table["section_id"] not in section_ids:
            errors.append(f"table {table['table_id']} references an unknown section")
        if any(len(row) != len(table["columns"]) for row in table["rows"]):
            errors.append(f"table {table['table_id']} has invalid row cardinality")
    image_ids = {image["image_id"] for image in package["media"]["images"]}
    for image in package["media"]["images"]:
        if image["section_id"] not in section_ids:
            errors.append(f"image {image['image_id']} references an unknown section")
    featured = package["media"].get("featured_image")
    if featured and featured["image_id"] not in image_ids:
        errors.append("featured_image references an unknown image")
    link_ids = [link["link_id"] for kind in ("internal", "external") for link in package["linking"][kind]]
    if len(link_ids) != len(set(link_ids)):
        errors.append("link IDs must be unique across internal and external links")
    for kind in ("internal", "external"):
        for link in package["linking"][kind]:
            if link["section_id"] not in section_ids:
                errors.append(f"{kind} link {link['link_id']} references an unknown section")
    return errors


def _validate_delivery_ready(package: dict[str, Any]) -> None:
    errors: list[str] = []
    if package["audit"]["validation_status"] != "validated":
        errors.append("audit.validation_status must be validated")
    for image in package["media"]["images"]:
        if image["materialization_status"] != "materialized" or not _clean(image.get("asset_ref")):
            errors.append(f"image {image['image_id']} is not materialized")
    for claim in package["content"]["claims"]:
        if claim["grounding_status"] != "grounded":
            errors.append(f"claim {claim['claim_id']} is not grounded")
    if errors:
        raise ArticlePackageEngineError("DELIVERY_NOT_READY", "Package cannot become delivery_ready", errors)


def validate_article_package(*, package: dict[str, Any], target_stage: str = "package_validated") -> dict[str, Any]:
    """Validate an assembled package without changing its content."""
    if target_stage not in LIFECYCLE_STAGES[2:]:
        raise ValueError("target_stage must be package_validated or delivery_ready")
    candidate = copy.deepcopy(package)
    candidate["identity"]["lifecycle_stage"] = target_stage
    candidate["audit"]["validation_status"] = "validated"
    errors = _validate_cross_domain(candidate) + _schema_errors(candidate)
    if target_stage == "delivery_ready":
        try:
            _validate_delivery_ready(candidate)
        except ArticlePackageEngineError as exc:
            errors.extend(exc.details)
    if errors:
        raise ArticlePackageEngineError("PACKAGE_INVALID", "Article Package validation failed", errors)
    return candidate


def build_article_package(*, project_name: str, artifacts: dict[str, Any], target_stage: str = "delivery_ready") -> dict[str, Any]:
    """Assemble a deterministic Article Package from explicit upstream artifacts only."""
    if not _clean(project_name):
        raise ArticlePackageEngineError("INVALID_INPUT", "project_name must be non-empty")
    if target_stage not in {"package_assembled", "package_validated", "delivery_ready"}:
        raise ValueError("target_stage must be package_assembled, package_validated, or delivery_ready")
    artifacts = _require_object(artifacts, "artifacts")
    _require_artifacts(artifacts)

    draft = _require_object(artifacts["article_draft"], "article_draft")
    quality = _require_object(artifacts["quality"], "quality")
    _require_ready(draft, "lifecycle_stage", "draft_ready", "Article Draft")
    _require_ready(quality, "lifecycle_stage", "article_draft_quality_ready", "Article Draft Quality")
    if quality.get("outcome") != "passed" or quality.get("audit", {}).get("validation_status") != "validated":
        raise ArticlePackageEngineError("UPSTREAM_NOT_READY", "Article Draft Quality must be passed and validated")
    if _clean(quality.get("draft_id")) != _clean(draft.get("draft_id")):
        raise ArticlePackageEngineError("LINEAGE_MISMATCH", "Article Draft and Quality draft_id must match")

    lineage = _lineage(artifacts)
    sections, claims, section_ids = _sections_and_claims(draft)
    tables = _tables(draft, section_ids)
    media, _ = _media(_require_object(artifacts["media"], "media"), section_ids)
    linking = _links(_require_object(artifacts["linking"], "linking"), section_ids)
    optimization = _optimization(_require_object(artifacts["optimization"], "optimization"))
    taxonomy = _taxonomy(_require_object(artifacts["taxonomy"], "taxonomy"))

    article = {"title": _clean(draft.get("title")), "slug": _clean(draft.get("slug"))}
    if not article["title"]:
        raise ArticlePackageEngineError("INVALID_CONTENT", "Article title is required")
    if _clean(draft.get("excerpt")):
        article["excerpt"] = _clean(draft["excerpt"])

    package = {
        "identity": {
            "package_id": _package_id(project_name, lineage),
            "project_name": project_name,
            "schema_version": SCHEMA_VERSION,
            "lifecycle_stage": "package_assembled",
            "content_type": _clean(draft.get("content_type")),
            "primary_keyword": _clean(draft.get("primary_keyword")),
        },
        "lineage": lineage,
        "content": {"article": article, "sections": sections, "claims": claims, "tables": tables},
        "media": media,
        "linking": linking,
        "optimization": optimization,
        "taxonomy": taxonomy,
        "delivery": {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True},
        "audit": {"method": "article_package_contract", "version": "v1", "validation_status": "pending"},
    }

    structural_errors = _validate_cross_domain(package) + _schema_errors(package)
    if structural_errors:
        raise ArticlePackageEngineError("PACKAGE_INVALID", "Assembled Article Package violates its contract", structural_errors)
    if target_stage == "package_assembled":
        return package
    return validate_article_package(package=package, target_stage=target_stage)
