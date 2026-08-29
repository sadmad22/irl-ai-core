import pytest

from agents.research.article_draft import _section_body


def test_writer_never_serializes_internal_evidence_as_article_prose():
    evidence = [{
        "evidence_id": "ev_internal_001",
        "claim": {"attribute": "commercial_value"},
        "value": {"data": "low"},
        "subject": {"id": "consultant insurance cost"},
    }]

    body = _section_body(
        heading="Costs and Pricing Factors",
        keyword="consultant insurance cost",
        evidence_records=evidence,
        editorial_evidence=None,
    )

    assert body == ""
    assert "research evidence records" not in body
    assert "has a recorded value" not in body


def test_writer_uses_verified_editorial_evidence_as_prose():
    editorial = [{
        "evidence_id": "ev_editorial_001",
        "text": "Professional liability coverage can help protect consultants against claims arising from errors, omissions, or alleged professional negligence.",
    }]

    body = _section_body(
        heading="Coverage and Key Factors",
        keyword="consultant insurance cost",
        evidence_records=[],
        editorial_evidence=editorial,
    )

    assert body.rstrip(".") == editorial[0]["text"].rstrip(".")
    assert "research evidence records" not in body
