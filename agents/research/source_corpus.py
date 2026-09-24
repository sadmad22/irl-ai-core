from __future__ import annotations

import hashlib
import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from .source_acquisition import (
    ACQUISITION_POLICY_VERSION,
    HttpTransport,
    acquire_source_document,
    canonicalize_url,
)
from .source_extraction import EXTRACTION_POLICY_VERSION, extract_source_content


SOURCE_URLS_FILE = "source-urls.json"
SOURCE_DOCUMENTS_FILE = "source-documents.json"
EXTRACTED_PASSAGES_FILE = "extracted-passages.json"
SCHEMA_VERSION = "1.1"
DEFAULT_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60

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


def _fingerprint(sources: list[dict[str, str]]) -> str:
    canonical = {
        "acquisition_policy_version": ACQUISITION_POLICY_VERSION,
        "extraction_policy_version": EXTRACTION_POLICY_VERSION,
        "sources": sources,
    }
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
            provider = urlsplit(url).hostname or "unknown"

        if source_id in seen_source_ids:
            raise ValueError(f"duplicate source_id: {source_id}")
        if url in seen_urls:
            raise ValueError(f"duplicate source URL: {url}")

        seen_source_ids.add(source_id)
        seen_urls.add(url)
        requests.append(
            {
                "source_id": source_id,
                "url": url,
                "provider": provider,
                "type": source["type"],
            }
        )
    return requests


def _parse_datetime(value: str, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"cached {label} is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"cached {label} must include timezone")
    return parsed


def _now_iso(now: str | None) -> str:
    if now is None:
        return datetime.now(timezone.utc).isoformat()
    _parse_datetime(now, label="current time")
    return now


def _is_fresh(document: dict[str, Any], *, now: datetime, max_age_seconds: int) -> bool:
    checked_at = _parse_datetime(str(document["cache_checked_at"]), label="cache_checked_at")
    age = now - checked_at
    if age.total_seconds() < 0:
        return True
    return age <= timedelta(seconds=max_age_seconds)


def _load_cached(project_path: Path, fingerprint: str, project_name: str) -> tuple[dict, dict] | None:
    documents_path = project_path / SOURCE_DOCUMENTS_FILE
    passages_path = project_path / EXTRACTED_PASSAGES_FILE
    if not documents_path.exists() or not passages_path.exists():
        return None

    documents = json.loads(documents_path.read_text(encoding="utf-8"))
    passages = json.loads(passages_path.read_text(encoding="utf-8"))

    if documents.get("schema_version") != SCHEMA_VERSION or passages.get("schema_version") != SCHEMA_VERSION:
        return None

    _validate(_DOCUMENTS_VALIDATOR, documents, SOURCE_DOCUMENTS_FILE)
    _validate(_PASSAGES_VALIDATOR, passages, EXTRACTED_PASSAGES_FILE)

    if documents["project_name"] != project_name or passages["project_name"] != project_name:
        return None
    if documents["request_fingerprint"] != fingerprint or passages["request_fingerprint"] != fingerprint:
        return None
    if documents["acquisition_policy_version"] != ACQUISITION_POLICY_VERSION:
        return None
    if documents["extraction_policy_version"] != EXTRACTION_POLICY_VERSION:
        return None
    if passages["acquisition_policy_version"] != ACQUISITION_POLICY_VERSION:
        return None
    if passages["extraction_policy_version"] != EXTRACTION_POLICY_VERSION:
        return None

    document_ids = {item["source_document_id"] for item in documents["documents"]}
    if any(item["source_document_id"] not in document_ids for item in passages["passages"]):
        raise ValueError("cached extracted passages contain unknown source documents")
    return documents, passages


def _passages_by_document(passages: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in passages["passages"]:
        grouped.setdefault(item["source_document_id"], []).append(item)
    return grouped


def build_source_corpus_from_file(
    project_path: str | Path,
    *,
    transport: HttpTransport | None = None,
    cache_max_age_seconds: int = DEFAULT_CACHE_MAX_AGE_SECONDS,
    force_refresh: bool = False,
    now: str | None = None,
    dns_resolver: Callable[..., list[tuple[Any, ...]]] = socket.getaddrinfo,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if cache_max_age_seconds < 0:
        raise ValueError("cache_max_age_seconds must be non-negative")

    project_root = Path(project_path)
    manifest_path = project_root / SOURCE_URLS_FILE
    if not manifest_path.exists():
        raise FileNotFoundError(f"{SOURCE_URLS_FILE} not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate(_MANIFEST_VALIDATOR, manifest, SOURCE_URLS_FILE)

    project_name = str(manifest["project_name"]).strip()
    requests = _normalize_requests(manifest)
    fingerprint = _fingerprint(requests)
    check_time = _now_iso(now)
    check_datetime = _parse_datetime(check_time, label="current time")

    cached = _load_cached(project_root, fingerprint, project_name)
    if cached is not None:
        cached_documents, cached_passages = cached
        cached_by_source = {item["source_id"]: item for item in cached_documents["documents"]}
        cached_passages_by_document = _passages_by_document(cached_passages)

        all_fresh = not force_refresh and all(
            item["source_id"] in cached_by_source
            and _is_fresh(
                cached_by_source[item["source_id"]],
                now=check_datetime,
                max_age_seconds=cache_max_age_seconds,
            )
            for item in requests
        )
        if all_fresh:
            return cached_documents, cached_passages
    else:
        cached_documents = None
        cached_passages = None
        cached_by_source = {}
        cached_passages_by_document = {}

    documents_list: list[dict[str, Any]] = []
    passages_list: list[dict[str, Any]] = []

    for item in requests:
        cached_document = cached_by_source.get(item["source_id"])
        reusable_cached = (
            cached_document is not None
            and not force_refresh
            and _is_fresh(
                cached_document,
                now=check_datetime,
                max_age_seconds=cache_max_age_seconds,
            )
        )

        if reusable_cached:
            document = cached_document
            passages = cached_passages_by_document.get(document["source_document_id"], [])
            if not passages:
                raise ValueError("cached source document has no extracted passages")
        else:
            document = acquire_source_document(
                url=item["url"],
                source_id=item["source_id"],
                provider=item["provider"],
                source_type=item["type"],
                transport=transport,
                dns_resolver=dns_resolver,
                captured_at=check_time,
                cached_document=cached_document,
            )
            same_document = (
                cached_document is not None
                and document["source_document_id"] == cached_document["source_document_id"]
            )
            if same_document:
                passages = cached_passages_by_document.get(document["source_document_id"], [])
                if not passages:
                    raise ValueError("revalidated source document has no cached extracted passages")
            else:
                extracted = extract_source_content(document)
                document = extracted["document"]
                passages = extracted["passages"]

        documents_list.append(document)
        passages_list.extend(passages)

    documents = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "request_fingerprint": fingerprint,
        "acquisition_policy_version": ACQUISITION_POLICY_VERSION,
        "extraction_policy_version": EXTRACTION_POLICY_VERSION,
        "documents": documents_list,
    }
    passages = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "request_fingerprint": fingerprint,
        "acquisition_policy_version": ACQUISITION_POLICY_VERSION,
        "extraction_policy_version": EXTRACTION_POLICY_VERSION,
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