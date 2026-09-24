from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any


_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "footer", "header", "aside", "form"}
_BLOCK_TAGS = {
    "p": "paragraph",
    "li": "list_item",
    "td": "table_cell",
    "th": "table_cell",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass
class _Block:
    kind: str
    text: str
    heading_path: list[str]


class _HTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.focus_depth = 0
        self.has_title = False
        self.title_parts: list[str] = []
        self.current_tag: str | None = None
        self.current_kind: str | None = None
        self.current_parts: list[str] = []
        self.current_heading_level: int | None = None
        self.heading_path: list[str] = []
        self.focused_blocks: list[_Block] = []
        self.fallback_blocks: list[_Block] = []
        self.focused_loose_parts: list[str] = []
        self.fallback_loose_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self.skip_depth += 1
            return
        if tag == "title":
            self.has_title = True
            self.title_parts = []
            return
        if tag in {"main", "article"}:
            self.focus_depth += 1

        if self.current_tag is None and tag in _BLOCK_TAGS:
            self.current_tag = tag
            self.current_kind = _BLOCK_TAGS[tag]
            self.current_parts = []
            self.current_heading_level = int(tag[1]) if tag.startswith("h") else None

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if tag == "title":
            self.has_title = False
            return

        if self.current_tag == tag:
            self._finalize_block()
            self.current_tag = None
            self.current_kind = None
            self.current_parts = []
            self.current_heading_level = None

        if tag in {"main", "article"} and self.focus_depth:
            self.focus_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.has_title:
            self.title_parts.append(data)
        elif self.current_tag is not None:
            self.current_parts.append(data)
        else:
            target = self.focused_loose_parts if self.focus_depth else self.fallback_loose_parts
            target.append(data)

    def close(self) -> None:
        super().close()
        if self.current_tag is not None:
            self._finalize_block()
            self.current_tag = None
            self.current_kind = None
            self.current_parts = []
            self.current_heading_level = None

    def _finalize_block(self) -> None:
        text = _clean_text(" ".join(self.current_parts))
        if not text:
            return

        level = self.current_heading_level
        block = _Block(kind=self.current_kind or "paragraph", text=text, heading_path=list(self.heading_path))
        target = self.focused_blocks if self.focus_depth else self.fallback_blocks
        if block.kind == "heading" or len(text) >= 16:
            target.append(block)

        if level is not None:
            self.heading_path = self.heading_path[: level - 1]
            self.heading_path.append(text)


def _blocks_with_loose_fallback(parser: _HTMLExtractor) -> list[_Block]:
    blocks = parser.focused_blocks or parser.fallback_blocks
    if blocks:
        return blocks

    loose_parts = parser.focused_loose_parts or parser.fallback_loose_parts
    loose_text = _clean_text(" ".join(loose_parts))
    if len(loose_text) < 16:
        return []
    return [_Block(kind="paragraph", text=loose_text, heading_path=[])]


def extract_source_content(document: dict[str, Any]) -> dict[str, Any]:
    html = document.get("html")
    source_document_id = str(document.get("source_document_id", "")).strip()
    if not isinstance(html, str) or not html.strip():
        raise ValueError("source document html is required")
    if not source_document_id:
        raise ValueError("source_document_id is required")

    parser = _HTMLExtractor()
    parser.feed(html)
    parser.close()

    blocks = _blocks_with_loose_fallback(parser)
    seen: set[tuple[str, tuple[str, ...]]] = set()
    passages: list[dict[str, Any]] = []
    normalized_parts: list[str] = []
    cursor = 0

    for block in blocks:
        key = (block.text, tuple(block.heading_path))
        if key in seen:
            continue
        seen.add(key)

        text_sha256 = hashlib.sha256(block.text.encode("utf-8")).hexdigest()
        normalized_parts.append(block.text)
        char_start = cursor
        char_end = cursor + len(block.text)
        cursor = char_end + 1
        ordinal = len(passages)
        passage_id = "pass_" + hashlib.sha256(
            f"{source_document_id}\0{ordinal}\0{text_sha256}".encode("utf-8")
        ).hexdigest()[:24]
        passages.append(
            {
                "passage_id": passage_id,
                "source_document_id": source_document_id,
                "ordinal": ordinal,
                "kind": block.kind,
                "heading_path": block.heading_path,
                "text": block.text,
                "text_sha256": text_sha256,
                "char_start": char_start,
                "char_end": char_end,
            }
        )

    if not passages:
        raise ValueError("source document contains no extractable content")

    normalized_text = "\n".join(normalized_parts)
    title = _clean_text(" ".join(parser.title_parts)) or source_document_id
    enriched_document = dict(document)
    enriched_document["title"] = title
    enriched_document["normalized_text"] = normalized_text
    return {"document": enriched_document, "passages": passages}
