from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
TARGET = "wordpress"
PUBLICATION = {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "production-delivery-boundary.schema.json"


class ProductionDeliveryBoundaryEngineError(ValueError):
    """Deterministic, fail-closed Production Delivery Boundary Engine error."""

    def __init__(self, code: str, message: str, details: list[str] | None = None) -> None:
        self.code = code
        self.details = tuple(details or ())
        suffix = f" ({'; '.join(self.details)})" if self.details else ""
        super().__init__(f"{code}: {message}{suffix}")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _obj(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionDeliveryBoundaryEngineError("INVALID_INPUT", f"{name} must be an object")
    return value


def _package_id(package: dict[str, Any]) -> str:
    identity = _obj(package.get("identity"), "package.identity")
    package_id = _text(identity.get("package_id"))
    if not package_id:
        raise ProductionDeliveryBoundaryEngineError("INVALID_PACKAGE", "Article Package identity.package_id is required")
    return package_id


def _require_package_ready(package: dict[str, Any]) -> None:
    identity = _obj(package.get("identity"), "package.identity")
    audit = _obj(package.get("audit"), "package.audit")
    delivery = _obj(package.get("delivery"), "package.delivery")
    errors: list[str] = []
    if identity.get("lifecycle_stage") != "delivery_ready":
        errors.append("package.lifecycle_stage must be delivery_ready")
    if audit.get("validation_status") != "validated":
        errors.append("package.audit.validation_status must be validated")
    if _text(identity.get("schema_version")) != SCHEMA_VERSION:
        errors.append("package.identity.schema_version must be 1.0")
    if delivery != PUBLICATION:
        errors.append("package.delivery must be immutable wordpress_draft intent")
    if errors:
        raise ProductionDeliveryBoundaryEngineError("SOURCE_NOT_READY", "Article Package is not delivery-ready", errors)


def _deterministic_delivery_id(package_id: str, adapter_id: str) -> str:
    seed = {
        "package_id": package_id,
        "adapter_id": adapter_id,
        "target": TARGET,
        "schema_version": SCHEMA_VERSION,
    }
    raw = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"delivery_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _content(package: dict[str, Any]) -> tuple[dict[str, Any], set[str], set[str]]:
    content = _obj(package.get("content"), "package.content")
    article = _obj(content.get("article"), "package.content.article")
    sections = content.get("sections")
    claims = content.get("claims")
    tables = content.get("tables")
    if not isinstance(sections, list) or not sections:
        raise ProductionDeliveryBoundaryEngineError("INVALID_CONTENT", "Article Package sections must be a non-empty array")
    if not isinstance(claims, list):
        raise ProductionDeliveryBoundaryEngineError("INVALID_CONTENT", "Article Package claims must be an array")
    if not isinstance(tables, list):
        raise ProductionDeliveryBoundaryEngineError("INVALID_CONTENT", "Article Package tables must be an array")

    section_ids = [_text(s.get("section_id")) for s in sections if isinstance(s, dict)]
    if len(section_ids) != len(sections) or any(not x for x in section_ids) or len(set(section_ids)) != len(section_ids):
        raise ProductionDeliveryBoundaryEngineError("REFERENCE_INTEGRITY", "Article Package section identities are invalid")
    if [s.get("order") for s in sections] != list(range(len(sections))):
        raise ProductionDeliveryBoundaryEngineError("REFERENCE_INTEGRITY", "Article Package section order is not contiguous")

    claim_ids = {_text(c.get("claim_id")) for c in claims if isinstance(c, dict)}
    if len(claim_ids) != len(claims) or "" in claim_ids:
        raise ProductionDeliveryBoundaryEngineError("REFERENCE_INTEGRITY", "Article Package claim identities are invalid")
    for section in sections:
        if not isinstance(section.get("claim_ids"), list) or any(cid not in claim_ids for cid in section["claim_ids"]):
            raise ProductionDeliveryBoundaryEngineError("REFERENCE_INTEGRITY", f"Section {section.get('section_id', 'unknown')} has unresolved claims")
    for claim in claims:
        if claim.get("grounding_status") != "grounded":
            raise ProductionDeliveryBoundaryEngineError("UPSTREAM_NOT_READY", "All delivered claims must be grounded", [claim.get("claim_id", "unknown")])

    content_type = _text(package["identity"].get("content_type"))
    if content_type in {"comparison", "buyer_guide"} and not tables:
        raise ProductionDeliveryBoundaryEngineError("REQUIRED_ASSET_MISSING", "Comparison and buyer_guide packages require a table")

    article_out = {"title": _text(article.get("title")), "slug": _text(article.get("slug"))}
    if not article_out["title"] or not article_out["slug"]:
        raise ProductionDeliveryBoundaryEngineError("INVALID_CONTENT", "Article title and slug are required")
    if _text(article.get("excerpt")):
        article_out["excerpt"] = _text(article["excerpt"])

    return copy.deepcopy({"article": article_out, "sections": sections, "claims": claims, "tables": tables}), set(section_ids), claim_ids


def _render_content(content: dict[str, Any], media: list[dict[str, Any]], links: list[dict[str, Any]]) -> str:
    # Representation-only rendering. No discovery, generation, or rewriting occurs here.
    parts: list[str] = []
    for section in content["sections"]:
        parts.append(f"<h2>{section['heading']}</h2>")
        parts.append(f"<p>{section['body']}</p>")
        for table in content["tables"]:
            if table["section_id"] != section["section_id"]:
                continue
            parts.append("<table><thead><tr>" + "".join(f"<th>{cell}</th>" for cell in table["columns"]) + "</tr></thead><tbody>")
            for row in table["rows"]:
                parts.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
            parts.append("</tbody></table>")
        for image in media:
            if image["section_id"] == section["section_id"]:
                parts.append(f"<img src=\"{image['asset_ref']}\" alt=\"{image['alt_text']}\" />")
        for link in links:
            if link["section_id"] == section["section_id"]:
                parts.append(f"<a href=\"{link['target_url']}\">{link['anchor_text']}</a>")
    return "".join(parts)


def _media(package: dict[str, Any], section_ids: set[str]) -> list[dict[str, Any]]:
    media = _obj(package.get("media"), "package.media")
    images = media.get("images")
    if not isinstance(images, list) or not images:
        raise ProductionDeliveryBoundaryEngineError("REQUIRED_ASSET_MISSING", "Delivery-ready package requires at least one image")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in images:
        image = _obj(raw, "package.media.image")
        image_id = _text(image.get("image_id")); section_id = _text(image.get("section_id"))
        if not image_id or image_id in seen or section_id not in section_ids:
            raise ProductionDeliveryBoundaryEngineError("REFERENCE_INTEGRITY", "Media identity or section reference is invalid", [image_id or "unknown"])
        if image.get("materialization_status") != "materialized" or not _text(image.get("asset_ref")):
            raise ProductionDeliveryBoundaryEngineError("MEDIA_NOT_MATERIALIZED", "Every delivery-ready image must be materialized", [image_id])
        alt_text = _text(image.get("alt_text"))
        if not alt_text:
            raise ProductionDeliveryBoundaryEngineError("INVALID_MEDIA", "Every delivered image requires non-empty alt_text", [image_id])
        result.append({"image_id": image_id, "asset_ref": _text(image["asset_ref"]), "alt_text": alt_text, "placement": _text(image.get("placement")), "featured": False})
        seen.add(image_id)
    featured = package["media"].get("featured_image")
    if featured is not None:
        featured_id = _text(_obj(featured, "package.media.featured_image").get("image_id"))
        if featured_id not in seen:
            raise ProductionDeliveryBoundaryEngineError("REFERENCE_INTEGRITY", "Featured image does not reference a package image", [featured_id])
        for image in result:
            image["featured"] = image["image_id"] == featured_id
    return result


def _links(package: dict[str, Any], section_ids: set[str]) -> list[dict[str, Any]]:
    linking = _obj(package.get("linking"), "package.linking")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind in ("internal", "external"):
        raw_links = linking.get(kind)
        if not isinstance(raw_links, list):
            raise ProductionDeliveryBoundaryEngineError("INVALID_LINKS", f"package.linking.{kind} must be an array")
        for raw in raw_links:
            link = _obj(raw, f"package.linking.{kind}")
            item = {"link_id": _text(link.get("link_id")), "section_id": _text(link.get("section_id")), "target_url": _text(link.get("target_url")), "anchor_text": _text(link.get("anchor_text")), "placement": _text(link.get("placement")), "kind": kind}
            if not item["link_id"] or item["link_id"] in seen or item["section_id"] not in section_ids or not item["target_url"].startswith(("http://", "https://")) or not item["anchor_text"] or not item["placement"]:
                raise ProductionDeliveryBoundaryEngineError("INVALID_LINKS", "Explicit package link is invalid", [item["link_id"] or "unknown"])
            seen.add(item["link_id"]); result.append(item)
    return result


def _optimization(package: dict[str, Any]) -> dict[str, str]:
    optimization = _obj(package.get("optimization"), "package.optimization")
    result = {"seo_title": _text(optimization.get("seo_title")), "meta_description": _text(optimization.get("meta_description"))}
    if not result["seo_title"] or not result["meta_description"]:
        raise ProductionDeliveryBoundaryEngineError("REQUIRED_ASSET_MISSING", "Final SEO values are required")
    canonical = _text(optimization.get("canonical_url"))
    if canonical:
        result["canonical_url"] = canonical
    return result


def _taxonomy(package: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    taxonomy = _obj(package.get("taxonomy"), "package.taxonomy")
    categories = taxonomy.get("categories"); tags = taxonomy.get("tags")
    if not isinstance(categories, list) or not categories:
        raise ProductionDeliveryBoundaryEngineError("REQUIRED_ASSET_MISSING", "At least one explicit category is required")
    if not isinstance(tags, list):
        raise ProductionDeliveryBoundaryEngineError("INVALID_TAXONOMY", "Package tags must be an array")
    def items(values: list[Any], name: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []; seen: set[str] = set()
        for raw in values:
            if isinstance(raw, str):
                value = _text(raw); item = {"name": value}
            else:
                item = _obj(raw, f"package.taxonomy.{name}")
                value = _text(item.get("name")); item = {"name": value}
            if not value or value in seen:
                raise ProductionDeliveryBoundaryEngineError("INVALID_TAXONOMY", f"Taxonomy {name} contains an invalid or duplicate name")
            seen.add(value); out.append(item)
        return out
    return {"categories": items(categories, "categories"), "tags": items(tags, "tags")}


def _schema_errors(boundary: dict[str, Any]) -> list[str]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(boundary), key=lambda e: (list(e.path), e.message))
    return [f"{'.'.join(str(p) for p in error.path) or 'root'}: {error.message}" for error in errors]


def _cross_errors(boundary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if boundary["source"]["package_id"] != boundary["package_id"]:
        errors.append("source.package_id must equal package_id")
    media = boundary["request"]["media"]
    if sum(1 for item in media if item["featured"]) > 1:
        errors.append("at most one delivered image may be featured")
    if boundary["request"]["status"] != "draft":
        errors.append("request.status must remain draft")
    if boundary["publication"] != PUBLICATION:
        errors.append("publication safety policy is immutable draft-only")
    link_ids = [link["link_id"] for link in boundary["request"]["links"]]
    if len(link_ids) != len(set(link_ids)):
        errors.append("request link IDs must be unique")
    image_ids = [image["image_id"] for image in media]
    if len(image_ids) != len(set(image_ids)):
        errors.append("request image IDs must be unique")
    return errors


def validate_production_delivery_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    candidate = copy.deepcopy(boundary)
    if not isinstance(candidate, dict):
        raise ProductionDeliveryBoundaryEngineError("INVALID_INPUT", "Delivery Boundary must be an object")
    errors = _schema_errors(candidate) + _cross_errors(candidate)
    if errors:
        raise ProductionDeliveryBoundaryEngineError("BOUNDARY_INVALID", "Production Delivery Boundary validation failed", errors)
    return candidate


def build_production_delivery_boundary(*, package: dict[str, Any], publisher_id: str, adapter_id: str, execution_mode: str = "dry_run") -> dict[str, Any]:
    package = copy.deepcopy(_obj(package, "package"))
    publisher_id = _text(publisher_id); adapter_id = _text(adapter_id)
    if not publisher_id or not adapter_id:
        raise ProductionDeliveryBoundaryEngineError("INVALID_INPUT", "publisher_id and adapter_id are required")
    if execution_mode not in {"dry_run", "live"}:
        raise ProductionDeliveryBoundaryEngineError("INVALID_INPUT", "execution_mode must be dry_run or live")
    _require_package_ready(package)
    package_id = _package_id(package)
    content, section_ids, _ = _content(package)
    media = _media(package, section_ids)
    links = _links(package, section_ids)
    optimization = _optimization(package)
    taxonomy = _taxonomy(package)
    request = {
        **content["article"],
        "content": _render_content(content, media, links),
        "status": "draft",
        "media": media,
        "links": links,
        "optimization": optimization,
        "taxonomy": taxonomy,
    }
    boundary = {
        "delivery_id": _deterministic_delivery_id(package_id, adapter_id),
        "package_id": package_id,
        "publisher_id": publisher_id,
        "adapter_id": adapter_id,
        "target": TARGET,
        "execution_mode": execution_mode,
        "publication": copy.deepcopy(PUBLICATION),
        "source": {"package_id": package_id, "package_lifecycle_stage": "delivery_ready", "package_validation_status": "validated", "package_schema_version": SCHEMA_VERSION},
        "request": request,
        "lifecycle_stage": "delivery_ready",
        "delivery_status": "ready",
        "audit": {"method": "production_delivery_boundary", "version": METHOD_VERSION, "validation_status": "validated"},
    }
    return validate_production_delivery_boundary(boundary)
