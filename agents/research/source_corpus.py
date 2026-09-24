from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .source_acquisition import acquire_source_document, canonicalize_url
from .source_extraction import extract_source_content


SOURCE_URLS_FILE = "source-urls.json"
SOURCE_DOCUMENTS_FILE = "source-documents.json"
EXTRACTED_PASSAGES_FILE = "extracted-passages.json"
SCHEMA_VERSION = "1.0"


_ROOT = Path(__file__).resolve().parents[2]


def _load_validator(filename: str) -> Draft202012Validator:
    schema = json.loads(
        (_ROOT / "shared" / "schemas" / filename).read_text(encoding="utf-8")
    )
    return Draft202012Validator(schema, format_checker=FormatChecker())


_MANIFEST_VALIDATOR = _load_validator("source-urls.schema.json")
_DOCUMENTS_VALIDATOR = _load_validator("source-documents.schema.json")
_PASSAGES_VALIDATOR = _load_validator("extracted-passages.schema.json")


def _validate(validator: Draft202012Validator, payload: dict[str, Any], label: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(item) for item in errors[0].path) or "<root>"
        raise ValueError(f"Invalid {label} at {location}: {errors[0].message}")


def _fingerprint(sources: list[dict[str, Any]]) -> str:
    canonical = []
    for source in sources:
        item = {
            "url": canonicalize_url(source["url"]),
            "type": source["type"],
            "source_id": source.get("source_id"),
            "provider": source.get("provider"),
        }
        canonical.append(item)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_requests(manifest: dict[str, Any]) -> list[dict[str, str]]:
    requests: list[dict[str, str]] = []
    seen_source_ids: set[str] = set()
    seen_urls: set[str] = set()
    for source in manifest["sources"]:
        url = canonicalize_url(source["url"])
        source_id = str(source.get("source_id") or "").strip()
        if not source_id:
            source_id = "src_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        provider = str(source.get("provider") or "").strip()
        if not provider:
            provider = str(urlsplit_hostname(url))
        if source_id in seen_source_ids:
            raise ValueError(f"duplicate source_id: {source_id}")
        if url in seen_urls:
            raise ValueError(f"duplicate source URL: {url}")
        seen_source_ids.add(source_id)
        seen_urls.add(url)
        requests.append({
            "source_id": source_id,
            "url": url,
            "provider": provider,
            "type": source["type"],
        })
    return requests


def urlsplit_hostname(url: str) -> str:
    from urllib.parse import urlsplit
    return urlsplit(url).hostname or "unknown"


def _load_cached(project_path: Path, fingerprint: str, project_name: str) -> tuple[dict, dict] | None:
    documents_path = project_path / SOURCE_DOCUMENTS_FILE
    passages_path = project_path / EXTRACTED_PASSAGES_FILE
    if not documents_path.exists() or not passages_path.exists():
        return None

    documents = json.loads(documents_path.read_text(encoding="utf-8"))
    passages = json.loads(passages_path.read_text(encoding="utf-8"))
    _validate(_DOCUMENTS_VALIDATOR, documents, SOURCE_DOCUMENTS_FILE)
    _validate(_PASSAGES_VALIDATOR, passages, EXTRACTED_PASSAGES_FILE)
    if documents["project_name"] != project_name or passages["project_name"] != project_name:
        return None
    if documents["request_fingerprint"] != fingerprint or passages["request_fingerprint"] != fingerprint:
        return None
    return documents, passages


def build_source_corpus_from_file(project_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = Path(project_path)
    manifest_path = project_root / SOURCE_URLS_FILE
    if not manifest_path.exists():
        raise FileNotFoundError(f"{SOURCE_URLS_FILE} not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate(_MANIFEST_VALIDATOR, manifest, SOURCE_URLS_FILE)

    project_name = str(manifest["project_name"]).strip()
    requests = _normalize_requests(manifest)
    fingerprint = _fingerprint(manifest["sources"])

    cached = _load_cached(project_root, fingerprint, project_name)
    if cached is not None:
        return cached

    documents_list: list[dict[str, Any]] = []
    passages_list: list[dict[str, Any]] = []

    for item in requests:
        document = acquire_source_document(
            url=item["url"],
            source_id=item["source_id"],
            provider=item["provider"],
            source_type=item["type"],
        )
        extracted = extract_source_content(document)
        document = extracted["document"]
        documents_list.append(document)
        passages_list.extend(extracted["passages"])

    documents = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "request_fingerprint": fingerprint,
        "documents": documents_list,
    }
    passages = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "request_fingerprint": fingerprint,
        "passages": passages_list,
    }
    _validate(_DOCUMENTS_VALIDATOR, documents, SOURCE_DOCUMENTS_FILE)
    _validate(_PASSAGES_VALIDATOR, passages, EXTRACTED_PASSAGES_FILE)

    (project_root / SOURCE_DOCUMENTS_FILE).write_text(
        json.dumps(documents, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    (project_root / EXTRACTED_PASSAGES_FILE).write_text(
        json.dumps(passages, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return documents, passages
