from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "youtube_videos_ready"
SOURCE = "youtube_api"
PLACEMENTS = {"intro", "body", "conclusion"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _int(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _score(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError("youtube candidate relevance_score must be between 0 and 1")
    return float(value)


def _video_id(lineage: dict[str, str], video: dict[str, Any]) -> str:
    raw = json.dumps({"lineage": lineage, "video": video, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"yt_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    allowed = {"youtube_video_id", "url", "title", "channel_title", "published_at", "duration_seconds", "thumbnail_url", "relevance_score", "source"}
    unknown = set(candidate) - allowed
    if unknown:
        raise ValueError(f"youtube candidate contains unsupported fields: {sorted(unknown)}")
    source = candidate.get("source", SOURCE)
    if source != SOURCE:
        raise ValueError("youtube candidate source must be youtube_api")
    video_id = _text(candidate.get("youtube_video_id"), "youtube candidate.youtube_video_id")
    _text(candidate.get("url"), "youtube candidate.url")
    _text(candidate.get("title"), "youtube candidate.title")
    _text(candidate.get("channel_title"), "youtube candidate.channel_title")
    _text(candidate.get("published_at"), "youtube candidate.published_at")
    _int(candidate.get("duration_seconds"), "youtube candidate.duration_seconds")
    _text(candidate.get("thumbnail_url"), "youtube candidate.thumbnail_url")
    relevance = _score(candidate.get("relevance_score"))
    if len(video_id) > 64:
        raise ValueError("youtube candidate.youtube_video_id is too long")
    if not candidate["url"].strip().startswith("https://www.youtube.com/watch?v="):
        raise ValueError("youtube candidate.url must be a canonical YouTube watch URL")
    return {
        "youtube_video_id": video_id,
        "url": candidate["url"].strip(),
        "title": candidate["title"].strip(),
        "channel_title": candidate["channel_title"].strip(),
        "published_at": candidate["published_at"].strip(),
        "duration_seconds": candidate["duration_seconds"],
        "thumbnail_url": candidate["thumbnail_url"].strip(),
        "relevance_score": relevance,
        "source": SOURCE,
    }


def build_youtube_videos_contract(*, outline_editor: dict[str, Any], candidates: list[dict[str, Any]] | None = None, enabled: bool = True, required: bool = False, max_videos: int = 1, placement: str = "body") -> dict[str, Any]:
    """Build a deterministic YouTube video selection contract from API-sourced candidates.

    The engine does not call YouTube, generate metadata, insert embeds, or publish content.
    Discovery and verification happen upstream; rendering remains downstream.
    """
    if not isinstance(outline_editor, dict) or outline_editor.get("lifecycle_stage") != "outline_editor_ready":
        raise ValueError("YouTube Videos requires an outline_editor_ready Outline Editor")
    lineage_fields = ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "outline_editor_id", "details_to_include_id")
    lineage = {field: _text(outline_editor.get(field), f"Outline Editor.{field}") for field in lineage_fields}
    enabled = _bool(enabled, "enabled")
    required = _bool(required, "required")
    max_videos = _int(max_videos, "max_videos")
    placement = _text(placement, "placement")
    if placement not in PLACEMENTS:
        raise ValueError(f"placement must be one of {sorted(PLACEMENTS)}")
    if required and not enabled:
        raise ValueError("required cannot be true when disabled")
    if enabled and max_videos < 1:
        raise ValueError("max_videos must be at least 1 when enabled")
    if not enabled and max_videos != 0:
        raise ValueError("max_videos must be zero when disabled")

    normalized = [_normalize_candidate(candidate) for candidate in (candidates or [])]
    ids = [video["youtube_video_id"] for video in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("YouTube candidate video IDs must be unique")
    selected = sorted(normalized, key=lambda item: (-item["relevance_score"], item["youtube_video_id"]))[:max_videos] if enabled else []
    if required and not selected:
        raise ValueError("required YouTube Videos need at least one verified candidate")

    payload = {"enabled": enabled, "required": required, "max_videos": max_videos, "placement": placement, "source_requirement": SOURCE, "videos": selected}
    return {
        "youtube_videos_id": _video_id(lineage, payload),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "youtube_videos": payload,
        "audit": {"method": "deterministic-youtube-video-contract", "method_version": METHOD_VERSION, "validation_status": "validated"},
    }
