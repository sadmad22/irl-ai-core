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
    "assembly_started",
    "inputs_validated",
    "artifacts_normalized",
    "production_assembly_ready",
    "failed",
)
_REQUIRED_ARTIFACTS = (
    "article_draft",
    "quality",
    "claim_audit",
    "editorial_review",
    "optimization",
    "media",
    "linking",
    "taxonomy",
    "production_intent",
)
_REQUIRED_LINEAGE = (
    "report_id",
    "decision_id",
    "strategy_id",
    "brief_id",
    "draft_id",
    "quality_id",
)
_EXPECTED_INTENT = {
    "target": "wordpress",
    "mode": "wordpress_draft",
    "publish": False,
    "human_approval_required": True,
}
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "production-assembly.schema.json"


class ProductionAssemblyEngineError(ValueError):
    """Deterministic, fail-closed Production Assembly error."""

    def __init__(self, code: str, message: str, details: list[str] | None = None) -> None:
        self.code = code
        self.details = tuple(details or ())
        suffix = f" ({'; '.join(self.details)})" if self.details else ""
        super().__init__(f"{code}: {message}{suffix}")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionAssemblyEngineError("INVALID_INPUT", f"{name} must be an object")
    return value


def _validate_inputs(inputs: dict[str, Any]) -> None:
    missing = [name for name in _REQUIRED_ARTIFACTS if name not in inputs]
    if missing:
        raise ProductionAssemblyEngineError("MISSING_ARTIFACT", "Required production artifact is missing", missing)
    lineage = _object(inputs.get("lineage"), "lineage")
    missing_lineage = [key for key in _REQUIRED_LINEAGE if not _text(lineage.get(key))]
    if missing_lineage:
        raise ProductionAssemblyEngineError("INVALID_LINEAGE", "Required production lineage is missing", missing_lineage)

    draft = _object(inputs["article_draft"], "article_draft")
    if draft.get("lifecycle_stage") != "draft_ready":
        raise ProductionAssemblyEngineError("UPSTREAM_NOT_READY", "article_draft must be draft_ready")

    quality = _object(inputs["quality"], "quality")
    if quality.get("lifecycle_stage") != "article_draft_quality_ready" or quality.get("outcome") != "passed":
        raise ProductionAssemblyEngineError("QUALITY_GATE_FAILED", "quality must be passed and ready")
    if _object(quality.get("audit"), "quality.audit").get("validation_status") != "validated":
        raise ProductionAssemblyEngineError("QUALITY_GATE_FAILED", "quality audit must be validated")

    claim_audit = _object(inputs["claim_audit"], "claim_audit")
    if claim_audit.get("outcome") != "passed" or _object(claim_audit.get("audit"), "claim_audit.audit").get("validation_status") != "validated":
        raise ProductionAssemblyEngineError("CLAIM_AUDIT_FAILED", "claim_audit must be passed and validated")

    editorial = _object(inputs["editorial_review"], "editorial_review")
    if editorial.get("outcome") != "approved" or _object(editorial.get("audit"), "editorial_review.audit").get("validation_status") != "validated":
        raise ProductionAssemblyEngineError("EDITORIAL_GATE_FAILED", "editorial_review must be approved and validated")

    optimization = _object(inputs["optimization"], "optimization")
    if not _text(optimization.get("seo_title")) or not _text(optimization.get("meta_description")):
        raise ProductionAssemblyEngineError("OPTIMIZATION_INCOMPLETE", "Final SEO title and meta description are required")

    media = _object(inputs["media"], "media")
    images = media.get("images")
    if not isinstance(images, list) or not images:
        raise ProductionAssemblyEngineError("MEDIA_NOT_READY", "At least one media image is required")
    seen_images: set[str] = set()
    for index, raw in enumerate(images):
        image = _object(raw, f"media.images[{index}]")
        image_id = _text(image.get("image_id"))
        if not image_id or image_id in seen_images:
            raise ProductionAssemblyEngineError("INVALID_MEDIA", "Image identity is missing or duplicated", [image_id or str(index)])
        seen_images.add(image_id)
        if image.get("materialization_status") != "materialized":
            raise ProductionAssemblyEngineError("MEDIA_NOT_MATERIALIZED", "All assembly media must be materialized", [image_id])
        if not _text(image.get("asset_ref")) or not _text(image.get("alt_text")) or not _text(image.get("prompt")) or not _text(image.get("placement")):
            raise ProductionAssemblyEngineError("INVALID_MEDIA", "Materialized media requires asset_ref, alt_text, prompt, and placement", [image_id])
        section_ref = image.get("section_id")
        if not _text(section_ref) and not isinstance(image.get("section_index"), int):
            raise ProductionAssemblyEngineError("REFERENCE_INTEGRITY", "Media requires a section reference", [image_id])

    linking = _object(inputs["linking"], "linking")
    for kind in ("internal", "external"):
        links = linking.get(kind)
        if not isinstance(links, list):
            raise ProductionAssemblyEngineError("INVALID_LINKS", f"linking.{kind} must be an array")
        seen_links: set[str] = set()
        for index, raw in enumerate(links):
            link = _object(raw, f"linking.{kind}[{index}]")
            link_id = _text(link.get("link_id"))
            if not link_id or link_id in seen_links:
                raise ProductionAssemblyEngineError("INVALID_LINKS", "Link identity is missing or duplicated", [link_id or str(index)])
            seen_links.add(link_id)
            if not _text(link.get("target_url")) or not _text(link.get("anchor_text")) or not _text(link.get("placement")):
                raise ProductionAssemblyEngineError("INVALID_LINKS", "Link target, anchor text, and placement are required", [link_id])
            if not _text(link.get("section_id")) and not isinstance(link.get("section_index"), int):
                raise ProductionAssemblyEngineError("REFERENCE_INTEGRITY", "Link requires a section reference", [link_id])

    taxonomy = _object(inputs["taxonomy"], "taxonomy")
    categories = taxonomy.get("categories")
    tags = taxonomy.get("tags")
    if not isinstance(categories, list) or not categories or any(not _text(value) for value in categories) or len(categories) != len(set(categories)):
        raise ProductionAssemblyEngineError("INVALID_TAXONOMY", "At least one unique non-empty taxonomy category is required")
    if not isinstance(tags, list) or any(not _text(value) for value in tags) or len(tags) != len(set(tags)):
        raise ProductionAssemblyEngineError("INVALID_TAXONOMY", "Taxonomy tags must be unique and non-empty")

    intent = _object(inputs["production_intent"], "production_intent")
    if intent != _EXPECTED_INTENT:
        raise ProductionAssemblyEngineError("UNSAFE_PRODUCTION_INTENT", "Production intent must be immutable and draft-only")


