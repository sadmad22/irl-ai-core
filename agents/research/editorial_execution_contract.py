"""Bounded execution contract for editorial recovery mutations.

Editorial recovery is intentionally narrower than arbitrary article rewriting:
one execution may revise exactly one existing section's body/content/text.
Claims, evidence references, SEO metadata, section identity, and publication
state remain outside this contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict


class EditorialRevision(TypedDict):
    """The only mutation shape accepted by the editorial executor."""

    section_id: str
    content: str


_ALLOWED_FIELDS = frozenset({"section_id", "content"})


def validate_editorial_revision(value: Any) -> EditorialRevision:
    """Validate and normalize one bounded editorial revision payload."""
    if not isinstance(value, Mapping):
        raise ValueError("editorial revision must be a mapping")
    unknown = set(value) - _ALLOWED_FIELDS
    missing = _ALLOWED_FIELDS - set(value)
    if unknown:
        raise ValueError(f"editorial revision returned unsupported fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"editorial revision is missing fields: {sorted(missing)}")
    section_id = str(value["section_id"]).strip()
    content = str(value["content"]).strip()
    if not section_id:
        raise ValueError("editorial revision requires section_id")
    if not content:
        raise ValueError("editorial revision requires non-empty content")
    return {"section_id": section_id, "content": content}
