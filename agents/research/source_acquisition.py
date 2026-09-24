from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests


DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 4
DEFAULT_USER_AGENT = "IRL-AI-Core-Research/1.0 (+https://insurancereviewlab.com/)"
ACQUISITION_POLICY_VERSION = "1.1"

_ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
_PRIVATE_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost"}


class SourceAcquisitionError(ValueError):
    """Raised when a source cannot be fetched safely and completely."""


class HttpTransport(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any:
        ...


def canonicalize_url(url: str) -> str:
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError as exc:
        raise SourceAcquisitionError("source URL is malformed") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SourceAcquisitionError("source URL must use http or https")
    if not parsed.hostname:
        raise SourceAcquisitionError("source URL must contain a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise SourceAcquisitionError("source URL must not contain credentials")

    hostname = parsed.hostname.lower().rstrip(".")
    try:
        port = parsed.port
    except ValueError as exc:
        raise SourceAcquisitionError("source URL port is invalid") from exc
    if port is not None and not 1 <= port <= 65535:
        raise SourceAcquisitionError("source URL port is invalid")

    is_ipv6 = ":" in hostname
    host_for_netloc = f"[{hostname}]" if is_ipv6 else hostname
    netloc = host_for_netloc
    if port is not None:
        default_port = (parsed.scheme.lower() == "http" and port == 80) or (
            parsed.scheme.lower() == "https" and port == 443
        )
        if not default_port:
            netloc = f"{host_for_netloc}:{port}"

    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))


