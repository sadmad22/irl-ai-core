from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from agents.research import agent
from agents.research.source_acquisition import SourceAcquisitionError, acquire_source_document, canonicalize_url
from agents.research.source_corpus import build_source_corpus_from_file


ROOT = Path(__file__).resolve().parents[1]


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "shared" / "schemas" / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


class FakeResponse:
    def __init__(self, *, status_code: int, headers: dict[str, str], body: bytes = b"") -> None:
        self.status_code = status_code
        self.headers = headers
        self._body = body
        self.closed = False

    def iter_content(self, *, chunk_size: int):
        for start in range(0, len(self._body), max(1, chunk_size)):
            yield self._body[start : start + chunk_size]

    def close(self) -> None:
        self.closed = True


class FakeTransport:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.get(url)
        if response is None:
            raise AssertionError(f"unexpected URL requested: {url}")
        return response


HTML = b"""<!doctype html>
<html>
  <head><title>Expat Health Insurance Guide</title></head>
  <body>
    <nav><p>Navigation text that must not become source material.</p></nav>
    <main>
      <h1>Expat Health Insurance</h1>
      <p>International health insurance can provide medical coverage while you live outside your home country.</p>
      <h2>Coverage</h2>
      <p>Plans can include benefits for hospital treatment and routine medical care.</p>
      <ul><li>Some plans apply deductibles before benefits begin.</li></ul>
      <p>Some plans apply deductibles before benefits begin.</p>
    </main>
    <footer><p>Footer boilerplate that must not be extracted.</p></footer>
  </body>
</html>"""


def test_canonicalize_url_normalizes_scheme_host_and_fragment():
    assert canonicalize_url("HTTPS://Example.COM/path#section") == "https://example.com/path"


def test_private_destination_is_blocked_before_network_request():
    with pytest.raises(SourceAcquisitionError, match="public IP"):
        acquire_source_document(
            url="http://127.0.0.1/private",
            source_id="src_test",
            provider="example",
            source_type="official",
        )


def test_redirects_are_manual_and_final_destination_is_revalidated():
    first = "https://example.com/start"
    second = "https://example.com/final"
    transport = FakeTransport(
        {
            first: FakeResponse(status_code=302, headers={"location": "/final"}),
            second: FakeResponse(
                status_code=200,
                headers={"content-type": "text/html; charset=utf-8"},
                body=HTML,
            ),
        }
    )

    document = acquire_source_document(
        url=first,
        source_id="src_example",
        provider="example.com",
        source_type="official",
        transport=transport,
        resolve_public_host=False,
        captured_at="2026-09-24T10:00:00+00:00",
    )

    assert document["requested_url"] == first
    assert document["final_url"] == second
    assert document["redirect_chain"] == [first, second]
    assert len(transport.calls) == 2
    assert all(call[1]["allow_redirects"] is False for call in transport.calls)


def test_non_html_sources_fail_closed():
    transport = FakeTransport(
        {
            "https://example.com/file.pdf": FakeResponse(
                status_code=200,
                headers={"content-type": "application/pdf"},
                body=b"%PDF-1.7",
            )
        }
    )

    with pytest.raises(SourceAcquisitionError, match="unsupported source content type"):
        acquire_source_document(
            url="https://example.com/file.pdf",
            source_id="src_pdf",
            provider="example.com",
            source_type="secondary",
            transport=transport,
            resolve_public_host=False,
        )


def test_source_corpus_extracts_content_and_preserves_cache(tmp_path):
    project = tmp_path / "research" / "sample"
    project.mkdir(parents=True)
    manifest = {
        "schema_version": "1.0",
        "project_name": "sample",
        "sources": [
            {
                "url": "https://example.com/guide",
                "source_id": "src_example",
                "provider": "example.com",
                "type": "official",
            }
        ],
    }
    (project / "source-urls.json").write_text(json.dumps(manifest), encoding="utf-8")

    transport = FakeTransport(
        {
            "https://example.com/guide": FakeResponse(
                status_code=200,
                headers={"content-type": "text/html; charset=utf-8"},
                body=HTML,
            )
        }
    )

    documents, passages = build_source_corpus_from_file(project, transport=transport)

    _validator("source-documents.schema.json").validate(documents)
    _validator("extracted-passages.schema.json").validate(passages)

    document = documents["documents"][0]
    assert document["title"] == "Expat Health Insurance Guide"
    assert "Navigation text" not in document["normalized_text"]
    assert "Footer boilerplate" not in document["normalized_text"]
    assert passages["passages"]
    assert all(item["source_document_id"] == document["source_document_id"] for item in passages["passages"])
    assert all(
        document["normalized_text"][item["char_start"] : item["char_end"]] == item["text"]
        for item in passages["passages"]
    )

    second_transport = FakeTransport({})
    cached_documents, cached_passages = build_source_corpus_from_file(project, transport=second_transport)

    assert cached_documents == documents
    assert cached_passages == passages
    assert second_transport.calls == []


def test_source_corpus_is_all_or_nothing_on_acquisition_failure(tmp_path):
    project = tmp_path / "research" / "sample"
    project.mkdir(parents=True)
    manifest = {
        "schema_version": "1.0",
        "project_name": "sample",
        "sources": [
            {"url": "https://example.com/ok", "type": "official"},
            {"url": "https://example.com/fail", "type": "secondary"},
        ],
    }
    (project / "source-urls.json").write_text(json.dumps(manifest), encoding="utf-8")

    transport = FakeTransport(
        {
            "https://example.com/ok": FakeResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                body=HTML,
            ),
            "https://example.com/fail": FakeResponse(
                status_code=500,
                headers={"content-type": "text/html"},
                body=b"server error",
            ),
        }
    )

    with pytest.raises(SourceAcquisitionError, match="HTTP 500"):
        build_source_corpus_from_file(project, transport=transport)

    assert not (project / "source-documents.json").exists()
    assert not (project / "extracted-passages.json").exists()


def test_research_agent_invokes_source_corpus_when_manifest_exists(tmp_path, monkeypatch):
    source = ROOT / "research" / "expat-health-insurance"
    destination = tmp_path / "research" / "expat-health-insurance"
    destination.parent.mkdir(parents=True)
    shutil.copytree(source, destination)
    (destination / "source-urls.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "expat-health-insurance",
                "sources": [
                    {
                        "url": "https://example.com/guide",
                        "type": "official",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    calls: list[Path] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        agent,
        "build_source_corpus_from_file",
        lambda project_path: calls.append(Path(project_path)),
    )

    agent.run("expat-health-insurance")

    assert [tmp_path / call for call in calls] == [destination]