def _normalize(inputs: dict[str, Any]) -> dict[str, Any]:
    """Return canonical Article Package inputs without mutating caller-owned data."""
    result = {name: copy.deepcopy(inputs[name]) for name in _REQUIRED_ARTIFACTS}
    draft = result["article_draft"]
    sections = draft.get("sections", [])
    section_ids = {
        index: _text(section.get("section_id"))
        for index, section in enumerate(sections)
        if isinstance(section, dict) and _text(section.get("section_id"))
    }

    for image in result["media"].get("images", []):
        if not _text(image.get("section_id")) and isinstance(image.get("section_index"), int):
            image["section_id"] = section_ids.get(image["section_index"], "")
        image.pop("section_index", None)

    for kind in ("internal", "external"):
        for link in result["linking"].get(kind, []):
            if not _text(link.get("section_id")) and isinstance(link.get("section_index"), int):
                link["section_id"] = section_ids.get(link["section_index"], "")
            link.pop("section_index", None)

    return result


def _lineage(inputs: dict[str, Any]) -> dict[str, str]:
    lineage = copy.deepcopy(inputs["lineage"])
    draft = inputs["article_draft"]
    quality = inputs["quality"]
    for key in ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id"):
        values = {_text(lineage.get(key)), _text(draft.get(key)), _text(quality.get(key))}
        if "" in values or len(values) != 1:
            raise ProductionAssemblyEngineError("LINEAGE_MISMATCH", "Production lineage is inconsistent", [key])
    if _text(lineage.get("quality_id")) != _text(quality.get("quality_id")):
        raise ProductionAssemblyEngineError("LINEAGE_MISMATCH", "quality_id lineage is inconsistent", ["quality_id"])
    return {key: _text(value) for key, value in lineage.items()}


def _assembly_id(project_name: str, lineage: dict[str, str], artifacts: dict[str, Any]) -> str:
    seed = {
        "project_name": project_name,
        "lineage": lineage,
        "artifacts": artifacts,
        "schema_version": SCHEMA_VERSION,
    }
    raw = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"assembly_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _validate_output(value: dict[str, Any]) -> None:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda error: (list(error.path), error.message))
    if errors:
        details = [f"{'.'.join(str(part) for part in error.path) or 'root'}: {error.message}" for error in errors]
        raise ProductionAssemblyEngineError("SCHEMA_VALIDATION_FAILED", "Production Assembly output failed schema validation", details)


def build_production_assembly(*, project_name: str, artifacts: dict[str, Any]) -> dict[str, Any]:
    """Assemble explicit production artifacts into a delivery-capable canonical result."""
    if not _text(project_name):
        raise ProductionAssemblyEngineError("INVALID_INPUT", "project_name must be a non-empty string")
    source = _object(artifacts, "artifacts")
    _validate_inputs(source)
    lineage = _lineage(source)
    normalized = _normalize(source)
    assembly_id = _assembly_id(project_name, lineage, normalized)
    result = {
        "assembly_id": assembly_id,
        "project_name": project_name.strip(),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "production_assembly_ready",
        "lineage": lineage,
        "artifacts": normalized,
        "audit": {
            "method": "production_assembly",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
    _validate_output(result)
    return result