def _resolve_host_addresses(
    hostname: str,
    port: int,
    resolver: Callable[..., list[tuple[Any, ...]]],
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        results = resolver(hostname, port, type=socket.SOCK_STREAM)
        return {ipaddress.ip_address(item[4][0]) for item in results}
    except (OSError, ValueError, IndexError, KeyError) as exc:
        raise SourceAcquisitionError(f"source hostname could not be resolved: {hostname}") from exc


def _assert_public_host(
    url: str,
    *,
    resolver: Callable[..., list[tuple[Any, ...]]] = socket.getaddrinfo,
) -> None:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    normalized = hostname.lower().rstrip(".")
    if normalized in _PRIVATE_HOSTNAMES or normalized.endswith(".localhost"):
        raise SourceAcquisitionError("source URL resolves to a local hostname")

    try:
        literal = ipaddress.ip_address(normalized)
    except ValueError:
        literal = None

    if literal is not None:
        if not literal.is_global:
            raise SourceAcquisitionError("source URL must target a public IP address")
        return

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    first = _resolve_host_addresses(normalized, port, resolver)
    second = _resolve_host_addresses(normalized, port, resolver)

    if first != second:
        raise SourceAcquisitionError(
            "source hostname DNS resolution changed during safety validation"
        )
    if not first or any(not address.is_global for address in first):
        raise SourceAcquisitionError("source hostname resolves to a non-public IP address")


def _decode_html(body: bytes, content_type: str) -> str:
    match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
    encoding = match.group(1).strip().strip('"') if match else "utf-8"
    try:
        return body.decode(encoding, errors="strict")
    except (LookupError, UnicodeDecodeError):
        try:
            return body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SourceAcquisitionError("source HTML could not be decoded deterministically") from exc


def _read_limited_body(response: Any, *, max_bytes: int) -> bytes:
    content_length = str(response.headers.get("content-length", "")).strip()
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise SourceAcquisitionError("source response exceeds the maximum byte limit")
        except ValueError:
            pass

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise SourceAcquisitionError("source response exceeds the maximum byte limit")
        chunks.append(bytes(chunk))
    if total == 0:
        raise SourceAcquisitionError("source response body is empty")
    return b"".join(chunks)


def _now_iso(captured_at: str | None) -> str:
    if captured_at is not None:
        return captured_at
    return datetime.now(timezone.utc).isoformat()


def _cache_validators(cached_document: dict[str, Any] | None, *, current_url: str) -> dict[str, str]:
    if not cached_document:
        return {}
    if cached_document.get("final_url") != current_url:
        return {}

    headers: dict[str, str] = {}
    etag = cached_document.get("etag")
    last_modified = cached_document.get("last_modified")
    if isinstance(etag, str) and etag.strip():
        headers["If-None-Match"] = etag
    if isinstance(last_modified, str) and last_modified.strip():
        headers["If-Modified-Since"] = last_modified
    return headers


def acquire_source_document(
    *,
    url: str,
    source_id: str,
    provider: str,
    source_type: str,
    transport: HttpTransport | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    user_agent: str = DEFAULT_USER_AGENT,
    resolve_public_host: bool = True,
    dns_resolver: Callable[..., list[tuple[Any, ...]]] = socket.getaddrinfo,
    captured_at: str | None = None,
    cached_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not str(source_id).strip():
        raise SourceAcquisitionError("source_id is required")
    if not str(provider).strip():
        raise SourceAcquisitionError("provider is required")
    if source_type not in {"official", "institutional", "secondary"}:
        raise SourceAcquisitionError("source type is invalid")
    if timeout_seconds <= 0 or max_bytes <= 0 or max_redirects < 0:
        raise SourceAcquisitionError("acquisition limits must be positive")
    if not str(user_agent).strip():
        raise SourceAcquisitionError("user_agent is required")

    current_url = canonicalize_url(url)
    requested_url = current_url
    redirect_chain = [requested_url]
    transport_obj: HttpTransport = transport or requests.Session()
    revalidation_headers = _cache_validators(cached_document, current_url=current_url)
    checked_at = _now_iso(captured_at)

    try:
        for _ in range(max_redirects + 1):
            if resolve_public_host:
                _assert_public_host(current_url, resolver=dns_resolver)

            response = transport_obj.get(
                current_url,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                    **revalidation_headers,
                },
                timeout=timeout_seconds,
                allow_redirects=False,
                stream=True,
            )
            try:
                status = int(response.status_code)
                location = response.headers.get("location")
                if 300 <= status < 400 and location:
                    if len(redirect_chain) >= max_redirects + 1:
                        raise SourceAcquisitionError("source redirect limit exceeded")
                    next_url = canonicalize_url(urljoin(current_url, str(location)))
                    if (
                        urlsplit(current_url).scheme == "https"
                        and urlsplit(next_url).scheme == "http"
                    ):
                        raise SourceAcquisitionError(
                            "HTTPS to HTTP redirect is not allowed"
                        )
                    current_url = next_url
                    revalidation_headers = _cache_validators(
                        cached_document,
                        current_url=current_url,
                    )
                    redirect_chain.append(current_url)
                    continue

                if status == 304:
                    if cached_document is None:
                        raise SourceAcquisitionError("304 response received without cached source document")
                    if cached_document.get("source_id") != source_id:
                        raise SourceAcquisitionError("cached source document identity mismatch")
                    if canonicalize_url(str(cached_document.get("requested_url", ""))) != requested_url:
                        raise SourceAcquisitionError("cached source document URL mismatch")
                    if cached_document.get("final_url") != current_url:
                        raise SourceAcquisitionError("304 response final URL does not match cached source document")

                    refreshed = dict(cached_document)
                    refreshed["cache_checked_at"] = checked_at
                    etag = response.headers.get("etag")
                    last_modified = response.headers.get("last-modified")
                    if etag:
                        refreshed["etag"] = str(etag)
                    if last_modified:
                        refreshed["last_modified"] = str(last_modified)
                    return refreshed

                if status < 200 or status >= 300:
                    raise SourceAcquisitionError(f"source returned HTTP {status}")

                content_type = str(response.headers.get("content-type", "")).split(";", 1)[0].strip().lower()
                if content_type not in _ALLOWED_CONTENT_TYPES:
                    raise SourceAcquisitionError(f"unsupported source content type: {content_type or '<missing>'}")

                body = _read_limited_body(response, max_bytes=max_bytes)
                html = _decode_html(body, str(response.headers.get("content-type", "")))
                content_sha256 = hashlib.sha256(body).hexdigest()
                source_document_id = "srcdoc_" + hashlib.sha256(
                    f"{current_url}\0{content_sha256}".encode("utf-8")
                ).hexdigest()[:24]

                same_content_identity = (
                    cached_document is not None
                    and cached_document.get("source_document_id") == source_document_id
                    and cached_document.get("content_sha256") == content_sha256
                    and cached_document.get("final_url") == current_url
                )
                retrieved_at = (
                    str(cached_document["retrieved_at"])
                    if same_content_identity
                    else checked_at
                )

                return {
                    "source_document_id": source_document_id,
                    "source_id": source_id,
                    "requested_url": requested_url,
                    "final_url": current_url,
                    "provider": provider,
                    "type": source_type,
                    "retrieved_at": retrieved_at,
                    "cache_checked_at": checked_at,
                    "http_status": status,
                    "content_type": content_type,
                    "content_sha256": content_sha256,
                    "content_bytes": len(body),
                    "redirect_chain": redirect_chain,
                    "etag": str(response.headers["etag"]) if response.headers.get("etag") else None,
                    "last_modified": (
                        str(response.headers["last-modified"])
                        if response.headers.get("last-modified")
                        else None
                    ),
                    "html": html,
                }
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

        raise SourceAcquisitionError("source redirect limit exceeded")
    except SourceAcquisitionError:
        raise
    except requests.RequestException as exc:
        raise SourceAcquisitionError(f"source request failed: {exc}") from exc
